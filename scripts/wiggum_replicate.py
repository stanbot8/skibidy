"""Run N simulation replicates with distinct seeds and save each CSV.

Used by the wiggum loop to get multi-replicate signal for mechanistic
validation. Runs sequentially; full-config sim takes ~4 min each in WSL.

Usage:
    python3 scripts/wiggum_replicate.py [--n N] [--skin S] [--study ST] [--out-dir DIR]
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from batch import lib


def runtime_identity(binary):
    """Resolve and hash dependencies using the simulation's exact loader env."""
    binary = Path(binary).resolve()
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(binary.parent) + ":" + environment.get("LD_LIBRARY_PATH", "")
    resolved = subprocess.run(["ldd", str(binary)], env=environment,
                              capture_output=True, text=True, check=True)
    if "not found" in resolved.stdout:
        raise RuntimeError(f"unresolved runtime dependency: {resolved.stdout}")
    dependencies = []
    for line in resolved.stdout.splitlines():
        match = re.search(r"(?:=>\s+)?(/\S+)\s+\(", line)
        if match and Path(match[1]).is_file():
            path = Path(match[1]).resolve()
            dependencies.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    project = [item for item in dependencies if Path(item["path"]).name.startswith("libskibidy.so")]
    if len(project) != 1 or Path(project[0]["path"]).parent != binary.parent:
        raise RuntimeError("loader did not resolve libskibidy from the selected build directory")
    return {"binary": str(binary), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "dependencies": dependencies, "ldd": resolved.stdout,
            "dependency_evidence": "ldd resolution under the exact subprocess environment; not process mapping capture",
            "ld_library_path": environment["LD_LIBRARY_PATH"],
            "bdmsys": environment.get("BDMSYS")}, environment


def run_cohorts():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--skin", default="normal")
    p.add_argument("--study", default="wound")
    p.add_argument("--seed-start", type=int, default=42)
    p.add_argument("--out-dir", default="/tmp/replicate_runs")
    p.add_argument("--build-dir", default="build")
    p.add_argument("--matrix", action="store_true",
                   help="Run normal, diabetic and full-model baseline cohorts")
    args = p.parse_args()

    if args.n < 2:
        p.error("replicated validation requires at least two seeds")
    cohorts = [(args.skin, args.study)]
    if args.matrix:
        cohorts = [("normal", "wound"), ("diabetic", "diabetic-wound"),
                   ("normal", "full-model")]
    binary = os.path.abspath(os.path.join(args.build_dir, "skibidy"))
    runtime, environment = runtime_identity(binary)
    runtime.update({"cohorts": cohorts, "seeds": list(range(args.seed_start, args.seed_start + args.n))})
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "runtime.json"), "w") as f:
        json.dump(runtime, f, indent=2)
    for skin, study in cohorts:
      for i in range(args.n):
        seed = args.seed_start + i
        print(f"[{skin}/{study} replicate {i + 1}/{args.n}] seed={seed}", flush=True)
        lib.setup_run(skin=skin, study=study)
        lib.override_param("simulation.random_seed", seed)
        run_dir = os.path.abspath(os.path.join(args.out_dir, f"{skin}-{study}", f"seed{seed}"))
        os.makedirs(run_dir, exist_ok=False)
        lib.override_param("simulation.output_dir", run_dir)
        lib.override_param("visualization.export", False)
        lib.override_param("skin.headless", True)
        lib.override_param("skin.hot_reload", False)
        shutil.copy("bdm.toml", os.path.join(run_dir, "bdm.toml"))
        started = time.monotonic()
        with open(os.path.join(run_dir, "stdout.log"), "w") as stdout, \
             open(os.path.join(run_dir, "stderr.log"), "w") as stderr:
            r = subprocess.run([binary], cwd=lib.ROOT, stdout=stdout,
                               stderr=stderr, timeout=1200, env=environment)
        if r.returncode != 0:
            raise RuntimeError(f"simulation exit={r.returncode}; inspect {run_dir}")
        src = os.path.join(run_dir, "skibidy", "metrics.csv")
        with open(src) as f:
            rows = list(csv.DictReader(f))
        if not rows or any(not math.isfinite(float(v)) for row in rows for v in row.values()):
            raise RuntimeError(f"missing or nonfinite metrics: {src}")
        cfg = lib.parse_toml(os.path.join(run_dir, "bdm.toml"))
        expected_hours = cfg["skin"]["duration_days"] * 24
        # Metrics are sampled at intervals; permit one final sampling interval.
        interval_hours = cfg["skin"].get("metrics_interval_h", 10)
        final_hours = float(rows[-1]["time_h"])
        if final_hours < expected_hours - interval_hours - 1e-6:
            raise RuntimeError(f"incomplete run: {final_hours}h of {expected_hours}h")
        validation = subprocess.run(
            [sys.executable, "literature/validate_all.py", src,
             "--config", os.path.join(run_dir, "bdm.toml")],
            cwd=lib.ROOT, capture_output=True, text=True)
        with open(os.path.join(run_dir, "validation.txt"), "w") as f:
            f.write(validation.stdout + validation.stderr)
        with open(os.path.join(run_dir, "receipt.json"), "w") as f:
            json.dump({"seed": seed, "skin": skin, "study": study,
                       "seconds": time.monotonic() - started, "rows": len(rows),
                       "final_hours": final_hours,
                       "validation_exit": validation.returncode}, f, indent=2)
        print(f"  saved {src}; validation exit={validation.returncode}", flush=True)

    print("DONE")


def main():
    config = Path(lib.ROOT) / "bdm.toml"
    original = config.read_bytes() if config.exists() else None
    previous_cwd = Path.cwd()
    try:
        os.chdir(lib.ROOT)
        run_cohorts()
    finally:
        if original is None:
            config.unlink(missing_ok=True)
        else:
            config.write_bytes(original)
        os.chdir(previous_cwd)


if __name__ == "__main__":
    main()
