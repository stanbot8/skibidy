"""Re-score the frozen NO experiment without changing its archive or simulations."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from batch.lib import parse_toml, validate_run_metrics
from literature.lib import condition_from_config, evaluate_run, load_csv
from literature.check_data_quality import discover_csvs


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replay(output, verify_consumers=False):
    archive_path = ROOT / "literature/no-collagen-20261007/evidence.zip"
    records, consumer_checks = [], []
    with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        paths = sorted(n for n in archive.namelist() if n.endswith("/skibidy/metrics.csv"))
        for index, member in enumerate(paths):
            directory = member.rsplit("/skibidy/", 1)[0]
            config_bytes = archive.read(directory + "/bdm.toml")
            metrics_bytes = archive.read(member)
            saved = temp / str(index)
            saved.mkdir()
            metrics_path = saved / "metrics.csv"
            metrics_path.write_bytes(metrics_bytes)
            (saved / "run-config.toml").write_bytes(config_bytes)
            config = parse_toml(saved / "run-config.toml")
            validate_run_metrics(metrics_path, config)
            sim = load_csv(metrics_path)
            _, report = evaluate_run(sim, [h / 24 for h in sim["time_h"]],
                                     config, condition_from_config(config))
            previous = json.loads(archive.read(member.replace("metrics.csv", "validation.json")))
            comparisons = {}
            for name, item in report["coverage"].items():
                old = previous["coverage"][name]
                comparisons[name] = {
                    "previous_status": old["status"], "previous_rmse_pct": old.get("rmse_pct"),
                    "current_status": item["status"], "current_rmse_pct": item.get("rmse_pct"),
                    "normalization_denominator": item.get("normalization_denominator"),
                    "comparison_kind": item.get("comparison_kind"),
                    "comparison_dates": {k: v for k, v in item.get("comparison_dates", {}).items()
                                         if k != "sample_days"}}
            records.append(dict(run=directory, metrics_sha256=digest(metrics_bytes),
                                config_sha256=digest(config_bytes),
                                previous_status=previous["status"], current_status=report["status"],
                                raw_final_collagen=sim.get("mean_collagen_wound", [None])[-1],
                                comparisons=comparisons))
            if verify_consumers and directory == "candidate/normal-wound/seed42":
                commands = [
                    [sys.executable, str(ROOT / "literature/validate_all.py"), str(metrics_path)],
                    [sys.executable, str(ROOT / "literature/validators/compare.py"),
                     "fibroblast", str(metrics_path), "--quick"],
                    [sys.executable, str(ROOT / "scripts/figures.py"), "--normal-consensus",
                     str(metrics_path), "--fig", "1", "--format", "png", "--output", str(saved / "figures")]]
                for command in commands:
                    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                    expected = 0 if "figures.py" in command[1] else 1
                    if completed.returncode != expected:
                        raise RuntimeError(completed.stdout + completed.stderr)
                    consumer_checks.append(dict(command=command[1], exit_code=completed.returncode))
                from scripts.dashboard import run_validation
                dashboard = run_validation(str(metrics_path))
                if dashboard.get("coverage") != report["coverage"]:
                    raise ValueError("Dashboard computation differs from the shared report")
                module = json.loads((saved / "validation_fibroblast.json").read_text())
                for name, item in module["coverage"].items():
                    if item != report["coverage"][name]:
                        raise ValueError("Module CLI differs from the shared report")
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(saved / "plots/validation_dashboard.png", output.parent / "normal_dashboard.png")
                figures = list((saved / "figures").glob("fig1*.png"))
                if len(figures) != 1:
                    raise ValueError("Publication figure was not produced")
                shutil.copyfile(figures[0], output.parent / "normal_figure.png")
    report = dict(archive=str(archive_path.relative_to(ROOT)),
                  archive_sha256=digest(archive_path.read_bytes()),
                  scoring_method="time-weighted piecewise-linear RMSE v2",
                  previous_method="equally weighted simulation samples, legacy normalization",
                  parameters_changed=False, threshold_pct=15, simulations_rerun=False,
                  source_sha256={name: digest((ROOT / name).read_bytes()) for name in
                                 ("literature/lib.py", "literature/validate_all.py",
                                  "literature/validators/compare.py", "scripts/figures.py",
                                  "literature/validators/ra_dashboard.py", "scripts/dashboard.py",
                                  "literature/check_data_quality.py", "scripts/compare_cohorts.py",
                                  "scripts/compare_replicates.py", "modules/tumor/SOURCES.yaml",
                                  "modules/diabetic/SOURCES.yaml")},
                  reference_sha256={str(Path(path).relative_to(ROOT)): digest(Path(path).read_bytes())
                                    for path in discover_csvs()},
                  runs=records, consumer_checks=consumer_checks)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    rows = [dict(run=r["run"], observable=name, **{key: item[key] for key in
                  ("previous_status", "previous_rmse_pct", "current_status", "current_rmse_pct")})
            for r in records for name, item in r["comparisons"].items()
            if item["previous_rmse_pct"] is not None or item["current_rmse_pct"] is not None]
    with output.with_suffix(".csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    changes = [(r["run"], name, item["previous_status"], item["current_status"])
               for r in records for name, item in r["comparisons"].items()
               if item["previous_status"] != item["current_status"]]
    print(f"Re-scored {len(records)} archived runs. Current overall failures: "
          f"{sum(r['current_status'] == 'fail' for r in records)}. Observable status changes: {len(changes)}")
    for change in changes:
        print(*change)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("replay.json"))
    parser.add_argument("--verify-consumers", action="store_true")
    options = parser.parse_args()
    replay(options.output, options.verify_consumers)
