"""Package existing baseline replicates without running or changing simulations."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from batch.lib import parse_toml, validate_run_metrics
from literature.lib import condition_from_config


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path):
    with Path(path).open(newline="") as stream:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(stream)]


def export(source, destination, frozen):
    source, destination, frozen = map(Path, (source, destination, frozen))
    runtime = json.loads((source / "runtime.json").read_text())
    files = [source / "runtime.json", source / "validation-summary.json"]
    runs, cohorts = [], []
    for skin, study in runtime["cohorts"]:
        cohort = source / f"{skin}-{study}"
        raw = []
        for seed in runtime["seeds"]:
            directory = cohort / f"seed{seed}"
            config_path, metrics = directory / "bdm.toml", directory / "skibidy/metrics.csv"
            config = parse_toml(config_path)
            count, last = validate_run_metrics(metrics, config)
            if config["simulation"]["random_seed"] != seed:
                raise ValueError("saved configuration seed differs")
            record = json.loads((directory / "receipt.json").read_text())
            validation = json.loads((directory / "skibidy/validation.json").read_text())
            names = ["bdm.toml", "receipt.json", "stdout.log", "stderr.log", "validation.txt",
                     "skibidy/metrics.csv", "skibidy/validation.json"]
            products = [directory / name for name in names]
            if any(not path.is_file() for path in products):
                raise ValueError("replicate evidence is incomplete")
            files.extend(products)
            raw.append(table(metrics))
            runs.append({"cohort": cohort.name, "seed": seed,
                         "condition_from_saved_config": condition_from_config(config),
                         "duration_days": config["skin"]["duration_days"],
                         "metrics_rows": count, "last_time_h": last,
                         "execution_status": "complete_metrics_verified",
                         "historical_validation_exit": record["validation_exit"],
                         "saved_validation_status": validation["status"],
                         "config_sha256": digest(config_path), "metrics_sha256": digest(metrics),
                         "validation_sha256": digest(directory / "skibidy/validation.json")})
        mean, sd = table(cohort / "consensus_metrics.csv"), table(cohort / "sample_std.csv")
        if any(len(rows) != len(mean) for rows in raw + [sd]):
            raise ValueError("cohort sampling extent differs")
        for index, row in enumerate(mean):
            for key, value in row.items():
                values = [rows[index][key] for rows in raw]
                expected_mean = statistics.mean(values)
                # The time coordinate remains a coordinate in both summary tables.
                expected_sd = value if key == "time_h" else statistics.stdev(values)
                # Six significant digits; allow the last digit's rounding bin,
                # including floating summation at an exact decimal midpoint.
                tolerance = 0.51 * 10 ** (math.floor(math.log10(abs(expected_mean))) - 5) if expected_mean else 1e-14
                if not math.isclose(value, expected_mean, rel_tol=0, abs_tol=tolerance):
                    raise ValueError(f"consensus differs from replicates: {cohort.name}/{key}")
                sd_tolerance = 0.51 * 10 ** (math.floor(math.log10(abs(expected_sd))) - 5) if expected_sd else 1e-14
                if not math.isclose(sd[index][key], expected_sd, rel_tol=0, abs_tol=max(sd_tolerance, 1e-14)):
                    raise ValueError(f"sample SD differs from replicates: {cohort.name}/{key}")
        files.extend([cohort / "consensus_metrics.csv", cohort / "sample_std.csv"])
        cohorts.append({"cohort": cohort.name, "n": len(raw), "summary_verified": True,
                        "standard_deviation": "sample SD, ddof=1; time_h column is the time coordinate",
                        "verification_precision": "existing writer's six significant digits; SD numerical noise below 1e-14 tolerated"})
    binary, library = frozen / "skibidy", frozen / "libskibidy.so"
    known = [{"path": str(path), "sha256": digest(path)} for path in (binary, library)]
    if known[0]["sha256"] != runtime["binary_sha256"]:
        raise ValueError("frozen executable differs from historical recorded executable")
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination / "replicate_evidence.zip"
    inventory = [{"path": path.relative_to(source).as_posix(), "sha256": digest(path),
                  "bytes": path.stat().st_size} for path in files]
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path, item in zip(files, inventory):
            zipped.write(path, item["path"])
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None or any(hashlib.sha256(zipped.read(item["path"])).hexdigest()
                                               != item["sha256"] for item in inventory):
            raise ValueError("archive verification failed")
    receipt = {"status": "published_existing_baseline_evidence", "source": str(source),
               "requested_runs": len(runs), "runs": runs, "cohorts": cohorts,
               "archive_sha256": digest(archive), "files": inventory,
               "runtime_provenance": {"historical_executable_sha256": runtime["binary_sha256"],
                   "known_frozen_files": known, "loaded_shared_library_identity": "not recorded",
                   "limitation": "Frozen library hash identifies a known file only. The old runner did not "
                   "prepend its selected build directory or capture dependency resolution/process mappings; "
                   "these nine runs do not prove which libskibidy, BioDynaMo or ROOT libraries were loaded."},
               "limits": "Three stochastic model seeds per condition; no new simulation or validation run. "
                         "Saved validation failures are retained. Original configs and evidence are byte-preserved."}
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--frozen-build", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.source, args.destination, args.frozen_build)
    print(json.dumps({"runs": result["requested_runs"], "archive_sha256": result["archive_sha256"]}))
