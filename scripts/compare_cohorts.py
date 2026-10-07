"""Compare saved candidate and control cohorts using matched simulation seeds.

Usage: python scripts/compare_cohorts.py CONTROL_DIR CANDIDATE_DIR [--report FILE]
A negative delta indicates lower RMSE. It does not establish biological efficacy.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_replicates import load_cohort, summarize


def compare(control, candidate):
    if control.keys() != candidate.keys():
        raise ValueError("paired comparison requires identical seed sets")
    if len(control) < 2:
        raise ValueError("paired comparison requires at least two seeds")
    coverage = {}
    for seed in sorted(control):
        left, right = control[seed], candidate[seed]
        if (left["condition"], left["profile"]) != (right["condition"], right["profile"]):
            raise ValueError(f"condition or recorded profile mismatch for seed {seed}")
        if left["validation"]["coverage"].keys() != right["validation"]["coverage"].keys():
            raise ValueError("observable coverage differs between cohorts")
    for name in next(iter(control.values()))["validation"]["coverage"]:
        deltas = []
        for seed in sorted(control):
            left = control[seed]["validation"]["coverage"][name]
            right = candidate[seed]["validation"]["coverage"][name]
            if left["status"] == "not_tested" or right["status"] == "not_tested":
                deltas = []
                break
            if left.get("comparison_dates") != right.get("comparison_dates"):
                raise ValueError(f"different comparison windows for seed {seed}: {name}")
            deltas.append(right["rmse_pct"] - left["rmse_pct"])
        if not deltas:
            coverage[name] = dict(status="not_tested", reason="unsupported in at least one paired run")
        else:
            coverage[name] = dict(status="compared", n=len(deltas),
                                  mean_delta_pct=statistics.mean(deltas),
                                  sample_sd_delta_pct=statistics.stdev(deltas),
                                  per_seed={str(s): d for s, d in zip(sorted(control), deltas)})
    return dict(control=summarize(control), candidate=summarize(candidate), coverage=coverage,
                interpretation="Candidate minus control RMSE, paired by seed. Descriptive model comparison only.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = compare(load_cohort(args.control), load_cohort(args.candidate))
    for name, item in report["coverage"].items():
        if item["status"] == "not_tested":
            print(f"{name}: NOT TESTED")
        else:
            print(f"{name}: delta {item['mean_delta_pct']:+.2f}% ± {item['sample_sd_delta_pct']:.2f}% SD")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return 0 if report["candidate"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
