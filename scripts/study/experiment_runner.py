#!/usr/bin/env python3
"""Experiment runner: execute named experiments from TOML configs.

Each experiment TOML defines a set of named configurations with parameter
overrides, run counts, and comparison mode.  The runner handles config
merging, simulation execution, consensus aggregation, and outcome
comparison automatically.

Usage:
    python3 scripts/study/experiment_runner.py studies/diabetic-wound/experiments/wound_size.toml
    python3 scripts/study/experiment_runner.py studies/*/experiments/*.toml
    python3 scripts/study/experiment_runner.py studies/diabetic-wound/experiments/biofilm_infection.toml --runs=3
"""

import argparse
import csv
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from batch.lib import (
    merge_config,
    apply_profile,
    apply_study,
    apply_overlay,
    override_param,
    run_simulation,
    get_metrics_path,
    load_csv,
    aggregate_csvs,
    resolve_study,
    study_profile,
)

from batch.lib import get_tomllib
tomllib = get_tomllib()
from scripts.study.gen_treatment_schedule import resolve_treatment, encode_runtime_schedule
# ---------------------------------------------------------------------------
# Experiment loading
# ---------------------------------------------------------------------------

def load_experiment(path):
    """Parse and validate an experiment TOML file."""
    with open(path, "rb") as f:
        data = tomllib.load(f)

    experiment = data.get("experiment")
    if not experiment:
        raise ValueError(f"{path}: missing [experiment] table")

    required = ["name", "configs"]
    for key in required:
        if key not in experiment:
            raise ValueError(f"{path}: missing experiment.{key}")

    # Defaults
    if "study" not in experiment:
        from pathlib import Path
        owner = next((parent for parent in Path(path).resolve().parents
                      if (parent / "preset.toml").is_file()), None)
        experiment["study"] = owner.name if owner else "diabetic-wound"
    experiment.setdefault("profile", study_profile(experiment["study"]) or None)
    experiment.setdefault("runs_per_config", 5)
    experiment.setdefault("description", "")

    # Validate configs
    for i, cfg in enumerate(experiment["configs"]):
        if "label" not in cfg:
            raise ValueError(f"{path}: configs[{i}] missing 'label'")
        cfg.setdefault("overrides", {})
        cfg.setdefault("profile", None)
        cfg.setdefault("study", None)
        cfg.setdefault("treatments", [])
        cfg.setdefault("extra_overlays", [])
        cfg.setdefault("schedule", [])

    return experiment


# ---------------------------------------------------------------------------
# Config preparation
# ---------------------------------------------------------------------------

def prepare_experiment_config(cfg, experiment):
    """Build bdm.toml for one experiment config entry.

    Merges core config, applies profile and study config from the experiment
    (or per-config overrides), applies treatments, then applies
    parameter overrides.
    """
    bdm_path = os.path.join(REPO, "bdm.toml")
    if os.path.exists(bdm_path):
        os.remove(bdm_path)

    # Merge base config
    merge_config()

    # Profile: per-config overrides experiment-level
    study = cfg.get("study") or experiment.get("study")
    profile = cfg.get("profile") or experiment.get("profile") or (study_profile(study) if study else None)
    if profile:
        apply_profile(profile)

    # Study config: per-config overrides experiment-level
    if study:
        apply_study(study)

    # Day-zero overlays retain declared order; shared treatments are explicit.
    for tname in cfg.get("treatments", []):
        apply_overlay(resolve_treatment(tname, study))

    # Extra overlays (arbitrary TOML files)
    for overlay in cfg.get("extra_overlays", []):
        opath = os.path.join(REPO, overlay)
        if os.path.isfile(opath):
            apply_overlay(opath)
        else:
            raise ValueError(f"missing overlay: {overlay}")

    # Parameter overrides
    for param_path, value in {**experiment.get("overrides", {}), **cfg.get("overrides", {})}.items():
        override_param(param_path, value)

    # Strip visualization for headless batch
    _strip_viz(bdm_path)
    from scripts.study.experiment_evidence import save_analysis_identity
    save_analysis_identity(bdm_path, cfg, experiment, profile, study)
    schedule = encode_runtime_schedule(cfg.get("schedule", []), study)
    if schedule:
        with open(bdm_path, "a", encoding="utf-8") as f:
            f.write(schedule)


