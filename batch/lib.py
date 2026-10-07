"""Shared utilities for the batch/sweep system.

Provides config merging, parameter override, simulation running,
CSV aggregation, and outcome extraction.
"""

import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

# Project root (one level up from batch/)
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))


def user_studies_dir():
    return os.environ.get("SKIBIDY_USER_STUDIES",
                          os.path.join(os.path.expanduser("~"), ".skibidy", "studies"))


def resolve_study(name):
    """Resolve the same user-first study identity displayed by the dashboard."""
    if not name or name in (".", "..") or os.path.basename(name) != name or "\\" in name:
        raise ValueError("Invalid study name")
    for base in (user_studies_dir(), os.path.join(ROOT, "studies")):
        path = os.path.join(base, name)
        if os.path.isfile(os.path.join(path, "preset.toml")):
            return path
    raise ValueError(f"Study '{name}' not found")


def study_profile(name):
    path = os.path.join(resolve_study(name), name + ".skibidy")
    return parse_toml(path).get("project", {}).get("profile", "") if os.path.isfile(path) else ""


def file_sha256(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def plots_dir(csv_path):
    """Derive plots output directory from a metrics CSV path.

    Returns <csv_parent>/plots/, e.g. studies/wound/results/plots/.
    """
    return os.path.join(os.path.dirname(os.path.abspath(csv_path)), "plots")


# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------

def merge_config():
    """Run merge_config.py to produce bdm.toml from bdm.core.toml + modules."""
    rc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "config", "merge_config.py")],
        cwd=ROOT, capture_output=True, text=True)
    if rc.returncode != 0:
        print(f"Config merge failed: {rc.stderr}")
        sys.exit(1)
    return rc.stdout.strip()


def apply_overlay(overlay_path):
    """Apply a TOML overlay (profile or study config) to bdm.toml."""
    rc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "config", "apply_preset.py"),
         overlay_path, "bdm.toml"],
        cwd=ROOT, capture_output=True, text=True)
    if rc.returncode != 0:
        print(f"Overlay failed ({overlay_path}): {rc.stderr}")
        sys.exit(1)


def apply_profile(name):
    """Apply a skin profile by name."""
    path = os.path.join(ROOT, "profiles", f"{name}.toml")
    if not os.path.isfile(path):
        print(f"ERROR: skin profile '{name}' not found.")
        sys.exit(1)
    apply_overlay(path)


def apply_site(name):
    """Apply a body site overlay by name (looks up modules/body_site/sites/{name}.toml)."""
    path = os.path.join(ROOT, "modules", "body_site", "sites", f"{name}.toml")
    if not os.path.isfile(path):
        print(f"ERROR: body site '{name}' not found.")
        sys.exit(1)
    apply_overlay(path)


def apply_study(name):
    """Apply a study config by name (looks up studies/{name}/preset.toml)."""
    apply_overlay(os.path.join(resolve_study(name), "preset.toml"))


def apply_treatment(name, study=None):
    """Apply a treatment overlay by name.

    Searches studies/{study}/treatments/ first if study is given,
    then studies/shared/treatments/. Other studies are never a fallback.
    """
    if not name or os.path.basename(name) != name or "\\" in name or name in (".", ".."):
        raise ValueError("Invalid treatment name")
    if study:
        path = os.path.join(resolve_study(study), "treatments", f"{name}.toml")
        if os.path.isfile(path):
            apply_overlay(path)
            return
    # Search shared treatments
    shared = os.path.join(ROOT, "studies", "shared", "treatments", f"{name}.toml")
    if os.path.isfile(shared):
        apply_overlay(shared)
        return
    raise ValueError(f"Treatment {name!r} not found in requested study {study!r} or shared treatments")


