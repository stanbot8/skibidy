"""Validate saved replicate cohorts, preserving individual failures and spread.

Usage: python scripts/validate_replicates.py RESULTS_ROOT [--quick]
Exit 1 means at least one biological screen failed or was not tested; invalid
run evidence raises an error. No simulations are rerun by this command.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from batch.lib import aggregate_csvs, parse_toml, validate_run_metrics, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    results = args.results.resolve()
    runtime = json.loads((results / "runtime.json").read_text())
    summary = {"runtime": runtime, "cohorts": {}, "status": "pass"}
    curves = {}
    for skin, study in runtime["cohorts"]:
        name = skin + "-" + study
        cohort = results / name
        reports, paths = [], []
        for seed in runtime["seeds"]:
            run = cohort / f"seed{seed}"
            config = run / "bdm.toml"
            metrics = run / "skibidy" / "metrics.csv"
            cfg = parse_toml(config)
            if cfg.get("simulation", {}).get("random_seed") != seed:
                raise ValueError(f"seed/config mismatch: {run}")
            integrity = validate_run_metrics(metrics, cfg)
            report_path = run / "skibidy" / "validation.json"
            report_path.unlink(missing_ok=True)
            command = [sys.executable, str(ROOT / "literature" / "validate_all.py"),
                       str(metrics), "--config", str(config), "--report", str(report_path)]
            if args.quick:
                command.append("--quick")
            validation = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            (run / "validation.txt").write_text(validation.stdout + validation.stderr)
            if not report_path.exists():
                raise RuntimeError(f"validator did not produce a report: {run}; inspect validation.txt")
            report = json.loads(report_path.read_text())
            report.update(seed=seed, integrity=integrity, exit=validation.returncode)
            if report["status"] != "pass" or validation.returncode != 0:
                summary["status"] = "fail"
            reports.append(report)
            paths.append(str(metrics))
            print(f"{name} seed {seed}: {report['status']} ({report['tested']} comparisons)", flush=True)
        mean, population_std = aggregate_csvs(paths)
        n = len(paths)
        std = {k: [v * math.sqrt(n / (n - 1)) for v in values]
               for k, values in population_std.items()} if n > 1 else population_std
        write_csv(mean, cohort / "consensus_metrics.csv")
        std["time_h"] = mean["time_h"]
        write_csv(std, cohort / "sample_std.csv")
        summary["cohorts"][name] = dict(n=n, replicates=reports,
            spread="sample standard deviation across seeds; not parameter or patient uncertainty")
        curves[name] = (mean, std)
    (results / "validation-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    if not args.quick:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        for name, (mean, std) in curves.items():
            days = [v / 24 for v in mean["time_h"]]
            value = mean["wound_closure_pct"]
            spread = std["wound_closure_pct"]
            line, = ax.plot(days, value, label=name)
            ax.fill_between(days, [v-s for v,s in zip(value, spread)],
                            [v+s for v,s in zip(value, spread)], color=line.get_color(), alpha=.15)
        ax.set(xlabel="Simulation day", ylabel="Wound closure (%)",
               title="Saved baseline cohorts: mean and sample SD across seeds")
        ax.legend()
        fig.tight_layout()
        fig.savefig(results / "baseline-closure.png", dpi=160)
        plt.close(fig)
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