def _strip_viz(bdm_path):
    """Remove visualization sections and disable autoopen."""
    with open(bdm_path) as f:
        lines = f.readlines()
    out = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[visualization") or stripped.startswith("[[visualize"):
            skip = True
            continue
        if skip and stripped.startswith("[") and not stripped.startswith("[visualization"):
            skip = False
        if skip:
            continue
        if stripped.startswith("metrics_autoopen"):
            out.append(line.replace("true", "false"))
            continue
        out.append(line)
    with open(bdm_path, "w") as f:
        f.writelines(out)


# ---------------------------------------------------------------------------
# Simulation execution with consensus
# ---------------------------------------------------------------------------

def run_consensus(label, cfg, experiment, n_runs, output_dir):
    """Run n_runs simulations for one config and aggregate.

    Returns (mean_data, std_data, csv_paths, outcomes).
    """
    if isinstance(n_runs, bool) or not isinstance(n_runs, int) or n_runs < 1:
        raise ValueError("runs_per_config must be a positive integer")
    from scripts.study.experiment_evidence import save_json, scalar_outcomes, summarize_replicates
    csv_paths = []
    records = [{"seed": experiment.get("seed", 42) + i, "status": "pending"}
               for i in range(n_runs)]
    raw_dir = os.path.join(output_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    safe_label = label.replace(" ", "_").replace("+", "_").replace("(", "").replace(")", "")
    receipt = os.path.join(raw_dir, safe_label + "_cohort.json")
    save_json(receipt, {"label": label, "status": "running", "runs": records})

    for i in range(n_runs):
        prepare_experiment_config(cfg, experiment)
        override_param("simulation.random_seed", records[i]["seed"])
        run_dir = os.path.join(raw_dir, f"{safe_label}_run{i:03d}")
        success, elapsed = run_simulation(output_path=run_dir)

        if not success:
            records[i]["status"] = "failed"
            save_json(receipt, {"label": label, "status": "failed", "runs": records})
            raise RuntimeError(f"{label}: run {i+1}/{n_runs} failed; cohort is incomplete")

        csv_path = get_metrics_path()
        if not os.path.isfile(csv_path):
            records[i]["status"] = "failed"
            save_json(receipt, {"label": label, "status": "failed", "runs": records})
            raise RuntimeError(f"{label}: run {i+1}/{n_runs} has no metrics")
        csv_paths.append(csv_path)
        records[i].update(status="complete", metrics=csv_path,
                          outcomes=scalar_outcomes(load_csv(csv_path)))
        save_json(receipt, {"label": label, "status": "running", "runs": records})
        print(f"    Run {i+1}/{n_runs} done ({elapsed:.0f}s)", flush=True)

    mean_data, std_data = aggregate_csvs(csv_paths)
    outcomes = summarize_replicates(records)
    save_json(receipt, {"label": label, "status": "complete", "runs": records,
                        "outcomes": outcomes})
    return mean_data, std_data, csv_paths, outcomes


# ---------------------------------------------------------------------------
# Comparison and output
# ---------------------------------------------------------------------------

def write_comparison(results, output_dir):
    """Write comparison CSV with all configs side by side."""
    if not results:
        return

    path = os.path.join(output_dir, "comparison.csv")
    outcome_keys = set()
    for r in results:
        outcome_keys.update(r.get("outcomes", {}).keys())
    outcome_keys = sorted(outcome_keys)

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["config", "n_runs"] + outcome_keys)
        for r in results:
            row = [r["label"], r.get("n_runs", 0)]
            for key in outcome_keys:
                val = r.get("outcomes", {}).get(key, "")
                if isinstance(val, float):
                    row.append(f"{val:.6g}")
                else:
                    row.append(val if val is not None else "")
            writer.writerow(row)

    print(f"  Comparison: {path}", flush=True)
    return path


def write_summary(experiment, results, output_dir, elapsed):
    """Write human-readable summary."""
    path = os.path.join(output_dir, "summary.txt")
    with open(path, "w") as f:
        f.write(f"Experiment: {experiment['name']}\n")
        if experiment.get("description"):
            f.write(f"{experiment['description']}\n")
        f.write(f"\nProfile: {experiment.get('profile', 'default')}\n")
        f.write(f"Study: {experiment.get('study', 'default')}\n")
        f.write(f"Runs per config: {experiment.get('runs_per_config', 5)}\n")
        f.write(f"Total time: {elapsed/60:.1f} minutes\n")
        f.write(f"\n{'='*70}\n")
        f.write(f"{'Config':<30} {'Closure':>8} {'T50 (d)':>8} {'Peak Infl':>10} {'Scar':>8}\n")
        f.write(f"{'-'*70}\n")

        for r in results:
            o = r.get("outcomes", {})
            label = r["label"][:30]
            closure = o.get("wound_closure_pct", 0)
            t50 = o.get("time_to_50pct_days")
            t50_str = f"{t50:.1f}" if t50 is not None else "N/A"
            peak = o.get("peak_inflammation", 0)
            scar = o.get("scar_magnitude", 0)
            f.write(f"{label:<30} {closure:>7.1f}% {t50_str:>8} {peak:>10.4f} {scar:>8.3f}\n")

        # Comparison vs first config (baseline)
        if len(results) > 1 and results[0].get("outcomes"):
            base = results[0]["outcomes"]
            base_closure = base.get("wound_closure_pct", 0)
            f.write(f"\n{'='*70}\n")
            f.write("Comparison vs first config:\n\n")
            for r in results[1:]:
                o = r.get("outcomes", {})
                closure = o.get("wound_closure_pct", 0)
                delta = closure - base_closure
                f.write(f"  {r['label']:<30} closure: {delta:+.1f} percentage points\n")

    print(f"  Summary: {path}", flush=True)


def print_results_table(results):
    """Print a results table to stdout."""
    if not results:
        return

    print(f"\n  {'Config':<30} {'Closure':>8} {'T50 (d)':>8} {'Peak Infl':>10} {'Scar':>8}")
    print(f"  {'-'*66}")

    for r in results:
        o = r.get("outcomes", {})
        label = r["label"][:30]
        closure = o.get("wound_closure_pct", 0)
        t50 = o.get("time_to_50pct_days")
        t50_str = f"{t50:.1f}" if t50 is not None else "N/A"
        peak = o.get("peak_inflammation", 0)
        scar = o.get("scar_magnitude", 0)
        print(f"  {label:<30} {closure:>7.1f}% {t50_str:>8} {peak:>10.4f} {scar:>8.3f}")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_experiment_file(experiment_path, runs_override=None, output_override=None, binary=None):
    """Load and run a single experiment file."""
    experiment = load_experiment(experiment_path)
    from scripts.study.experiment_evidence import run_complete_experiment
    if runs_override is not None:
        experiment["runs_per_config"] = runs_override
    study = experiment.get("study", "diabetic-wound")
    destination = output_override or os.path.join(
        resolve_study(study), "results", "experiments",
        experiment["name"].lower().replace(" ", "_") + "_" + time.strftime("%Y%m%d-%H%M%S"))
    return run_complete_experiment(experiment, destination, binary or os.path.join(REPO, "build", "skibidy"))


def main():
    parser = argparse.ArgumentParser(
        description="Run experiment experiments from TOML configs")
    parser.add_argument("experiments", nargs="+",
                        help="Path(s) to experiment TOML file(s)")
    parser.add_argument("--runs", type=int, default=None,
                        help="Override runs per config")
    parser.add_argument("--output", help="Fresh output directory (one experiment only)")
    parser.add_argument("--binary", help="Production binary to freeze (defaults to build/skibidy)")
    args = parser.parse_args()
    if args.output and len(args.experiments) != 1:
        parser.error("--output requires exactly one experiment")

    for path in args.experiments:
        if not os.path.isfile(path):
            print(f"ERROR: experiment file not found: {path}")
            sys.exit(1)

    for path in args.experiments:
        run_experiment_file(path, runs_override=args.runs, output_override=args.output, binary=args.binary)


if __name__ == "__main__":
    main()