def override_param(param_path, value):
    """Override a single dotted TOML parameter in bdm.toml.

    param_path: e.g. "skin.immune.cytokine_rate"
    value: the value to set (number, bool, or string)
    """
    bdm_toml = os.path.join(ROOT, "bdm.toml")
    with open(bdm_toml) as f:
        lines = f.readlines()

    # Parse dotted path: "skin.immune.cytokine_rate" -> section "[skin.immune]", key "cytokine_rate"
    parts = param_path.split(".")
    key = parts[-1]
    section = ".".join(parts[:-1])
    section_header = f"[{section}]"

    # Find the section, then the key within it
    in_section = False
    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = (stripped == section_header)
            if found:
                break  # past our section
        elif in_section:
            # Match key = value (ignoring comments)
            m = re.match(rf"^(\s*){re.escape(key)}\s*=\s*", line)
            if m:
                indent = m.group(1)
                if isinstance(value, bool):
                    val_str = "true" if value else "false"
                elif isinstance(value, (int, float)):
                    val_str = str(value)
                else:
                    val_str = json.dumps(value, ensure_ascii=False)
                lines[i] = f"{indent}{key} = {val_str}\n"
                found = True

    if not found:
        # Append section and key if missing
        if isinstance(value, bool):
            val_str = "true" if value else "false"
        elif isinstance(value, (int, float)):
            val_str = str(value)
        else:
            val_str = json.dumps(value, ensure_ascii=False)
        # Check if section exists but key is missing
        section_exists = any(line.strip() == section_header for line in lines)
        if section_exists:
            # Find the section and append the key after it
            for i, line in enumerate(lines):
                if line.strip() == section_header:
                    lines.insert(i + 1, f"{key} = {val_str}\n")
                    break
        else:
            lines.append(f"\n{section_header}\n{key} = {val_str}\n")

    with open(bdm_toml, "w") as f:
        f.writelines(lines)

    return True


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_if_needed():
    """Build the binary if sources are newer."""
    binary = os.path.join(ROOT, "build", "skibidy")
    if os.path.isfile(binary):
        bin_mtime = os.path.getmtime(binary)
        needs_build = False
        for source_dir in ("src", "modules", "studies"):
            for root, _, files in os.walk(os.path.join(ROOT, source_dir)):
                if any(f.endswith((".h", ".cc", ".cpp", ".cmake")) and
                       os.path.getmtime(os.path.join(root, f)) > bin_mtime
                       for f in files):
                    needs_build = True
                    break
        if os.path.getmtime(os.path.join(ROOT, "CMakeLists.txt")) > bin_mtime:
            needs_build = True
        if not needs_build:
            return
    print("Building...")
    build_dir = os.path.join(ROOT, "build")
    subprocess.run(["cmake", "-S", ROOT, "-B", build_dir,
                    "-DCMAKE_BUILD_TYPE=Release"], check=True)
    subprocess.run(["cmake", "--build", build_dir, "--parallel", "2"], check=True)


# ---------------------------------------------------------------------------
# Simulation execution
# ---------------------------------------------------------------------------

def simulation_environment(environment=None):
    """Ordinary runs must not inherit checkpoint or state-witness controls."""
    return {key: value for key, value in (os.environ if environment is None else environment).items()
            if not key.startswith(("SKIBIDY_CKPT_", "SKIBIDY_CHECKPOINT_"))
            and key != "SKIBIDY_STATE_SIGNATURE_FILE"}


def run_simulation(output_path=None):
    """Run one simulation. Returns (success, elapsed_seconds).

    If output_path is given, BDM writes directly there (no copy needed).
    Otherwise falls back to the default output/ directory.

    Success requires a zero exit status and complete, finite metrics.
    The effective configuration and process logs accompany each run.
    """
    if output_path:
        # Write directly to the target directory.
        # BDM appends the project name ("skibidy") as a subdirectory.
        os.makedirs(output_path, exist_ok=True)
        output_path = os.path.abspath(output_path)
        override_param("simulation.output_dir", output_path)
        _last_output[0] = os.path.join(output_path, "skibidy")
    else:
        out = os.path.join(ROOT, "output")
        override_param("simulation.output_dir", out)
        _last_output[0] = os.path.join(out, "skibidy")

    # Remove only stale metrics owned by this run; preserve adjacent evidence.
    metrics_path = get_metrics_path()
    if os.path.isfile(metrics_path):
        os.remove(metrics_path)

    # Disable viz export and suppress xdg-open/GUI for batch/AI runs.
    # skin.headless is the exposed flag checked by the binary.
    override_param("visualization.export", False)
    override_param("skin.headless", True)
    override_param("skin.hot_reload", False)
    config = parse_toml(os.path.join(ROOT, "bdm.toml"))
    evidence_dir = os.path.dirname(_last_output[0])
    os.makedirs(evidence_dir, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "bdm.toml"),
                    os.path.join(evidence_dir, "run-config.toml"))

    t0 = time.time()
    env = simulation_environment()
    result = subprocess.run(
        [os.path.join(ROOT, "build", "skibidy")],
        cwd=ROOT, capture_output=True, text=True, env=env)
    elapsed = time.time() - t0
    for stream in ("stdout", "stderr"):
        with open(os.path.join(evidence_dir, stream + ".log"), "w") as f:
            f.write(getattr(result, stream) or "")
    ok = result.returncode == 0
    error = "" if ok else f"simulation exited with status {result.returncode}"
    try:
        validate_run_metrics(metrics_path, config)
    except (OSError, ValueError, KeyError) as exc:
        ok = False
        error = str(exc) if not error else error + "; " + str(exc)
        print(f"[invalid run: {exc}]", end=" ")
    if not ok and result.returncode != 0:
        # Log last 5 lines of stderr for debugging
        err_lines = (result.stderr or "").strip().splitlines()[-5:]
        if err_lines:
            print(f"[sim stderr: {'; '.join(err_lines)}]", end=" ")
    _last_result.clear()
    _last_result.update(success=ok, error=error, returncode=result.returncode,
                        seed=config.get("simulation", {}).get("random_seed", 0),
                        config_sha256=file_sha256(os.path.join(evidence_dir, "run-config.toml")),
                        metrics_sha256=file_sha256(metrics_path))
    return ok, elapsed


