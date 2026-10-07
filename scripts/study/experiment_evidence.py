"""Isolated, frozen-binary cohorts and replicate-level treatment evidence."""

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

from batch.lib import (aggregate_csvs, extract_outcome, load_csv, validate_run_metrics, get_tomllib,
                       write_csv, resolve_study, study_profile)
from scripts.config.apply_preset import apply_overrides, parse_overrides
from scripts.study.gen_treatment_schedule import encode_runtime_schedule, resolve_treatment

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def set_parameter(path, dotted, value):
    """Set a scalar without adding duplicate tables or changing neighboring keys."""
    section, key = dotted.rsplit(".", 1)
    encoded = json.dumps(value)  # JSON scalar spelling is also valid TOML.
    lines = Path(path).read_text().splitlines(keepends=True)
    current = ""
    header = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            current = stripped[1:-1] if not stripped.startswith("[[") else ""
            if current == section:
                header = i
        elif current == section and re.match(rf"^{re.escape(key)}\s*=", stripped):
            lines[i] = f"{key} = {encoded}\n"
            break
    else:
        if header is None:
            lines.extend([f"\n[{section}]\n", f"{key} = {encoded}\n"])
        else:
            lines.insert(header + 1, f"{key} = {encoded}\n")
    Path(path).write_text("".join(lines))


def prepare_config(cfg, experiment, directory, seed):
    """Use maintained merge/overlay functions, writing only to this run's CWD."""
    from scripts.study.experiment_runner import _strip_viz
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "bdm.toml"
    # Calling merge() directly avoids generated-header writes performed by its CLI.
    result = subprocess.run(
        [sys.executable, "-c", "from scripts.config.merge_config import merge; import sys; merge(*sys.argv[1:])",
         str(ROOT / "bdm.core.toml"), str(ROOT / "modules"), str(path)],
        cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"config merge failed: {result.stderr}")
    study = cfg.get("study") or experiment.get("study")
    profile = cfg.get("profile") or experiment.get("profile") or (study_profile(study) if study else None)
    overlays = []
    if profile:
        overlays.append(ROOT / "profiles" / f"{profile}.toml")
    if study:
        overlays.append(Path(resolve_study(study)) / "preset.toml")
    overlays.extend(Path(resolve_treatment(name, study)) for name in cfg.get("treatments", []))
    overlays.extend(ROOT / name for name in cfg.get("extra_overlays", []))
    for overlay in overlays:
        if not overlay.is_file():
            raise ValueError(f"missing overlay: {overlay}")
        apply_overrides(path, parse_overrides(overlay))
    for key, value in {**experiment.get("overrides", {}), **cfg.get("overrides", {})}.items():
        set_parameter(path, key, value)
    _strip_viz(path)
    for key, value in {"simulation.random_seed": seed,
                       "simulation.output_dir": str(directory / "output"),
                       "skin.headless": True, "skin.hot_reload": False,
                       "visualization.export": False}.items():
        set_parameter(path, key, value)
    save_analysis_identity(path, cfg, experiment, profile, study)
    with path.open("a") as f:
        f.write(encode_runtime_schedule(cfg.get("schedule", []), study))
    shutil.copyfile(path, directory / "run-config.toml")
    return path


def save_analysis_identity(path, cfg, experiment, profile, study):
    from literature.lib import condition_from_config
    config = get_tomllib().loads(Path(path).read_text())
    active = condition_from_config(dict(config, analysis={}))
    fallback = {"aged": "aging", "aged_diabetic": "diabetic", "healthy": "normal"}.get(
        profile, profile or "normal")
    condition = cfg.get("condition") or experiment.get("condition") or (
        active if active != "normal" else fallback)
    for key, value in {"profile": profile or "normal", "study": study or "",
                       "condition": condition}.items():
        set_parameter(path, "analysis." + key, value)


def scalar_outcomes(data):
    outcomes = {}
    for name, column, measure in [
        ("wound_closure_pct", "wound_closure_pct", "final"),
        ("peak_inflammation", "mean_infl_wound", "peak"),
        ("scar_magnitude", "scar_magnitude", "final"),
        ("peak_neutrophils", "n_neutrophils", "peak"),
        ("peak_macrophages", "n_macrophages", "peak"),
        ("peak_collagen", "mean_collagen_wound", "peak"),
        ("time_to_50pct_h", "wound_closure_pct", "time_to_50"),
        ("time_to_90pct_h", "wound_closure_pct", "time_to_90")]:
        if column in data:
            value = extract_outcome(data, column, measure)
            outcomes[name] = value if value is not None and math.isfinite(value) else None
    for key in ["time_to_50pct_h", "time_to_90pct_h"]:
        value = outcomes.get(key)
        outcomes[key.replace("_h", "_days")] = None if value is None else value / 24
    return outcomes


