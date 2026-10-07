#!/usr/bin/env python3
"""Multi-run consensus: same config, multiple seeds.

Runs N simulations, computes mean/std across runs, writes
validation-compatible consensus metrics, and optionally validates.

Usage:
    python3 batch/batch.py                         # 20 runs, default config
    python3 batch/batch.py -n 5                    # 5 runs
    python3 batch/batch.py -n 10 --study wound     # 10 runs, wound study
    python3 batch/batch.py --skin aged --study wound --validate
    python3 batch/batch.py --skin diabetic --study diabetic-wound --validate
"""

import argparse
import csv
import json
import os
import secrets
import shutil
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from batch import lib


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Multi-run consensus (same config, different seeds)")
    parser.add_argument("-n", "--num-runs", type=int, default=20,
                        help="Number of runs (default: 20)")
    parser.add_argument("--study", type=str, default=None)
    parser.add_argument("--skin", type=str, default=None)
    parser.add_argument("--site", type=str, default=None,
                        help="Body site (e.g. foot_plantar, scalp)")
    parser.add_argument("--treatment", type=str, default=None,
                        help="Treatment overlay (e.g. anti_tnf, tocilizumab)")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation on consensus")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip validation (default: skip)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Base random seed (run i uses seed+i for reproducibility)")
    args = parser.parse_args(argv)
    if args.num_runs < 1:
        parser.error("Number of runs must be positive")
    if args.seed is not None and (args.seed < 0 or args.seed + args.num_runs > 2 ** 32):
        parser.error("Seeds must fit unsigned 32-bit integers")
    do_validate = args.validate and not args.no_validate

    study_label = args.study or "default"
    skin_label = args.skin or "default"
    study_dir = os.path.join(lib.resolve_study(args.study) if args.study else
                             os.path.join(lib.ROOT, "studies", "default"), "results")
    result_dir = study_dir
    # Archive the previous cohort before starting. A failed replacement must
    # never leave old consensus at the current result paths.
    old = [name for name in ("raw", "metrics.csv", "consensus.csv", "run-config.toml",
                            "seed_manifest.csv", "cohort.json")
           if os.path.exists(os.path.join(result_dir, name))]
    if old:
        archive = os.path.join(result_dir, "archive", uuid.uuid4().hex)
        os.makedirs(archive)
        for name in old:
            os.replace(os.path.join(result_dir, name), os.path.join(archive, name))
    raw_dir = os.path.join(result_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    cohort = {"id": uuid.uuid4().hex, "status": "running", "requested_runs": args.num_runs,
              "study": args.study, "profile": args.skin or (lib.study_profile(args.study) if args.study else None),
              "runs": []}
    def save_manifest():
        path = os.path.join(result_dir, "cohort.json")
        with open(path + ".tmp", "w") as f:
            json.dump(cohort, f, indent=2, allow_nan=False)
        os.replace(path + ".tmp", path)
        fields = ("run", "seed", "status", "error", "returncode", "config_sha256", "metrics_sha256")
        with open(os.path.join(result_dir, "seed_manifest.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(cohort["runs"])
    save_manifest()

    print(f"=== Batch: {args.num_runs} runs ===")
    print(f"  Skin: {skin_label}, Study: {study_label}")
    if args.seed is not None:
        print(f"  Base seed: {args.seed}")
    print(f"  Output: {result_dir}/")
    print()

    # Setup config once
    try:
        lib.setup_run(args.skin, args.site, args.study, args.treatment)
        lib.build_if_needed()
    except (Exception, SystemExit) as error:
        cohort.update(status="failed", error=str(error))
        save_manifest()
        return 1

    # Run simulations
    csv_paths = []
    t_start = time.time()
    for i in range(args.num_runs):
        # Set reproducible seed: base_seed + run_index
        run_seed = (args.seed + i) if args.seed is not None else secrets.randbelow(2 ** 32)

        label = f"[{i + 1}/{args.num_runs}]"
        print(f"  {label}", end=" ", flush=True)
        run_dir = os.path.join(raw_dir, f"run_{i:03d}")
        lib._last_result.clear()
        try:
            lib.setup_run(args.skin, args.site, args.study, args.treatment)
            lib.override_param("simulation.random_seed", run_seed)
            ok, elapsed = lib.run_simulation(output_path=run_dir)
        except (Exception, SystemExit) as error:
            ok, elapsed = False, 0
            lib._last_result.update(success=False, error=str(error), returncode=None,
                                    config_sha256=lib.file_sha256(os.path.join(run_dir, "run-config.toml")),
                                    metrics_sha256=lib.file_sha256(os.path.join(run_dir, "skibidy", "metrics.csv")))
        cohort["runs"].append(dict(lib._last_result, run=i, seed=run_seed,
                                  status="ok" if ok else "failed", elapsed_seconds=elapsed))
        save_manifest()

        if not ok:
            print(f"FAILED ({elapsed:.0f}s)")
            continue

        csv_path = lib.get_metrics_path()
        if not os.path.isfile(csv_path):
            cohort["runs"][-1].update(success=False, status="failed", error="metrics file missing")
            save_manifest()
            print(f"FAILED (no metrics)")
            continue

        csv_paths.append(csv_path)
        print(f"OK ({elapsed:.0f}s)")

    t_total = time.time() - t_start
    print(f"\n{len(csv_paths)}/{args.num_runs} completed "
          f"({t_total:.0f}s total, {t_total / max(1, args.num_runs):.0f}s avg)")

    if len(csv_paths) != args.num_runs:
        cohort["status"] = "failed"
        save_manifest()
        print(f"Incomplete cohort: {len(csv_paths)}/{args.num_runs} successful runs; no consensus produced.")
        return 1

    # Consensus interpretation needs the exact enabled mechanisms and profile.
    shutil.copy2(os.path.join(lib.ROOT, "bdm.toml"), os.path.join(result_dir, "run-config.toml"))

    # Compute consensus
    try:
        mean_data, std_data = lib.aggregate_csvs(csv_paths)
    except (OSError, ValueError, ArithmeticError) as error:
        cohort.update(status="failed", error=str(error))
        save_manifest()
        return 1
    columns = list(mean_data.keys())

    # Write validation-compatible metrics.csv (means only)
    lib.write_csv(mean_data, os.path.join(result_dir, "metrics.csv"), columns)

    # Write full consensus with std
    full_path = os.path.join(result_dir, "consensus.csv")
    full_data = {}
    for col in columns:
        full_data[col] = mean_data[col]
        full_data[f"{col}_std"] = std_data[col]
    full_cols = []
    for col in columns:
        full_cols.append(col)
        full_cols.append(f"{col}_std")
    lib.write_csv(full_data, full_path, full_cols)
    cohort["status"] = "complete"
    cohort["metrics_sha256"] = lib.file_sha256(os.path.join(result_dir, "metrics.csv"))
    cohort["consensus_sha256"] = lib.file_sha256(full_path)
    save_manifest()

    print(f"Consensus: {full_path}")
    print(f"Metrics:   {os.path.join(result_dir, 'metrics.csv')}")

    # Validate
    if do_validate:
        print("\n=== Validation ===")
        rc = lib.run_validation(os.path.join(result_dir, "metrics.csv"))
        cohort["validation_returncode"] = rc
        save_manifest()
        if rc:
            return rc

    print(f"\nResults: {result_dir}/")
    return 0


if __name__ == "__main__":
    config_path = os.path.join(lib.ROOT, "bdm.toml")
    with open(config_path, "rb") as f:
        original_config = f.read()
    try:
        sys.exit(main())
    finally:
        with open(config_path, "wb") as f:
            f.write(original_config)