def validate_run_metrics(path, config):
    """Reject crashed, truncated or nonfinite simulation output."""
    import math
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "time_h" not in reader.fieldnames:
            raise ValueError("metrics header missing time_h")
        previous = -1.0
        count = 0
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("incomplete metrics row")
            values = {k: float(v) for k, v in row.items()}
            if not all(math.isfinite(v) for v in values.values()):
                raise ValueError("nonfinite metrics")
            current = values["time_h"]
            if current <= previous:
                raise ValueError("metrics time is not increasing")
            previous = current
            count += 1
    expected = float(config["skin"]["duration_days"]) * 24
    interval = float(config["skin"].get("metrics_interval_h", 10))
    if not count or previous < expected - interval - 1e-6 or previous > expected + interval:
        raise ValueError(f"incomplete duration: last={previous}, expected={expected} hours")
    return count, previous


# Tracks where the last run wrote its output
_last_output = [os.path.join(ROOT, "output", "skibidy")]
_last_result = {}


def get_metrics_path():
    """Return path to the metrics CSV from the last run."""
    return os.path.join(_last_output[0], "metrics.csv")


# ---------------------------------------------------------------------------
def setup_run(skin=None, site=None, study=None, treatment=None):
    """Merge config + apply profile/site/study/treatment overlays."""
    merge_config()
    effective_profile = skin or (study_profile(study) if study else "")
    if effective_profile:
        apply_profile(effective_profile)
    if site:
        apply_site(site)
    if study:
        apply_study(study)
    if treatment:
        apply_treatment(treatment, study)
    if effective_profile:
        config = parse_toml(os.path.join(ROOT, "bdm.toml"))
        override_param("analysis.profile", effective_profile)
        if not config.get("analysis", {}).get("condition"):
            from literature.lib import condition_from_config
            active = condition_from_config(dict(config, analysis={}))
            condition = active if active != "normal" else {
                "aged": "aging", "aged_diabetic": "diabetic",
            }.get(effective_profile, effective_profile)
            override_param("analysis.condition", condition)


def parse_toml(path):
    """Parse a TOML file. Uses tomllib (3.11+) or tomli fallback."""
    tl = get_tomllib()
    with open(path, "rb") as f:
        return tl.load(f)


def get_tomllib():
    """Import tomllib (3.11+), falling back to tomli or pip's vendored copy."""
    try:
        import tomllib
        return tomllib
    except ImportError:
        pass
    try:
        import tomli as tomllib
        return tomllib
    except ImportError:
        pass
    import pip._vendor.tomli as tomllib
    return tomllib


# CSV loading and aggregation
# ---------------------------------------------------------------------------