def summarize_replicates(records):
    """Extract before averaging; never turn censored runs into reached thresholds."""
    summary = {}
    for key in sorted(set().union(*(record["outcomes"] for record in records))):
        values = [record["outcomes"].get(key) for record in records]
        observed = [value for value in values if value is not None]
        summary[key] = statistics.mean(observed) if len(observed) == len(records) else None
        summary[key + "_n_observed"] = len(observed)
        summary[key + "_sd"] = statistics.stdev(observed) if len(observed) > 1 else None
    return summary


def freeze_binary(output, binary):
    target = Path(output) / "binary"
    target.mkdir()
    binary = Path(binary).resolve()
    sources = [binary] + sorted(binary.parent.glob("libskibidy.so*"))
    frozen = []
    for source in sources:
        dest = target / source.name
        shutil.copy2(source, dest)
        frozen.append({"source": str(source), "path": str(dest), "sha256": digest(dest)})
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(target) + ":" + environment.get("LD_LIBRARY_PATH", "")
    ldd = subprocess.run(["ldd", str(target / binary.name)], env=environment,
                         capture_output=True, text=True)
    if ldd.returncode or "not found" in ldd.stdout:
        raise RuntimeError(f"frozen binary dependency check failed: {ldd.stdout} {ldd.stderr}")
    dependencies = []
    for line in ldd.stdout.splitlines():
        match = re.search(r"(?:=>\s+)?(/\S+)\s+\(", line)
        if match and Path(match[1]).is_file():
            dependencies.append({"path": match[1], "sha256": digest(match[1])})
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    (target / "source.diff").write_bytes(diff)
    source_paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--",
         "src", "modules", "CMakeLists.txt"], cwd=ROOT).decode().split("\0")
    inventory = []
    for name in sorted(set(source_paths)):
        source = ROOT / name
        if source.is_file() and (source.suffix in {".h", ".cc", ".cpp", ".inc", ".in", ".cmake", ".toml"}
                                 or source.name == "CMakeLists.txt"):
            dest = target / "source" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            inventory.append({"path": name, "sha256": digest(dest)})
    save_json(target / "source-inventory.json", inventory)
    receipt = {"git_head": head, "source_diff_sha256": digest(target / "source.diff"),
               "source_inventory_sha256": digest(target / "source-inventory.json"),
               "project_files": frozen, "dependencies": dependencies, "ldd": ldd.stdout,
               "threads": 1, "created_unix_seconds": time.time()}
    save_json(target / "receipt.json", receipt)
    return target / binary.name, receipt, environment


