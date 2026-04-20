#!/usr/bin/env python3
"""Verify scheduled interventions through the maintained production binary.

Run with the BioDynaMo environment sourced. Each config, log, metric trajectory
and full-state witness is retained in --output; no project config is overwritten.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.validation.checkpoint_regression import CONFIG
from batch.checkpoint import read_checkpoint
from scripts.study.experiment_runner import load_experiment
from scripts.study.gen_treatment_schedule import encode_runtime_schedule, load_treatment


def event(name, value, step=0):
    parameters = f"[skin]\nwater_recovery_rate = {value}\n"
    return ("\n[[treatment_schedule]]\n"
            f"name = {json.dumps(name)}\nstart_day = {step * 0.1 / 24!r}\n"
            f"parameters = {json.dumps(parameters)}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build" / "skibidy")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    output = (args.output or Path(tempfile.mkdtemp(prefix="skibidy-treatment-regression-"))).resolve()
    output.mkdir(parents=True, exist_ok=True)
    boundary = 53
    runs = {}

    def run(name, text, prefix=False):
        directory = output / name
        directory.mkdir()
        (directory / "bdm.toml").write_text(text)
        env = {k: v for k, v in os.environ.items() if not k.startswith("SKIBIDY_CKPT_")}
        env.update(OMP_NUM_THREADS="1", OMP_DYNAMIC="FALSE",
                   SKIBIDY_STATE_SIGNATURE_FILE=str(directory / "state.txt"))
        if prefix:
            env.update(SKIBIDY_CKPT_SAVE_DIR=str(directory / "checkpoint"),
                       SKIBIDY_CKPT_STEP=str(boundary))
        result = subprocess.run([str(binary)], cwd=directory, env=env,
                                text=True, capture_output=True, timeout=180)
        (directory / "stdout.log").write_text(result.stdout)
        (directory / "stderr.log").write_text(result.stderr)
        assert result.returncode == 0, f"{name}: {result.stderr[-3000:]}"
        metrics = (directory / "results" / "skibidy" / "metrics.csv").read_bytes()
        rows = metrics.splitlines()[1:]
        assert rows and all(math.isfinite(float(cell)) for row in rows for cell in row.split(b",")), name
        assert len(rows) == (boundary if prefix else 120), name + ": incomplete trajectory"
        # Save exits at the boundary before the final-state witness writer.
        # Its checked checkpoint contains the same complete boundary fingerprint.
        state = (str(read_checkpoint(directory / "checkpoint")["state"]).encode()
                 if prefix else (directory / "state.txt").read_bytes())
        runs[name] = dict(metrics_sha256=hashlib.sha256(metrics).hexdigest(),
                          state_sha256=hashlib.sha256(state).hexdigest(), rows=len(rows))
        return metrics, state, result.stdout

    baseline = run("untreated", CONFIG)
    delayed_text = CONFIG + event("delayed", 0.2, boundary)
    delayed = run("delayed", delayed_text)
    earlier = [(a, b) for a, b in zip(baseline[0].splitlines()[1:], delayed[0].splitlines()[1:])
               if int(a.split(b",")[0]) < boundary]
    assert len(earlier) == boundary and all(a == b for a, b in earlier), "treatment changed pre-start metrics"
    assert baseline[0] != delayed[0] and baseline[1] != delayed[1], "no post-start biological effect"
    assert "at step 53" in delayed[2], "treatment did not execute at the requested boundary"
    saved_base = run("untreated-prefix", CONFIG, True)
    saved_delayed = run("delayed-prefix", delayed_text, True)
    assert saved_base[:2] == saved_delayed[:2], "complete pre-start boundary state differs"

    constant = run("constant-full", CONFIG.replace("water_recovery_rate = 0.005", "water_recovery_rate = 0.2"))
    day_zero = run("day-zero-full", CONFIG + event("full", 0.2))
    assert constant[:2] == day_zero[:2], "day-zero intervention differs from full constant treatment"
    low = run("day-zero-low", CONFIG + event("low", 0.05))
    forward = run("low-then-full", CONFIG + event("low", 0.05) + event("full", 0.2))
    reverse = run("full-then-low", CONFIG + event("full", 0.2) + event("low", 0.05))
    assert forward[:2] == day_zero[:2] and reverse[:2] == low[:2], "equal-time order was not respected"
    assert forward[0] != reverse[0], "order fixture did not affect actual biology"

    experiment = load_experiment(ROOT / "studies/diabetic-wound/experiments/proresolution_sensitivity.toml")
    for config in experiment["configs"]:
        encode_runtime_schedule(config["schedule"], experiment["study"])
    # A reduced diabetic runtime fixture tests all new parameter overlays through
    # the binary. It is not the 42-day replicated efficacy study.
    diabetic = CONFIG + ("\n[skin.diabetic]\nmode = true\n"
                         "efferocytosis_factor = 0.5\nresolution_factor = 0.3\n")
    for level in ("low", "medium", "high"):
        treatment = "resolvin_d1_" + level
        parameters = load_treatment(treatment, experiment["study"])
        constant_text = diabetic
        for path, value in parameters.items():
            key = path.rsplit(".", 1)[1]
            old = 0.5 if key == "efferocytosis_factor" else 0.3
            constant_text = constant_text.replace(f"{key} = {old}", f"{key} = {value}")
        expected = run(treatment + "-constant", constant_text)
        scheduled = run(treatment + "-scheduled", diabetic + encode_runtime_schedule(
            [{"treatment": treatment, "start_day": 0}], experiment["study"]))
        assert expected[:2] == scheduled[:2], treatment + ": overlay consumer differs"
        assert "at step 0" in scheduled[2], treatment + ": event was not applied"

    report = dict(passed=True, boundary=boundary, dt_hours=0.1, threads=1,
                  pre_start_rows=len(earlier), runs=runs, evidence=str(output), checks=[
                      "pre-start metrics and complete boundary state identical",
                      "event executes at step 53 and subsequent biology differs",
                      "day-zero equals constant full treatment",
                      "equal-time last writer wins in both declared orders",
                      "all six exploratory study schedules resolve and validate",
                      "all three Resolvin D1 overlays equal constant settings through the binary"])
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
