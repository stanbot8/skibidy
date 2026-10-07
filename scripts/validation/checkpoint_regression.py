#!/usr/bin/env python3
"""Exercise exact replay and treatment forks through the production binary.

Run in the sourced BioDynaMo Linux environment. Evidence remains in --output.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from batch.checkpoint import read_checkpoint, fork_config, fork_from_checkpoint, checksum

CONFIG = '''[simulation]
random_seed = 20261007
output_dir = "results"
[visualization]
export = false
[geometry]
patch_um = 2000.0
depth_um = 1500.0
height_um = 1500.0
margin_um = 500.0
um_per_unit = 50.0
voxel_um = 250.0
[skin]
duration_days = 0.5
metrics_interval_h = 0.1
headless = true
hot_reload = false
metrics_autoopen = false
subcycle_slow = 10
subcycle_medium = 5
derived_fields_subcycle = 5
migration_subcycle = 3
homeostasis_subcycle = 3
water_recovery_rate = 0.005
[skin.heterogeneity]
cycle_distribution = "lognormal"
cycle_cv = 0.2
[skin.basement_membrane]
enabled = true
wound_damage = 1.0
repair_rate = 0.005
[skin.wound]
enabled = true
trigger_h = 0.2
radius = 8.0
dissolution_closure_pct = 0
[skin.immune]
neutrophil_spawn_delay_h = 0.1
neutrophil_spawn_waves = 3
neutrophil_spawn_window_h = 2.0
macrophage_spawn_delay_h = 0.4
macrophage_spawn_rate = 0.9
macrophage_spawn_threshold = 0.00001
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build" / "skibidy")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix="skibidy-checkpoint-regression-"))
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    binary = args.binary.resolve()
    checkpoint = output / "checkpoint"
    boundary = 53  # off every configured slow/medium/migration subcycle
    checks = []

    def run(name, text=CONFIG, extra=None, expected=None):
        directory = output / name
        directory.mkdir()
        (directory / "bdm.toml").write_text(text)
        env = {k: v for k, v in os.environ.items() if not k.startswith("SKIBIDY_CKPT_")}
        env.update(OMP_NUM_THREADS="1", OMP_DYNAMIC="FALSE",
                   SKIBIDY_STATE_SIGNATURE_FILE=str(directory / "state.txt"))
        env.update(extra or {})
        result = subprocess.run([str(binary)], cwd=directory, env=env,
                                text=True, capture_output=True, timeout=180)
        (directory / "stdout.log").write_text(result.stdout)
        (directory / "stderr.log").write_text(result.stderr)
        if expected is None:
            assert result.returncode == 0, f"{name} failed: {result.stderr[-3000:]}"
        else:
            assert result.returncode != 0 and expected in result.stderr, (name, result.returncode, result.stderr[-1500:])
            checks.append(name)
        return directory

    def metrics(directory):
        return (directory / "results" / "skibidy" / "metrics.csv").read_bytes()

    full = run("uninterrupted")
    saved = run("saved", extra={"SKIBIDY_CKPT_SAVE_DIR": str(checkpoint), "SKIBIDY_CKPT_STEP": str(boundary)})
    record = read_checkpoint(checkpoint)
    assert record["step"] == boundary
    resumed = run("resumed", extra={"SKIBIDY_CKPT_LOAD_DIR": str(checkpoint)})
    assert metrics(full) == metrics(resumed), "resumed metrics trajectory differs"
    assert (full / "state.txt").read_bytes() == (resumed / "state.txt").read_bytes(), "resumed state witness differs"
    assert metrics(full).startswith(metrics(saved)), "save ran beyond the actual prefix"
    with (saved / "results" / "skibidy" / "metrics.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    recruitment = [key for key in rows[0] if "neutrophil" in key or "macrophage" in key]
    assert recruitment and any(float(row[key]) > 0 for row in rows for key in recruitment), "fixture lacks immune recruitment"
    membrane_values = [float(row["mean_basement_membrane_wound"]) for row in rows]
    assert min(membrane_values) < max(membrane_values), "fixture lacks membrane damage/repair"
    checks.append("heterogeneous agents, recruitment, membrane dynamics: exact trajectory and agent/RNG/grid/derived witness at step 53")

    for edge in (0, 120):
        edge_checkpoint = output / f"checkpoint-{edge}"
        run(f"saved-{edge}", extra={"SKIBIDY_CKPT_SAVE_DIR": str(edge_checkpoint),
                                    "SKIBIDY_CKPT_STEP": str(edge)})
        edge_resume = run(f"resumed-{edge}", extra={"SKIBIDY_CKPT_LOAD_DIR": str(edge_checkpoint)})
        assert metrics(edge_resume) == metrics(full), f"boundary {edge} trajectory differs"
        assert (edge_resume / "state.txt").read_bytes() == (full / "state.txt").read_bytes()
    checks.append("zero and final-step boundaries reproduce the complete trajectory")

    history_text = CONFIG + ('\n[[treatment_schedule]]\nname = "earlier-treatment"\n'
                             'start_day = 0.02\nparameters = "[skin]\\nwater_recovery_rate=0.01\\n"\n')
    history_checkpoint = output / "history-checkpoint"
    history_full = run("history-uninterrupted", history_text)
    run("history-saved", history_text, {"SKIBIDY_CKPT_SAVE_DIR": str(history_checkpoint),
                                       "SKIBIDY_CKPT_STEP": str(boundary)})
    history_resume = run("history-resumed", history_text, {"SKIBIDY_CKPT_LOAD_DIR": str(history_checkpoint)})
    assert metrics(history_full) == metrics(history_resume)
    assert (history_full / "state.txt").read_bytes() == (history_resume / "state.txt").read_bytes()
    run("changed-history", history_text.replace("water_recovery_rate=0.01", "water_recovery_rate=0.02"),
        {"SKIBIDY_CKPT_LOAD_DIR": str(history_checkpoint)}, "changes treatment history")
    checks.append("applied treatment history and schedule cursor replay exactly")

    fork_text = fork_config(record, overrides={"skin.water_recovery_rate": 0.2})
    treated = run("scheduled-uninterrupted", fork_text)
    forked = run("forked", fork_text, {"SKIBIDY_CKPT_LOAD_DIR": str(checkpoint)})
    assert metrics(treated) == metrics(forked), "fork differs from scheduled uninterrupted biology"
    assert (treated / "state.txt").read_bytes() == (forked / "state.txt").read_bytes()
    untreated_lines = metrics(full).splitlines()
    treated_lines = metrics(treated).splitlines()
    for baseline, changed in zip(untreated_lines[1:], treated_lines[1:]):
        if float(baseline.split(b",")[0]) < boundary * 0.1:
            assert baseline == changed, "future event changed earlier biology"
    assert metrics(treated) != metrics(full), "treatment did not affect actual biology"
    checks.append("boundary treatment fork equals scheduled trajectory; prefix unchanged, later divergence")

    # Exercise the maintained Python consumer and its finite/complete metric gate.
    success, _ = fork_from_checkpoint(checkpoint,
        overrides={"skin.water_recovery_rate": 0.2}, output_path=output / "batch-fork")
    assert success and metrics(output / "batch-fork") == metrics(treated)
    checks.append("batch fork validates complete finite metrics through actual binary")

    load = {"SKIBIDY_CKPT_LOAD_DIR": str(checkpoint)}
    run("changed-config", CONFIG.replace("20261007", "20261008"), load, "configuration mismatch")
    run("two-threads", extra={**load, "OMP_NUM_THREADS": "2"}, expected="OMP_NUM_THREADS=1")
    run("early-fork", fork_text.replace(f"start_day = {boundary * 0.1 / 24!r}", "start_day = 0.01"), load, "changes treatment history")
    run("invalid-step", extra={"SKIBIDY_CKPT_SAVE_DIR": str(output / "invalid"), "SKIBIDY_CKPT_STEP": "53garbage"}, expected="invalid unsigned")
    data = (checkpoint / "checkpoint.bin").read_bytes()
    for name, broken in [("truncated", data[:-1]), ("corrupt", data[:45] + bytes([data[45] ^ 1]) + data[46:]), ("old-format", b"old field only")]:
        directory = output / (name + "-checkpoint")
        directory.mkdir()
        (directory / "checkpoint.bin").write_bytes(broken)
        run(name, extra={"SKIBIDY_CKPT_LOAD_DIR": str(directory)}, expected="checkpoint")
    wrong_runtime = bytearray(data)
    wrong_runtime[16] ^= 1
    wrong_runtime[-8:] = struct.pack("<Q", checksum(wrong_runtime[:-8]))
    incompatible = output / "runtime-checkpoint"
    incompatible.mkdir()
    (incompatible / "checkpoint.bin").write_bytes(wrong_runtime)
    run("incompatible-runtime", extra={"SKIBIDY_CKPT_LOAD_DIR": str(incompatible)}, expected="runtime mismatch")
    wrong_state = bytearray(data)
    wrong_state[24] ^= 1
    wrong_state[-8:] = struct.pack("<Q", checksum(wrong_state[:-8]))
    state_checkpoint = output / "state-checkpoint"
    state_checkpoint.mkdir()
    (state_checkpoint / "checkpoint.bin").write_bytes(wrong_state)
    run("boundary-state-mismatch", extra={"SKIBIDY_CKPT_LOAD_DIR": str(state_checkpoint)}, expected="boundary state mismatch")
    report = dict(checks=checks, boundary=boundary, threads=1, evidence=str(output), passed=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
