"""Verified replay checkpoint commands. Replay reconstructs the prefix; no speedup.

python3 batch/checkpoint.py save --step 700 --dir checkpoints/step_700
python3 batch/checkpoint.py fork --checkpoint checkpoints/step_700 --treatments npwt
"""

import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from batch.lib import merge_config, apply_profile, apply_study, override_param, build_if_needed, validate_run_metrics
from scripts.study.gen_treatment_schedule import encode_runtime_schedule, validate_runtime_parameters


def checksum(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return value


def read_checkpoint(directory):
    """Validate the same immutable format used by the C++ reader."""
    path = Path(directory) / "checkpoint.bin"
    if path.stat().st_size > 16 * 1024 * 1024 + 48:
        raise ValueError("checkpoint too large")
    data = path.read_bytes()
    if len(data) < 48 or data[:8] != b"SKRPLY02":
        raise ValueError("unsupported or corrupt checkpoint")
    step, runtime, state, length = struct.unpack_from("<QQQQ", data, 8)
    if length > 16 * 1024 * 1024 or len(data) != length + 48:
        raise ValueError("checkpoint length mismatch")
    if struct.unpack_from("<Q", data, len(data) - 8)[0] != checksum(data[:-8]):
        raise ValueError("checkpoint integrity checksum mismatch")
    text = data[40:-8].decode("utf-8")
    return dict(step=step, runtime=runtime, state=state, text=text,
                config=tomllib.loads(text))


def _run_binary(config_text, env_extra=None, output_path=None, complete=True):
    """Isolate configuration and output; preserve process/config evidence."""
    if output_path is None:
        (ROOT / "output").mkdir(exist_ok=True)
        output_path = tempfile.mkdtemp(prefix="checkpoint-run-", dir=ROOT / "output")
    output = Path(output_path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = tomllib.loads(config_text)
    base = Path(config.get("simulation", {}).get("output_dir", "output"))
    base = (base if base.is_absolute() else output / base).resolve()
    if not base.is_relative_to(output):
        raise ValueError("checkpoint simulation.output_dir must stay inside the run directory")
    # A run directory owns only this run. Refuse stale evidence rather than erase it.
    config_path = output / "bdm.toml"
    if config_path.exists() or (output / "results" / "skibidy" / "metrics.csv").exists():
        raise ValueError(f"run output already exists: {output}")
    config_path.write_text(config_text, encoding="utf-8")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("SKIBIDY_CKPT_")}
    env.update(OMP_NUM_THREADS="1", OMP_DYNAMIC="FALSE")
    env.update(env_extra or {})
    started = time.monotonic()
    result = subprocess.run([str(ROOT / "build" / "skibidy")], cwd=output,
                            capture_output=True, text=True, env=env)
    elapsed = time.monotonic() - started
    for stream in ("stdout", "stderr"):
        (output / (stream + ".log")).write_text(getattr(result, stream) or "", encoding="utf-8")
    success = result.returncode == 0
    if complete and success:
        try:
            validate_run_metrics(base / "skibidy" / "metrics.csv", config)
        except (OSError, ValueError, KeyError) as error:
            print(f"Invalid checkpoint run: {error}", file=sys.stderr)
            success = False
    if not success:
        print(f"Checkpoint run failed; evidence: {output}", file=sys.stderr)
        print("\n".join(result.stderr.splitlines()[-5:]), file=sys.stderr)
    return success, elapsed


def prepare_config(profile="diabetic", study="diabetic-wound"):
    merge_config()
    if profile:
        apply_profile(profile)
    if study:
        apply_study(study)
    override_param("visualization.export", False)
    override_param("skin.headless", True)
    override_param("skin.hot_reload", False)
    return (ROOT / "bdm.toml").read_text(encoding="utf-8")


def save_checkpoint(step, ckpt_dir, profile="diabetic", study="diabetic-wound"):
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("checkpoint step must be a nonnegative integer")
    directory = Path(ckpt_dir).resolve()
    if (directory / "checkpoint.bin").exists():
        raise ValueError("checkpoint already exists")
    directory.mkdir(parents=True, exist_ok=True)
    original_path = ROOT / "bdm.toml"
    original = original_path.read_bytes() if original_path.exists() else None
    try:
        text = prepare_config(profile, study)
    finally:
        if original is not None:
            original_path.write_bytes(original)
        else:
            original_path.unlink(missing_ok=True)
    success, elapsed = _run_binary(text, {
        "SKIBIDY_CKPT_SAVE_DIR": str(directory), "SKIBIDY_CKPT_STEP": str(step)},
        directory / "save-run", complete=False)
    if success:
        success = read_checkpoint(directory)["step"] == step
    print(f"Checkpoint step {step}: {'OK' if success else 'FAILED'} ({elapsed:.1f}s)")
    return success


def fork_config(record, treatments=None, overrides=None, study="diabetic-wound"):
    """Add live treatment events at the actual boundary; never alter the prefix."""
    # Simulate's set_param owns this fixed step size (overrides are forbidden).
    dt = 0.1
    day = record["step"] * dt / 24
    text = record["text"]
    names = [name for item in (treatments or []) for name in item.split(",") if name]
    text += encode_runtime_schedule([dict(treatment=name, start_day=day)
                                     for name in names], study)
    if overrides:
        partial = {}
        for key, value in overrides.items():
            target = partial
            parts = key.split(".")
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value
        validate_runtime_parameters(partial)
        # TOML dotted keys within the embedded root table preserve owner paths.
        payload = "\n".join(f"{key} = {json.dumps(value)}" for key, value in overrides.items())
        text += (f'\n[[treatment_schedule]]\nname = "fork-overrides"\n'
                 f'start_day = {day!r}\nparameters = {json.dumps(payload)}\n')
    return text


def fork_from_checkpoint(ckpt_dir, treatments=None, overrides=None,
                         profile=None, study="diabetic-wound", output_path=None):
    if profile is not None:
        raise ValueError("a fork inherits its saved profile; profile overrides are incompatible")
    directory = Path(ckpt_dir).resolve()
    record = read_checkpoint(directory)
    return _run_binary(fork_config(record, treatments, overrides, study),
                       {"SKIBIDY_CKPT_LOAD_DIR": str(directory)}, output_path)


def main():
    parser = argparse.ArgumentParser(description="Verified replay checkpoints (no speedup)")
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("save", help="Stop and save at an exact step boundary")
    save.add_argument("--step", type=int, required=True)
    save.add_argument("--dir")
    save.add_argument("--profile", default="diabetic")
    save.add_argument("--study", default="diabetic-wound")
    fork = sub.add_parser("fork", help="Replay the prefix and continue with boundary treatments")
    fork.add_argument("--checkpoint", required=True)
    fork.add_argument("--treatments", nargs="+", default=[])
    fork.add_argument("--study", default="diabetic-wound")
    fork.add_argument("--output", help="New isolated run directory")
    args = parser.parse_args()
    try:
        build_if_needed()
        if args.command == "save":
            success = save_checkpoint(args.step, args.dir or ROOT / "checkpoints" / f"step_{args.step}",
                                      args.profile, args.study)
        else:
            success, elapsed = fork_from_checkpoint(args.checkpoint, treatments=args.treatments,
                                                    study=args.study, output_path=args.output)
            print(f"Fork: {'OK' if success else 'FAILED'} ({elapsed:.1f}s)")
        return 0 if success else 1
    except (OSError, ValueError) as error:
        print(f"Checkpoint failure: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