def write_replicate_tables(results, output):
    records = [record for result in results for record in result["replicates"]]
    keys = sorted(set().union(*(record["outcomes"] for record in records)))
    with (Path(output) / "replicate_outcomes.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["config", "seed"] + keys)
        for record in records:
            writer.writerow([record["label"], record["seed"]] + [record["outcomes"].get(k) for k in keys])
    baseline = {record["seed"]: record for record in results[0]["replicates"]}
    with (Path(output) / "paired_deltas.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["config", "outcome", "n_pairs", "mean_delta", "sd_delta", "min_delta", "max_delta"])
        for result in results[1:]:
            if {r["seed"] for r in result["replicates"]} != set(baseline):
                raise ValueError("paired comparison has mismatched seeds")
            for key in keys:
                pairs = [(r["outcomes"].get(key), baseline[r["seed"]]["outcomes"].get(key))
                         for r in result["replicates"]]
                deltas = [a - b for a, b in pairs if a is not None and b is not None]
                complete = len(deltas) == len(baseline)
                writer.writerow([result["label"], key, len(deltas),
                                 statistics.mean(deltas) if complete else None,
                                 statistics.stdev(deltas) if complete and len(deltas) > 1 else None,
                                 min(deltas) if complete else None, max(deltas) if complete else None])


def write_figures(results, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for result in results:
        data, sd = result["mean_data"], result["std_data"]
        days = [value / 24 for value in data["time_h"]]
        for axis, column, ylabel in zip(axes, ["wound_closure_pct", "mean_infl_wound"],
                                        ["Wound closure (%)", "Mean wound inflammation (model units)"]):
            if column not in data:
                continue
            line, = axis.plot(days, data[column], label=result["label"])
            spread = sd[column]
            axis.fill_between(days, [m - s for m, s in zip(data[column], spread)],
                              [m + s for m, s in zip(data[column], spread)], alpha=.12, color=line.get_color())
            axis.set(xlabel="Simulation day", ylabel=ylabel)
            axis.grid(alpha=.2)
    axes[0].set_ylim(0, 100)
    axes[1].legend(fontsize=8)
    fig.suptitle("Exploratory mechanism sensitivity: mean ± population SD across paired seeds\nAssumed effects; no clinical dose calibration")
    fig.tight_layout()
    fig.savefig(Path(output) / "trajectories.png", dpi=160)
    fig.savefig(Path(output) / "trajectories.svg")
    plt.close(fig)


def run_complete_experiment(experiment, output, binary):
    """Freeze inputs before execution; publish summaries only for the full cohort."""
    from scripts.study.experiment_runner import write_comparison, write_summary, print_results_table
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    n_runs = experiment["runs_per_config"]
    if isinstance(n_runs, bool) or not isinstance(n_runs, int) or n_runs < 1:
        raise ValueError("runs_per_config must be a positive integer")
    frozen, receipt, env = freeze_binary(output, binary)
    env["OMP_NUM_THREADS"] = "1"
    for key in list(env):
        if key.startswith("SKIBIDY_CKPT_"):
            del env[key]
    manifest = {"status": "preparing", "experiment": experiment, "binary_receipt": receipt,
                "requested_runs": len(experiment["configs"]) * n_runs, "runs": []}
    manifest_path = output / "manifest.json"
    save_json(manifest_path, manifest)
    t0 = time.time()
    try:
        for arm, cfg in enumerate(experiment["configs"]):
            for i in range(n_runs):
                seed = experiment.get("seed", 42) + i
                directory = output / "raw" / f"arm{arm:02d}_seed{seed}"
                config = prepare_config(cfg, experiment, directory, seed)
                manifest["runs"].append({"label": cfg["label"], "arm": arm, "seed": seed,
                                         "config": str(config), "config_sha256": digest(config),
                                         "directory": str(directory), "status": "pending"})
                save_json(manifest_path, manifest)
        manifest["status"] = "running"
        for record in manifest["runs"]:
            if digest(record["config"]) != record["config_sha256"]:
                record["status"] = "failed"
                raise RuntimeError(f"saved config changed: {record['config']}")
            for item in receipt["project_files"] + receipt["dependencies"]:
                if digest(item["path"]) != item["sha256"]:
                    raise RuntimeError(f"binary or dependency changed: {item['path']}")
            directory = Path(record["directory"])
            record["status"] = "running"
            save_json(manifest_path, manifest)
            started = time.time()
            with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
                process = subprocess.run([str(frozen)], cwd=directory, env=env, stdout=stdout, stderr=stderr)
            record["exit_code"] = process.returncode
            record["elapsed_seconds"] = time.time() - started
            if process.returncode:
                record["status"] = "failed"
                raise RuntimeError(f"{record['label']} seed {record['seed']}: exit {process.returncode}")
            metrics = directory / "output" / "skibidy" / "metrics.csv"
            import tomllib
            config = tomllib.loads(Path(record["config"]).read_text())
            try:
                count, last = validate_run_metrics(metrics, config)
            except Exception:
                record["status"] = "failed"
                raise
            record.update(status="complete", metrics=str(metrics), metrics_sha256=digest(metrics),
                          metrics_rows=count, last_time_h=last, outcomes=scalar_outcomes(load_csv(metrics)))
            save_json(manifest_path, manifest)
            print(f"[{sum(r['status']=='complete' for r in manifest['runs'])}/{manifest['requested_runs']}] "
                  f"{record['label']} seed={record['seed']} {record['elapsed_seconds']:.1f}s", flush=True)
        results = []
        for arm, cfg in enumerate(experiment["configs"]):
            records = [r for r in manifest["runs"] if r["arm"] == arm]
            if len(records) != n_runs or any(r["status"] != "complete" for r in records):
                raise RuntimeError("cohort is incomplete; no summary produced")
            mean, sd = aggregate_csvs([r["metrics"] for r in records])
            write_csv(mean, str(output / f"consensus_arm{arm:02d}.csv"))
            write_csv(sd, str(output / f"std_arm{arm:02d}.csv"))
            results.append({"label": cfg["label"], "n_runs": n_runs, "replicates": records,
                            "mean_data": mean, "std_data": sd, "outcomes": summarize_replicates(records)})
        write_replicate_tables(results, output)
        write_comparison(results, output)
        write_summary(experiment, results, output, time.time() - t0)
        write_figures(results, output)
        print_results_table(results)
        manifest["status"] = "complete"
        manifest["elapsed_seconds"] = time.time() - t0
        save_json(manifest_path, manifest)
        return results
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        save_json(manifest_path, manifest)
        raise