def load_csv(path):
    """Load complete CSV records; reject corruption instead of repairing evidence."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = [row for row in f if not row.startswith("#")]
    if any("\x00" in row for row in lines):
        raise ValueError(f"NUL byte in CSV: {path}")
    reader = csv.DictReader(lines)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError(f"missing or duplicate CSV header: {path}")
    rows = list(reader)
    if any(None in r or any(v is None or v == "" for v in r.values()) for r in rows):
        raise ValueError(f"incomplete CSV record: {path}")
    if not rows:
        return {}
    data = {}
    for key in rows[0]:
        try:
            data[key] = [float(r[key]) for r in rows]
            if any(not math.isfinite(v) for v in data[key]):
                raise ArithmeticError(f"nonfinite CSV value in {key}: {path}")
        except (ValueError, TypeError):
            data[key] = [r[key] for r in rows]
    return data


def aggregate_csvs(csv_paths, min_length_fraction=None):
    """Compute mean and std across multiple CSV files.

    Every requested run must be nonempty and have the same schema and time
    coordinates. Incomplete cohorts are errors, never silently dropped.
    min_length_fraction is retained for call compatibility and has no effect.

    Returns (mean_data, std_data) where each is a dict of lists.
    """
    if not csv_paths:
        return {}, {}
    all_data = [load_csv(p) for p in csv_paths]
    if any(not d for d in all_data):
        raise ValueError("cannot aggregate an empty replicate")

    columns = [k for k in all_data[0] if isinstance(all_data[0][k][0], float)]
    if not columns:
        return {}, {}

    lengths = [len(d[columns[0]]) for d in all_data]
    if len(set(lengths)) != 1 or any(set(d) != set(all_data[0]) for d in all_data):
        raise ValueError("replicates have different lengths or schemas")
    if "time_h" in all_data[0] and any(d["time_h"] != all_data[0]["time_h"] for d in all_data):
        raise ValueError("replicate time coordinates do not match")
    filtered = all_data
    n_rows = lengths[0]

    mean_data = {}
    std_data = {}
    for col in columns:
        means = []
        stds = []
        for i in range(n_rows):
            vals = [d[col][i] for d in filtered if i < len(d[col])]
            if not vals:
                break
            m = sum(vals) / len(vals)
            v = sum((x - m) ** 2 for x in vals) / len(vals)
            means.append(m)
            stds.append(math.sqrt(v))
        mean_data[col] = means
        std_data[col] = stds

    return mean_data, std_data


def write_csv(data, path, columns=None):
    """Write a dict-of-lists to CSV."""
    if columns is None:
        columns = list(data.keys())
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        n_rows = len(data[columns[0]])
        for i in range(n_rows):
            writer.writerow([f"{data[col][i]:.6g}" for col in columns])


# ---------------------------------------------------------------------------
# Outcome extraction
# ---------------------------------------------------------------------------

_OUTCOME_ALIASES = {
    "collagen_density": "mean_collagen_wound",
    "inflammation_level": "mean_infl_wound",
    "fibroblast_count": "n_fibroblasts",
    "vascular_density": "mean_perfusion_wound",
    "tnf_alpha_level": "mean_tnf_alpha_wound",
    "il6_level": "mean_il6_wound",
    "bone_density": "mean_bone_wound",
    "cartilage_density": "mean_cartilage_wound",
    "vegf_level": "mean_vegf_wound",
    "mmp_level": "mean_mmp_wound",
    "neutrophil_count": "n_neutrophils",
    "macrophage_count": "n_macrophages",
}


def extract_outcome(data, column, measure="final"):
    """Extract a scalar outcome from a metrics timeseries.

    Measures:
      final     - last value
      peak      - maximum value
      auc       - area under curve (trapezoidal, using time_h)
      time_to_N - first time value exceeds N (e.g. time_to_90)
    """
    values = data.get(column, [])
    if not values:
        # Try alias mapping
        alias = _OUTCOME_ALIASES.get(column)
        if alias:
            values = data.get(alias, [])
    if not values:
        return float("nan")

    if measure == "final":
        return values[-1]
    elif measure == "peak":
        return max(values)
    elif measure == "auc":
        times = data.get("time_h", list(range(len(values))))
        total = 0
        for i in range(1, len(values)):
            dt = times[i] - times[i - 1]
            total += 0.5 * (values[i] + values[i - 1]) * dt
        return total
    elif measure.startswith("time_to_"):
        threshold = float(measure.split("_")[-1])
        times = data.get("time_h", list(range(len(values))))
        for t, v in zip(times, values):
            if v >= threshold:
                return t
        return float("nan")  # never reached
    else:
        raise ValueError(f"Unknown measure: {measure}")


# ---------------------------------------------------------------------------
# Validation integration
# ---------------------------------------------------------------------------

def run_validation(metrics_path):
    """Run validate_all.py on a metrics CSV. Returns returncode."""
    rc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "literature", "validate_all.py"),
         metrics_path],
        cwd=ROOT)
    return rc.returncode
