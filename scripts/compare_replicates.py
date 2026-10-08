"""Summarize one saved replicate cohort using its exact run configurations.

Usage: python scripts/compare_replicates.py COHORT_DIR [--report FILE]
Seed variation is descriptive simulation variability, not patient uncertainty.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from batch.lib import parse_toml, validate_run_metrics
from literature.lib import condition_from_config, evaluate_run, load_csv, saved_config_path


def load_cohort(directory):
    directory = Path(directory).resolve()
    paths = sorted(directory.glob("seed*/skibidy/metrics.csv"))
    if len(paths) < 2:
        raise ValueError(f"expected at least two saved seed runs in one cohort: {directory}")
    runs = {}
    for metrics in paths:
        saved = saved_config_path(str(metrics))
        if saved is None:
            raise FileNotFoundError(f"saved configuration missing beside {metrics}")
        config = Path(saved)
        cfg = parse_toml(config)
        seed = cfg.get("simulation", {}).get("random_seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"missing integer random seed: {config}")
        if metrics.parent.parent.name != f"seed{seed}" or seed in runs:
            raise ValueError(f"duplicate or mismatched seed: {config}")
        integrity = validate_run_metrics(metrics, cfg)
        sim = load_csv(str(metrics))
        condition = condition_from_config(cfg)
        _, report = evaluate_run(sim, [h / 24 for h in sim["time_h"]], cfg, condition)
        cohort_config = copy.deepcopy(cfg)
        for key in ("random_seed", "output_dir"):
            cohort_config.get("simulation", {}).pop(key, None)
        runs[seed] = dict(seed=seed, condition=condition,
                          cohort_config=cohort_config,
                          profile=cfg.get("analysis", {}).get("profile"),
                          metrics=str(metrics), config=str(config), integrity=integrity,
                          metrics_sha256=hashlib.sha256(metrics.read_bytes()).hexdigest(),
                          config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                          validation=report)
    identities = {(r["condition"], r["profile"]) for r in runs.values()}
    if len(identities) != 1:
        raise ValueError("a cohort cannot mix conditions or recorded profiles")
    configurations = [run["cohort_config"] for run in runs.values()]
    if any(config != configurations[0] for config in configurations):
        raise ValueError("a cohort cannot mix configurations beyond seed and output directory")
    return runs


def summarize(runs):
    if len(runs) < 2:
        raise ValueError("a cohort summary requires at least two seeds")
    methods = {run["validation"].get("scoring_method") for run in runs.values()}
    if len(methods) != 1:
        raise ValueError("a cohort cannot mix scoring methods")
    coverage = {}
    names = sorted({name for run in runs.values() for name in run["validation"]["coverage"]})
    for name in names:
        items = [r["validation"]["coverage"][name] for r in runs.values()]
        if any(item["status"] == "not_tested" for item in items):
            coverage[name] = dict(status="not_tested", n=0,
                                  reason="at least one replicate lacks a supported comparison")
            continue
        scopes = [item.get("comparison_dates") for item in items]
        if any(scope != scopes[0] for scope in scopes):
            raise ValueError(f"replicates have different comparison windows: {name}")
        values = [item["rmse_pct"] for item in items]
        coverage[name] = dict(status="fail" if any(item["status"] == "fail" for item in items) else "pass",
                              n=len(values), mean_rmse_pct=statistics.mean(values),
                              sample_sd_pct=statistics.stdev(values),
                              per_seed={str(seed): run["validation"]["coverage"][name]["rmse_pct"]
                                        for seed, run in sorted(runs.items())},
                              comparison_dates=scopes[0])
    statuses = [run["validation"]["status"] for run in runs.values()]
    status = "fail" if "fail" in statuses else ("pass" if all(s == "pass" for s in statuses) else "not_tested")
    return dict(status=status, n=len(runs), coverage=coverage, scoring_method=methods.pop(),
                uncertainty="Sample SD across simulation seeds. No patient-level uncertainty or significance claim.",
                runs=list(runs.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = summarize(load_cohort(args.cohort))
    for name, item in report["coverage"].items():
        if item["status"] == "not_tested":
            print(f"{name}: NOT TESTED")
        else:
            print(f"{name}: {item['mean_rmse_pct']:.2f}% ± {item['sample_sd_pct']:.2f}% SD, {item['status'].upper()}")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
