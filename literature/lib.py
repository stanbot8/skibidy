"""Shared utilities for validation scripts.

Provides CSV loading, interpolation, normalization, error metrics,
module-level validate/plot/print functions used by validate_all.py
and the individual compare_*.py wrappers.
"""

import csv
import math
import os
from batch.lib import load_csv


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def plots_dir(csv_path):
    """Derive plots output directory from a metrics CSV path.

    Returns <csv_parent>/plots/, e.g. studies/wound/results/plots/.
    """
    return os.path.join(os.path.dirname(os.path.abspath(csv_path)), "plots")


# load_csv imported from batch.lib (canonical version)
def interpolate(x_ref, y_ref, x_query, extrapolate=True):
    """Linear interpolation of (x_ref, y_ref) at x_query points."""
    result = []
    for xq in x_query:
        if not extrapolate and (xq < x_ref[0] or xq > x_ref[-1]):
            result.append(float("nan"))
        elif xq <= x_ref[0]:
            result.append(y_ref[0])
        elif xq >= x_ref[-1]:
            result.append(y_ref[-1])
        else:
            for i in range(len(x_ref) - 1):
                if x_ref[i] <= xq <= x_ref[i + 1]:
                    t = (xq - x_ref[i]) / (x_ref[i + 1] - x_ref[i])
                    result.append(y_ref[i] + t * (y_ref[i + 1] - y_ref[i]))
                    break
    return result


def _window_normalize(values, days, reference_days, mode="peak"):
    """Define normalization only within the observed reference window."""
    inside = [v for d, v in zip(days, values)
              if reference_days[0] <= d <= reference_days[-1]]
    if not inside:
        return values, 0
    denominator = max(inside) if mode == "peak" else inside[-1]
    return ([v / denominator for v in values], denominator) if denominator > 0 else (values, 0)


def peak_normalize(values):
    """Normalize a list by its maximum value. Returns (normalized, peak)."""
    peak = max(values)
    if peak > 0:
        return [v / peak for v in values], peak
    return values, 0


def end_normalize(values):
    """Normalize a list by its final value. Returns (normalized, final)."""
    final = values[-1] if values else 0
    if final > 0:
        return [v / final for v in values], final
    return values, 0


def compute_rmse(sim, ref):
    """Compute root-mean-square error between two lists."""
    if len(sim) != len(ref):
        raise ValueError("Comparison lengths differ")
    errors = [s - r for s, r in zip(sim, ref) if math.isfinite(r)]
    if not errors:
        return float("nan")
    return math.sqrt(sum(e ** 2 for e in errors) / len(errors))




def phase_rmse(sim_days, sim_vals, ref_at_sim, day_start, day_end):
    """Compute RMSE over a day range."""
    indices = [i for i, d in enumerate(sim_days)
               if day_start <= d <= day_end and math.isfinite(ref_at_sim[i])]
    if not indices:
        return float("nan")
    errors = [sim_vals[i] - ref_at_sim[i] for i in indices]
    return math.sqrt(sum(e ** 2 for e in errors) / len(errors))


def surface_fraction(n_cells, cell_diameter=4.0, packing=0.5):
    """Estimate surface-shell fraction for a sphere of n_cells."""
    if n_cells <= 1:
        return 1.0
    R = (cell_diameter / 2.0) * (n_cells / packing) ** (1.0 / 3.0)
    ratio = max(0, 1 - cell_diameter / R)
    return 1.0 - ratio ** 3


# ---------------------------------------------------------------------------
# Reference data resolution (consensus CSVs live inside each module)
# ---------------------------------------------------------------------------

_MODULES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "modules")
_STUDIES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "studies")

_FILE_MODULE_MAP = {
    "closure_kinetics_punch_biopsy.csv": "wound",
    "inflammation_timecourse.csv": "inflammation",
    "immune_cell_kinetics.csv": "immune",
    "myofibroblast_kinetics.csv": "fibroblast",
    "collagen_deposition.csv": "fibroblast",
    "tgfb_kinetics.csv": "fibroblast",
    "fibroblast_kinetics.csv": "fibroblast",
    "fibronectin_kinetics.csv": "fibronectin",
    "mmp_kinetics.csv": "mmp",
    "vegf_kinetics.csv": "angiogenesis",
    "diabetic_closure_kinetics.csv": "diabetic",
    "diabetic_inflammation_timecourse.csv": "diabetic",
    "diabetic_immune_cell_kinetics.csv": "diabetic",
    "diabetic_mmp_kinetics.csv": "diabetic",
    "diabetic_tgfb_kinetics.csv": "diabetic",
    "tumor_doubling_time.csv": "tumor",
    "tumor_growth_rate.csv": "tumor",
    "tumor_proliferation_index.csv": "tumor",
    "ph_kinetics.csv": "ph",
    "burn_closure_kinetics.csv": "burn",
    "burn_inflammation_timecourse.csv": "burn",
    "burn_immune_cell_kinetics.csv": "burn",
    "pressure_closure_kinetics.csv": "pressure",
    "pressure_inflammation_timecourse.csv": "pressure",
    "pressure_immune_cell_kinetics.csv": "pressure",
    "surgical_closure_kinetics.csv": "wound",
    "surgical_inflammation_timecourse.csv": "wound",
    "surgical_immune_cell_kinetics.csv": "wound",
    "venous_closure_kinetics.csv": "wound",
    "p16_p21_age_cross_section.csv": "senescence",
    "scar_posas_observer_normal.csv": "scar",
    "scleroderma_mrss_trajectory.csv": "scar",
}


def _ref_path(filename):
    """Resolve a consensus CSV filename to its module data path."""
    module = _FILE_MODULE_MAP[filename]
    return os.path.join(_MODULES_DIR, module, "data", filename)


def _study_ref_path(study, module, filename):
    """Resolve a consensus CSV filename for a study-scoped module."""
    return os.path.join(_STUDIES_DIR, study, "modules", module, "data", filename)


# ---------------------------------------------------------------------------
# Condition detection (normal vs diabetic)
# ---------------------------------------------------------------------------

def condition_from_config(config):
    """Use saved condition metadata and active modes, never directory names."""
    skin = config.get("skin", {})
    active = [name for name, section in
              [("diabetic", "diabetic"), ("burn", "burn"),
               ("pressure", "pressure"), ("rheumatoid", "ra")]
              if skin.get(section, {}).get("mode", False)
              or (section == "ra" and skin.get(section, {}).get("enabled", False))]
    if len(active) > 1:
        raise ValueError(f"ambiguous active conditions: {active}")
    metadata = config.get("analysis", {})
    declared = metadata.get("condition") or metadata.get("profile")
    if active:
        if declared and declared not in (active[0], "normal", "default"):
            raise ValueError(f"saved condition {declared} conflicts with {active[0]}")
        return active[0]
    return declared or "normal"


def detect_condition(config_path=None):
    """Read the run's TOML; missing evidence is an error."""
    from batch.lib import parse_toml
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), os.pardir, "bdm.toml")
    return condition_from_config(parse_toml(config_path))


SIM_COLOR = "#D46664"
REF_COLOR = "#4A90D9"
REF_KW = dict(color=REF_COLOR, linewidth=1.5, linestyle="--",
              marker="o", markersize=4, label="Literature")
SIM_KW = dict(color=SIM_COLOR, linewidth=2, label="Simulation")

def detect_modules(sim, config=None):
    """Return (has_wound, has_fibroblast, has_tumor, has_microenv, has_ph, has_ra) booleans."""
    if config is not None:
        skin = config.get("skin", {})
        enabled = lambda name: skin.get(name, {}).get("enabled", False)
        wound = enabled("wound")
        return (wound, wound and enabled("fibroblast"), enabled("tumor"),
                wound and any(enabled(name) for name in ("fibroblast", "mmp", "angiogenesis", "fibronectin")),
                wound and "ph" in skin, enabled("ra"))
    has_wound = ("wound_closure_pct" in sim
                 and max(sim["wound_closure_pct"]) > 0)
    has_fibroblast = (has_wound and "n_myofibroblasts" in sim
                      and max(sim["n_myofibroblasts"]) > 0)
    has_tumor = ("n_tumor_cells" in sim
                 and (max(sim["n_tumor_cells"]) > 0
                      or ("tumor_field_cells" in sim
                          and max(sim["tumor_field_cells"]) > 0)))
    has_microenv = (has_wound
                    and "mean_tgfb_wound" in sim
                    and max(sim["mean_tgfb_wound"]) > 0)
    has_ph = (has_wound
              and "mean_ph_wound" in sim
              and max(sim["mean_ph_wound"]) > 0)
    has_ra = ("mean_tnf_alpha_wound" in sim
              and max(sim["mean_tnf_alpha_wound"]) > 0)
    return has_wound, has_fibroblast, has_tumor, has_microenv, has_ph, has_ra


# ---------------------------------------------------------------------------
# Validate functions (pure computation, no I/O)
# ---------------------------------------------------------------------------

def validate_wound(sim, sim_days, condition="normal"):
    """Compute wound validation metrics. Returns result dict.

    Supports conditions: normal, diabetic, burn, pressure, surgical.
    Each loads condition-specific reference curves from the corresponding
    module data directory.
    """
    if condition not in ("normal", "diabetic", "burn", "pressure", "surgical"):
        return None
    if condition == "diabetic":
        ref_closure = load_csv(_ref_path("diabetic_closure_kinetics.csv"))
        ref_infl = load_csv(_ref_path("diabetic_inflammation_timecourse.csv"))
        ref_immune = load_csv(_ref_path("diabetic_immune_cell_kinetics.csv"))
    elif condition == "burn":
        ref_closure = load_csv(_ref_path("burn_closure_kinetics.csv"))
        ref_infl = load_csv(_ref_path("burn_inflammation_timecourse.csv"))
        ref_immune = load_csv(_ref_path("burn_immune_cell_kinetics.csv"))
    elif condition == "pressure":
        ref_closure = load_csv(_ref_path("pressure_closure_kinetics.csv"))
        ref_infl = load_csv(_ref_path("pressure_inflammation_timecourse.csv"))
        ref_immune = load_csv(_ref_path("pressure_immune_cell_kinetics.csv"))
    elif condition == "surgical":
        ref_closure = load_csv(_ref_path("surgical_closure_kinetics.csv"))
        ref_infl = load_csv(_ref_path("surgical_inflammation_timecourse.csv"))
        ref_immune = load_csv(_ref_path("surgical_immune_cell_kinetics.csv"))
    else:
        ref_closure = load_csv(_ref_path("closure_kinetics_punch_biopsy.csv"))
        ref_infl = load_csv(_ref_path("inflammation_timecourse.csv"))
        ref_immune = load_csv(_ref_path("immune_cell_kinetics.csv"))

    sim_closure = sim["wound_closure_pct"]
    ref_closure_at_sim = interpolate(
        ref_closure["day"], ref_closure["closure_pct"], sim_days, extrapolate=False)
    closure_rmse = compute_rmse(sim_closure, ref_closure_at_sim)
    closure_ci = None  # Interpolated times are not independent biological replicates.
    closure_max = max((abs(s - r) for s, r in zip(sim_closure, ref_closure_at_sim) if math.isfinite(r)), default=float("nan"))

    infl_rmse = phase_rmse(sim_days, sim_closure, ref_closure_at_sim, 0, 3)
    prolif_rmse = phase_rmse(sim_days, sim_closure, ref_closure_at_sim, 3, 14)
    remod_rmse = phase_rmse(sim_days, sim_closure, ref_closure_at_sim, 14, 28)

    sim_infl, infl_peak = _window_normalize(sim["mean_infl_wound"], sim_days, ref_infl["day"], "peak") if ref_infl is not None else (sim["mean_infl_wound"], 0)
    ref_infl_at_sim = interpolate(
        ref_infl["day"], ref_infl["inflammation_normalized"], sim_days, extrapolate=False)
    inflammation_rmse = compute_rmse(sim_infl, ref_infl_at_sim)

    sim_neut, neut_peak = _window_normalize(sim["n_neutrophils"], sim_days, ref_immune["day"], "peak") if ref_immune is not None else (sim["n_neutrophils"], 0)
    ref_neut_at_sim = interpolate(
        ref_immune["day"], ref_immune["neutrophils_normalized"], sim_days, extrapolate=False)
    neut_rmse = compute_rmse(sim_neut, ref_neut_at_sim)

    sim_mac, mac_peak = _window_normalize(sim["n_macrophages"], sim_days, ref_immune["day"], "peak") if ref_immune is not None else (sim["n_macrophages"], 0)
    ref_mac_at_sim = interpolate(
        ref_immune["day"], ref_immune["macrophages_normalized"], sim_days, extrapolate=False)
    mac_rmse = compute_rmse(sim_mac, ref_mac_at_sim)

    return dict(
        # Series for plotting
        condition=condition,
        sim_closure=sim_closure, ref_closure=ref_closure,
        ref_closure_at_sim=ref_closure_at_sim,
        sim_infl=sim_infl, ref_infl=ref_infl,
        ref_infl_at_sim=ref_infl_at_sim, infl_peak=infl_peak,
        sim_neut=sim_neut, ref_immune=ref_immune,
        ref_neut_at_sim=ref_neut_at_sim, neut_peak=neut_peak,
        sim_mac=sim_mac, ref_mac_at_sim=ref_mac_at_sim, mac_peak=mac_peak,
        # Metrics
        closure_rmse=closure_rmse, closure_max=closure_max,
        closure_ci=closure_ci,
        infl_rmse=infl_rmse, prolif_rmse=prolif_rmse, remod_rmse=remod_rmse,
        inflammation_rmse=inflammation_rmse,
        neut_rmse=neut_rmse, mac_rmse=mac_rmse,
    )


def validate_fibroblast(sim, sim_days, condition="normal"):
    """Compute fibroblast/collagen validation metrics. Returns result dict.

    Reference data is only available for normal wounds. Returns None for
    non-normal conditions so callers don't report bogus RMSE.
    """
    if condition != "normal":
        return None
    ref_myofib = load_csv(_ref_path("myofibroblast_kinetics.csv"))
    ref_collagen = load_csv(_ref_path("collagen_deposition.csv"))
    ref_fibro = load_csv(_ref_path("fibroblast_kinetics.csv"))

    sim_myofib, myofib_peak = _window_normalize(sim["n_myofibroblasts"], sim_days, ref_myofib["day"], "peak") if ref_myofib is not None else (sim["n_myofibroblasts"], 0)
    ref_myofib_at_sim = interpolate(
        ref_myofib["day"], ref_myofib["myofibroblasts_normalized"], sim_days, extrapolate=False)
    myofib_rmse = compute_rmse(sim_myofib, ref_myofib_at_sim)

    sim_collagen, collagen_final = _window_normalize(sim["mean_collagen_wound"], sim_days, ref_collagen["day"], "end") if ref_collagen is not None else (sim["mean_collagen_wound"], 0)
    ref_collagen_at_sim = interpolate(
        ref_collagen["day"], ref_collagen["collagen_normalized"], sim_days, extrapolate=False)
    collagen_rmse = compute_rmse(sim_collagen, ref_collagen_at_sim)

    sim_fibro, fibro_peak = _window_normalize(sim["n_fibroblasts"], sim_days, ref_fibro["day"], "peak") if ref_fibro is not None else (sim["n_fibroblasts"], 0)
    ref_fibro_at_sim = interpolate(
        ref_fibro["day"], ref_fibro["fibroblasts_normalized"], sim_days, extrapolate=False)
    fibro_rmse = compute_rmse(sim_fibro, ref_fibro_at_sim)

    return dict(
        sim_myofib=sim_myofib, ref_myofib=ref_myofib,
        ref_myofib_at_sim=ref_myofib_at_sim, myofib_peak=myofib_peak,
        sim_collagen=sim_collagen, ref_collagen=ref_collagen,
        ref_collagen_at_sim=ref_collagen_at_sim, collagen_final=collagen_final,
        sim_fibro=sim_fibro, ref_fibro=ref_fibro,
        ref_fibro_at_sim=ref_fibro_at_sim, fibro_peak=fibro_peak,
        myofib_rmse=myofib_rmse, collagen_rmse=collagen_rmse,
        fibro_rmse=fibro_rmse,
    )


def validate_tumor(sim, sim_days):
    """Compute tumor validation metrics. Returns result dict."""
    ref_td = load_csv(_ref_path("tumor_doubling_time.csv"))
    ref_ki67 = load_csv(_ref_path("tumor_proliferation_index.csv"))

    bcc_doubling_days = 148.0
    for i, t in enumerate(ref_td["tumor_type"]):
        if t == "bcc_mean":
            bcc_doubling_days = ref_td["doubling_time_days"][i]
            break

    bcc_ki67_pct = 27.4
    for i, t in enumerate(ref_ki67["tumor_type"]):
        if t == "bcc_all":
            bcc_ki67_pct = ref_ki67["ki67_pct"][i]
            break

    sim_agents = sim["n_tumor_cells"]
    if "tumor_field_cells" in sim:
        sim_tumor = [a + f for a, f in zip(sim_agents, sim["tumor_field_cells"])]
    else:
        sim_tumor = sim_agents

    nonzero = [(d, n) for d, n in zip(sim_days, sim_tumor) if n > 0]
    observed_doubling = float("inf")
    if len(nonzero) >= 2:
        d0, n0 = nonzero[0]
        d1, n1 = nonzero[-1]
        if n1 > n0 and n0 > 0:
            observed_doubling = (d1 - d0) * math.log(2) / math.log(n1 / n0)

    ref_tumor_exp = []
    if nonzero:
        n_init = nonzero[0][1]
        d_start = nonzero[0][0]
        for d in sim_days:
            if d >= d_start and n_init > 0:
                ref_tumor_exp.append(
                    n_init * 2 ** ((d - d_start) / bcc_doubling_days))
            else:
                ref_tumor_exp.append(0)

    has_cycling = "n_tumor_cycling" in sim
    sim_ki67 = []
    mean_ki67 = float("nan")
    if has_cycling:
        sim_ki67 = [100.0 * c / n if n > 0 else 0
                    for c, n in zip(sim["n_tumor_cycling"], sim_tumor)]
        half = len(sim_ki67) // 2
        tail = sim_ki67[half:]
        mean_ki67 = sum(tail) / max(1, len(tail))

    sim_span = sim_days[-1] - (nonzero[0][0] if nonzero else 0)
    n_init = nonzero[0][1] if nonzero else 0
    ref_final = n_init * 2 ** (sim_span / bcc_doubling_days) if n_init > 0 else 0
    obs_final = sim_tumor[-1]
    obs_x = obs_final / n_init if n_init > 0 else 0
    ref_x = ref_final / n_init if n_init > 0 else 0
    sf = surface_fraction(obs_final)

    return dict(
        sim_tumor=sim_tumor, ref_tumor_exp=ref_tumor_exp,
        nonzero=nonzero, observed_doubling=observed_doubling,
        bcc_doubling_days=bcc_doubling_days, bcc_ki67_pct=bcc_ki67_pct,
        has_cycling=has_cycling, sim_ki67=sim_ki67, mean_ki67=mean_ki67,
        sim_span=sim_span, n_init=n_init,
        ref_final=ref_final, obs_final=obs_final,
        obs_x=obs_x, ref_x=ref_x, sf=sf,
    )


def validate_microenvironment(sim, sim_days, condition="normal"):
    """Compute microenvironment validation metrics (TGF-b, VEGF, fibronectin, MMP).

    When condition="diabetic", uses diabetic-specific reference curves for
    MMP (sustained elevation; Lobmann et al. 2002) and TGF-b (delayed peak;
    Mirza & Koh 2011).
    """
    if condition not in ("normal", "diabetic"):
        return None
    # Diabetic-specific references only exist for TGF-b and MMP; VEGF and
    # fibronectin have no diabetic reference data so we skip them for
    # non-normal conditions to avoid bogus RMSE against mismatched curves.
    if condition == "diabetic":
        ref_tgfb = load_csv(_ref_path("diabetic_tgfb_kinetics.csv"))
        ref_mmp = load_csv(_ref_path("diabetic_mmp_kinetics.csv"))
    else:
        ref_tgfb = load_csv(_ref_path("tgfb_kinetics.csv"))
        ref_mmp = load_csv(_ref_path("mmp_kinetics.csv"))
    has_vegf_ref = (condition == "normal")
    has_fn_ref = (condition == "normal")
    ref_vegf = load_csv(_ref_path("vegf_kinetics.csv")) if has_vegf_ref else None
    ref_fn = load_csv(_ref_path("fibronectin_kinetics.csv")) if has_fn_ref else None

    sim_tgfb, tgfb_peak = _window_normalize(sim["mean_tgfb_wound"], sim_days, ref_tgfb["day"], "peak") if ref_tgfb is not None else (sim["mean_tgfb_wound"], 0)
    ref_tgfb_at_sim = interpolate(
        ref_tgfb["day"], ref_tgfb["tgfb_normalized"], sim_days, extrapolate=False)
    tgfb_rmse = compute_rmse(sim_tgfb, ref_tgfb_at_sim)

    sim_vegf, vegf_peak = _window_normalize(sim["mean_vegf_wound"], sim_days, ref_vegf["day"], "peak") if ref_vegf is not None else (sim["mean_vegf_wound"], 0)
    if has_vegf_ref:
        ref_vegf_at_sim = interpolate(
            ref_vegf["day"], ref_vegf["vegf_normalized"], sim_days, extrapolate=False)
        vegf_rmse = compute_rmse(sim_vegf, ref_vegf_at_sim)
    else:
        ref_vegf_at_sim, vegf_rmse = None, None

    sim_fn, fn_peak = _window_normalize(sim["mean_fibronectin_wound"], sim_days, ref_fn["day"], "peak") if ref_fn is not None else (sim["mean_fibronectin_wound"], 0)
    if has_fn_ref:
        ref_fn_at_sim = interpolate(
            ref_fn["day"], ref_fn["fibronectin_normalized"], sim_days, extrapolate=False)
        fn_rmse = compute_rmse(sim_fn, ref_fn_at_sim)
    else:
        ref_fn_at_sim, fn_rmse = None, None

    sim_mmp, mmp_peak = _window_normalize(sim["mean_mmp_wound"], sim_days, ref_mmp["day"], "peak") if ref_mmp is not None else (sim["mean_mmp_wound"], 0)
    ref_mmp_at_sim = interpolate(
        ref_mmp["day"], ref_mmp["mmp_normalized"], sim_days, extrapolate=False)
    mmp_rmse = compute_rmse(sim_mmp, ref_mmp_at_sim)

    return dict(
        sim_tgfb=sim_tgfb, ref_tgfb=ref_tgfb,
        ref_tgfb_at_sim=ref_tgfb_at_sim, tgfb_peak=tgfb_peak,
        sim_vegf=sim_vegf, ref_vegf=ref_vegf,
        ref_vegf_at_sim=ref_vegf_at_sim, vegf_peak=vegf_peak,
        sim_fn=sim_fn, ref_fn=ref_fn,
        ref_fn_at_sim=ref_fn_at_sim, fn_peak=fn_peak,
        sim_mmp=sim_mmp, ref_mmp=ref_mmp,
        ref_mmp_at_sim=ref_mmp_at_sim, mmp_peak=mmp_peak,
        tgfb_rmse=tgfb_rmse, vegf_rmse=vegf_rmse,
        fn_rmse=fn_rmse, mmp_rmse=mmp_rmse,
    )


def validate_ph(sim, sim_days):
    """Compute wound pH (alkalinity) validation metrics. Returns result dict.

    pH is modeled as normalized alkalinity: 1.0 = fresh wound (pH 7.4),
    0.0 = healed acidic skin (pH 5.5). Reference: Schneider et al. 2007.
    """
    ref_ph = load_csv(_ref_path("ph_kinetics.csv"))

    sim_ph = sim["mean_ph_wound"]
    ref_ph_at_sim = interpolate(
        ref_ph["day"], ref_ph["ph_alkalinity_normalized"], sim_days, extrapolate=False)
    ph_rmse = compute_rmse(sim_ph, ref_ph_at_sim)

    return dict(
        sim_ph=sim_ph, ref_ph=ref_ph,
        ref_ph_at_sim=ref_ph_at_sim,
        ph_rmse=ph_rmse,
    )


def validate_ra(sim, sim_days):
    """Compute RA validation metrics. Returns result dict.

    Six observables: TNF-alpha, IL-6 (peak-normalized), cartilage and bone
    (absolute integrity), T cell density and synovial pannus (peak-normalized).
    Reference kinetics derived from Feldmann & Maini 2003, Kishimoto 2005,
    McInnes & Schett 2011, Schett & Gravallese 2012, Firestein 2003.
    """
    ref_tnf = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                        "tnf_alpha_kinetics.csv"))
    ref_il6 = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                        "il6_kinetics.csv"))
    ref_cart = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                         "cartilage_erosion.csv"))
    ref_bone = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                         "bone_erosion.csv"))
    ref_tcell = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                          "tcell_density.csv"))
    ref_syn = load_csv(_study_ref_path("rheumatoid", "rheumatoid",
                                        "synovial_pannus.csv"))

    # TNF-alpha: peak-normalize simulation, compare to reference
    sim_tnf, tnf_peak = _window_normalize(sim["mean_tnf_alpha_wound"], sim_days, ref_tnf["day"], "peak") if ref_tnf is not None else (sim["mean_tnf_alpha_wound"], 0)
    ref_tnf_at_sim = interpolate(
        ref_tnf["day"], ref_tnf["tnf_alpha_normalized"], sim_days, extrapolate=False)
    tnf_rmse = compute_rmse(sim_tnf, ref_tnf_at_sim)

    # IL-6: peak-normalize simulation
    sim_il6, il6_peak = _window_normalize(sim["mean_il6_wound"], sim_days, ref_il6["day"], "peak") if ref_il6 is not None else (sim["mean_il6_wound"], 0)
    ref_il6_at_sim = interpolate(
        ref_il6["day"], ref_il6["il6_normalized"], sim_days, extrapolate=False)
    il6_rmse = compute_rmse(sim_il6, ref_il6_at_sim)

    # Cartilage: normalize to initial value (wound cylinder includes non-cartilage voxels)
    sim_cart_raw = sim["mean_cartilage_wound"]
    cart_init = sim_cart_raw[0] if sim_cart_raw[0] > 1e-6 else 1.0
    sim_cart = [v / cart_init for v in sim_cart_raw]
    ref_cart_at_sim = interpolate(
        ref_cart["day"], ref_cart["cartilage_integrity"], sim_days, extrapolate=False)
    cart_rmse = compute_rmse(sim_cart, ref_cart_at_sim)

    # Phase-specific RMSE for TNF
    tnf_flare_rmse = phase_rmse(sim_days, sim_tnf, ref_tnf_at_sim, 0, 7)
    tnf_chronic_rmse = phase_rmse(sim_days, sim_tnf, ref_tnf_at_sim, 7, 30)

    # Bone: absolute integrity comparison (slower erosion than cartilage)
    has_bone = "mean_bone_wound" in sim
    bone_rmse = 0.0
    sim_bone = []
    ref_bone_at_sim = []
    if has_bone:
        sim_bone_raw = sim["mean_bone_wound"]
        bone_init = sim_bone_raw[0] if sim_bone_raw[0] > 1e-6 else 1.0
        sim_bone = [v / bone_init for v in sim_bone_raw]
        ref_bone_at_sim = interpolate(
            ref_bone["day"], ref_bone["bone_integrity"], sim_days, extrapolate=False)
        bone_rmse = compute_rmse(sim_bone, ref_bone_at_sim)

    # T cell density: peak-normalize
    has_tcell = "mean_tcell_wound" in sim
    tcell_rmse = 0.0
    sim_tcell = []
    tcell_peak = 0.0
    ref_tcell_at_sim = []
    if has_tcell:
        sim_tcell, tcell_peak = _window_normalize(sim["mean_tcell_wound"], sim_days, ref_tcell["day"], "peak") if ref_tcell is not None else (sim["mean_tcell_wound"], 0)
        ref_tcell_at_sim = interpolate(
            ref_tcell["day"], ref_tcell["tcell_normalized"], sim_days, extrapolate=False)
        tcell_rmse = compute_rmse(sim_tcell, ref_tcell_at_sim)

    # Synovial pannus: peak-normalize
    has_syn = "mean_synovial_wound" in sim
    syn_rmse = 0.0
    sim_syn = []
    syn_peak = 0.0
    ref_syn_at_sim = []
    if has_syn:
        sim_syn, syn_peak = _window_normalize(sim["mean_synovial_wound"], sim_days, ref_syn["day"], "peak") if ref_syn is not None else (sim["mean_synovial_wound"], 0)
        ref_syn_at_sim = interpolate(
            ref_syn["day"], ref_syn["synovial_normalized"], sim_days, extrapolate=False)
        syn_rmse = compute_rmse(sim_syn, ref_syn_at_sim)

    return dict(
        sim_tnf=sim_tnf, ref_tnf=ref_tnf,
        ref_tnf_at_sim=ref_tnf_at_sim, tnf_peak=tnf_peak,
        sim_il6=sim_il6, ref_il6=ref_il6,
        ref_il6_at_sim=ref_il6_at_sim, il6_peak=il6_peak,
        sim_cart=sim_cart, ref_cart=ref_cart,
        ref_cart_at_sim=ref_cart_at_sim,
        tnf_rmse=tnf_rmse, il6_rmse=il6_rmse, cart_rmse=cart_rmse,
        tnf_flare_rmse=tnf_flare_rmse, tnf_chronic_rmse=tnf_chronic_rmse,
        has_bone=has_bone, sim_bone=sim_bone, ref_bone=ref_bone,
        ref_bone_at_sim=ref_bone_at_sim, bone_rmse=bone_rmse,
        has_tcell=has_tcell, sim_tcell=sim_tcell, ref_tcell=ref_tcell,
        ref_tcell_at_sim=ref_tcell_at_sim, tcell_peak=tcell_peak,
        tcell_rmse=tcell_rmse,
        has_syn=has_syn, sim_syn=sim_syn, ref_syn=ref_syn,
        ref_syn_at_sim=ref_syn_at_sim, syn_peak=syn_peak,
        syn_rmse=syn_rmse,
    )


# ---------------------------------------------------------------------------
# Plot functions (draw into provided axes)
# ---------------------------------------------------------------------------

def plot_wound_panels(r, sim_days, axes):
    """Draw 4 wound panels into a 2x2 axes array."""
    cond = r.get("condition", "normal")
    ref_label = f"Lit. ({cond})" if cond != "normal" else "Literature"
    ref_kw = dict(REF_KW, label=ref_label)

    ax = axes[0, 0]
    ax.plot(sim_days, r["sim_closure"], **SIM_KW)
    ax.plot(r["ref_closure"]["day"], r["ref_closure"]["closure_pct"], **ref_kw)
    ax.axhline(90, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.set_ylabel("Wound closure (%)")
    ax.set_title("Wound Closure" + (f" ({cond})" if cond != "normal" else ""))
    ax.set_ylim(-2, 105)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.05, f"RMSE = {r['closure_rmse']:.1f}%",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray")

    ax = axes[0, 1]
    ax.plot(sim_days, r["sim_infl"], **SIM_KW)
    ax.plot(r["ref_infl"]["day"], r["ref_infl"]["inflammation_normalized"], **ref_kw)
    ax.set_ylabel("Inflammation (normalized)")
    ax.set_title("Inflammation Timecourse")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.95, f"RMSE = {r['inflammation_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[1, 0]
    ax.plot(sim_days, r["sim_neut"], **SIM_KW)
    ax.plot(r["ref_immune"]["day"], r["ref_immune"]["neutrophils_normalized"], **ref_kw)
    ax.set_ylabel("Neutrophils (normalized)")
    ax.set_title("Neutrophil Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['neut_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[1, 1]
    ax.plot(sim_days, r["sim_mac"], **SIM_KW)
    ax.plot(r["ref_immune"]["day"], r["ref_immune"]["macrophages_normalized"], **ref_kw)
    ax.set_ylabel("Macrophages (normalized)")
    ax.set_title("Macrophage Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['mac_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    for a in axes[-1]:
        a.set_xlabel("Time (days)")


def plot_fibroblast_panels(r, sim_days, axes):
    """Draw 3 fibroblast panels into axes array."""
    ax = axes[0]
    ax.plot(sim_days, r["sim_fibro"], **SIM_KW)
    ax.plot(r["ref_fibro"]["day"], r["ref_fibro"]["fibroblasts_normalized"], **REF_KW)
    ax.set_ylabel("Fibroblasts (normalized)")
    ax.set_title("Fibroblast Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['fibro_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[1]
    ax.plot(sim_days, r["sim_myofib"], **SIM_KW)
    ax.plot(r["ref_myofib"]["day"], r["ref_myofib"]["myofibroblasts_normalized"], **REF_KW)
    ax.set_ylabel("Myofibroblasts (normalized)")
    ax.set_title("Myofibroblast Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['myofib_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[2]
    ax.plot(sim_days, r["sim_collagen"], **SIM_KW)
    ax.plot(r["ref_collagen"]["day"], r["ref_collagen"]["collagen_normalized"], **REF_KW)
    ax.set_ylabel("Collagen (normalized)")
    ax.set_title("Collagen Deposition")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['collagen_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    axes[-1].set_xlabel("Time (days)")


def plot_tumor_panels(r, sim_days, axes):
    """Draw tumor panels into axes (2 or 3 element array)."""
    td = r["bcc_doubling_days"]

    # Left: log scale growth
    ax = axes[0]
    ax.plot(sim_days, r["sim_tumor"], **SIM_KW)
    if r["ref_tumor_exp"]:
        ax.plot(sim_days, r["ref_tumor_exp"], color=REF_COLOR, linewidth=1.5,
                linestyle="--", label=f"Ref (Td={td:.0f}d)")
    ax.set_ylabel("Tumor cells")
    ax.set_title("Tumor Growth")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    if r["observed_doubling"] < float("inf"):
        ax.text(0.98, 0.05, f"Obs Td = {r['observed_doubling']:.0f}d",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8, color="gray")

    # Right: Ki-67 or linear growth
    ax = axes[1]
    if r["has_cycling"]:
        ax.plot(sim_days, r["sim_ki67"], **SIM_KW)
        ax.axhline(r["bcc_ki67_pct"], color=REF_COLOR, linewidth=1.5,
                   linestyle="--",
                   label=f"BCC Ki-67 = {r['bcc_ki67_pct']:.1f}% (established)")
        ki67_scale = [surface_fraction(n) * 100 for n in r["sim_tumor"]]
        ax.plot(sim_days, ki67_scale, color="#7B9F35", linewidth=1.2,
                linestyle=":", label="Scale-adjusted est.")
        ax.set_ylabel("Cycling fraction (%)")
        ax.set_title("Ki-67 Proxy")
        ax.set_ylim(0, 105)
        ax.text(0.98, 0.85, f"Mean = {r['mean_ki67']:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="gray")
    else:
        ax.plot(sim_days, r["sim_tumor"], **SIM_KW)
        if r["ref_tumor_exp"]:
            ax.plot(sim_days, r["ref_tumor_exp"], color=REF_COLOR, linewidth=1.5,
                    linestyle="--", label=f"Ref (Td={td:.0f}d)")
        ax.set_ylabel("Tumor cells")
        ax.set_title("Tumor Growth (linear)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (days)")


def plot_microenvironment_panels(r, sim_days, axes):
    """Plot supported comparisons and explicitly label absent scores."""
    specs = [("tgfb", "TGF-b1 Kinetics", "tgfb_normalized"),
             ("vegf", "VEGF Kinetics", "vegf_normalized"),
             ("fn", "Fibronectin Kinetics", "fibronectin_normalized"),
             ("mmp", "MMP Activity", "mmp_normalized")]
    for ax, (key, title, column) in zip(axes.flat, specs):
        ax.plot(sim_days, r["sim_" + key], **SIM_KW)
        reference = r["ref_" + key]
        if reference is not None:
            ax.plot(reference["day"], reference[column], **REF_KW)
        score = r.get(key + "_rmse")
        label = f"RMSE = {score * 100:.1f}%" if score is not None and math.isfinite(score) else "Not tested"
        ax.set(title=title, ylabel="Normalized level", ylim=(-.05, 1.15), xlim=(0, 30))
        ax.legend(fontsize=8)
        ax.grid(True, alpha=.3)
        ax.text(.98, .85, label, transform=ax.transAxes, ha="right", fontsize=8, color="gray")
    for ax in axes[-1]:
        ax.set_xlabel("Time (days)")


def plot_ph_panel(r, sim_days, ax):
    """Draw wound pH (alkalinity) panel into a single axes."""
    ax.plot(sim_days, r["sim_ph"], **SIM_KW)
    ax.plot(r["ref_ph"]["day"], r["ref_ph"]["ph_alkalinity_normalized"], **REF_KW)
    ax.set_ylabel("Wound alkalinity (normalized)")
    ax.set_title("Wound pH Recovery")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['ph_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")
    ax.set_xlabel("Time (days)")


def plot_ra_panels(r, sim_days, axes):
    """Draw RA panels into axes array.

    Expects 3 axes for core panels (TNF, IL-6, cartilage).
    If extended data is available (bone, T cell, synovial), expects 6 axes.
    """
    ax = axes[0]
    ax.plot(sim_days, r["sim_tnf"], **SIM_KW)
    ax.plot(r["ref_tnf"]["day"], r["ref_tnf"]["tnf_alpha_normalized"], **REF_KW)
    ax.set_ylabel("TNF-alpha (normalized)")
    ax.set_title("TNF-alpha Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['tnf_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[1]
    ax.plot(sim_days, r["sim_il6"], **SIM_KW)
    ax.plot(r["ref_il6"]["day"], r["ref_il6"]["il6_normalized"], **REF_KW)
    ax.set_ylabel("IL-6 (normalized)")
    ax.set_title("IL-6 Kinetics")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.85, f"RMSE = {r['il6_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="gray")

    ax = axes[2]
    ax.plot(sim_days, r["sim_cart"], **SIM_KW)
    ax.plot(r["ref_cart"]["day"], r["ref_cart"]["cartilage_integrity"], **REF_KW)
    ax.set_ylabel("Cartilage integrity")
    ax.set_title("Cartilage Erosion")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, alpha=0.3)
    ax.text(0.98, 0.15, f"RMSE = {r['cart_rmse'] * 100:.1f}%",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray")

    # Extended panels (bone, T cell, synovial) if axes available
    if len(axes) < 6:
        axes[-1].set_xlabel("Time (days)")
        return

    if r.get("has_bone") and r["sim_bone"]:
        ax = axes[3]
        ax.plot(sim_days, r["sim_bone"], **SIM_KW)
        ax.plot(r["ref_bone"]["day"], r["ref_bone"]["bone_integrity"], **REF_KW)
        ax.set_ylabel("Bone integrity")
        ax.set_title("Subchondral Bone Erosion")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(True, alpha=0.3)
        ax.text(0.98, 0.15, f"RMSE = {r['bone_rmse'] * 100:.1f}%",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8, color="gray")
    else:
        axes[3].set_visible(False)

    if r.get("has_tcell") and r["sim_tcell"]:
        ax = axes[4]
        ax.plot(sim_days, r["sim_tcell"], **SIM_KW)
        ax.plot(r["ref_tcell"]["day"], r["ref_tcell"]["tcell_normalized"], **REF_KW)
        ax.set_ylabel("T cell density (normalized)")
        ax.set_title("T Cell Infiltration")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.text(0.98, 0.85, f"RMSE = {r['tcell_rmse'] * 100:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="gray")
    else:
        axes[4].set_visible(False)

    if r.get("has_syn") and r["sim_syn"]:
        ax = axes[5]
        ax.plot(sim_days, r["sim_syn"], **SIM_KW)
        ax.plot(r["ref_syn"]["day"], r["ref_syn"]["synovial_normalized"], **REF_KW)
        ax.set_ylabel("Pannus density (normalized)")
        ax.set_title("Synovial Pannus Growth")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.text(0.98, 0.85, f"RMSE = {r['syn_rmse'] * 100:.1f}%",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="gray")
    else:
        axes[5].set_visible(False)

    axes[-1].set_xlabel("Time (days)")


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def validation_report(wound=None, fibroblast=None, tumor=None, microenv=None,
                      ph=None, ra=None):
    """Machine-readable screening results; absence of evidence never passes.

    The existing 15% RMSE is an engineering screening threshold, not a claim
    of biological validity. Tumor comparisons have no agreed acceptance gate.
    """
    coverage = {}
    groups = [
        (wound, [("Wound closure", "closure_rmse", 1),
                 ("Inflammation", "inflammation_rmse", 100),
                 ("Neutrophils", "neut_rmse", 100),
                 ("Macrophages", "mac_rmse", 100)]),
        (fibroblast, [("Fibroblasts", "fibro_rmse", 100),
                     ("Myofibroblasts", "myofib_rmse", 100),
                     ("Collagen", "collagen_rmse", 100)]),
        (microenv, [("TGF-b", "tgfb_rmse", 100), ("VEGF", "vegf_rmse", 100),
                   ("Fibronectin", "fn_rmse", 100), ("MMP", "mmp_rmse", 100)]),
        (ph, [("pH", "ph_rmse", 100)]),
        (ra, [("TNF-alpha", "tnf_rmse", 100), ("IL-6", "il6_rmse", 100),
              ("Cartilage", "cart_rmse", 100), ("Bone", "bone_rmse", 100),
              ("T cells", "tcell_rmse", 100), ("Synovium", "syn_rmse", 100)])]
    for result, observables in groups:
        for name, key, scale in observables:
            value = result.get(key) if result is not None else None
            if result is not None and result is ra and key in ("bone_rmse", "tcell_rmse", "syn_rmse"):
                flag = {"bone_rmse": "has_bone", "tcell_rmse": "has_tcell", "syn_rmse": "has_syn"}[key]
                if not result.get(flag, False):
                    value = None
            if value is None or not math.isfinite(value):
                coverage[name] = dict(status="not_tested", reason="disabled, unavailable output, no condition-matched reference, or no date overlap")
            else:
                value *= scale
                coverage[name] = dict(status="pass" if math.isfinite(value) and value <= 15 else "fail",
                                      rmse_pct=value if math.isfinite(value) else None,
                                      threshold_pct=15)
    coverage["Tumor"] = dict(status="not_tested", reason="descriptive comparison only; acceptance criterion has not been established" if tumor else "disabled or unavailable output")
    tested = [r for r in coverage.values() if r["status"] != "not_tested"]
    status = "fail" if any(r["status"] == "fail" for r in tested) else ("pass" if tested else "not_tested")
    return dict(status=status, tested=len(tested), coverage=coverage,
                criterion="15% RMSE engineering screen; passing tested observables does not validate untested mechanisms")


def evaluate_run(sim, sim_days, config, condition):
    """Shared computation for command-line validation and the dashboard."""
    hw, hf, ht, hm, hp, hr = detect_modules(sim, config)
    results = dict(wound=validate_wound(sim, sim_days, condition) if hw else None,
                   fibroblast=validate_fibroblast(sim, sim_days, condition) if hf else None,
                   tumor=validate_tumor(sim, sim_days) if ht else None,
                   microenv=validate_microenvironment(sim, sim_days, condition) if hm else None,
                   ph=validate_ph(sim, sim_days) if hp and condition == "normal" else None,
                   ra=validate_ra(sim, sim_days) if hr else None)
    microenv = results["microenv"]
    if microenv is not None:
        for key, owner in [("tgfb", "fibroblast"), ("vegf", "angiogenesis"),
                           ("fn", "fibronectin"), ("mmp", "mmp")]:
            if not config.get("skin", {}).get(owner, {}).get("enabled", False):
                microenv[key + "_rmse"] = None
    report = validation_report(**results)
    report["condition"] = condition
    report["comparison_scope"] = "Only the overlap with each reference's recorded dates; normalization uses that same window."
    names = {"closure": "Wound closure", "inflammation": "Inflammation",
             "neut": "Neutrophils", "mac": "Macrophages", "fibro": "Fibroblasts",
             "myofib": "Myofibroblasts", "collagen": "Collagen", "tgfb": "TGF-b",
             "vegf": "VEGF", "fn": "Fibronectin", "mmp": "MMP", "ph": "pH",
             "tnf": "TNF-alpha", "il6": "IL-6", "cart": "Cartilage",
             "bone": "Bone", "tcell": "T cells", "syn": "Synovium"}
    for result in results.values():
        if result is None:
            continue
        for key, name in names.items():
            prefix = "infl" if key == "inflammation" else key
            reference = result.get("ref_" + prefix + "_at_sim")
            if reference is None:
                continue
            dates = [day for day, value in zip(sim_days, reference) if math.isfinite(value)]
            report["coverage"][name]["comparison_dates"] = dict(
                start_day=min(dates) if dates else None,
                end_day=max(dates) if dates else None,
                simulation_samples=len(dates),
                uncertainty="Interpolated simulation samples are not biological replicates.")
    return results, report


def saved_config_path(csv_path):
    """Resolve evidence saved beside a run; never infer it from today's config."""
    parent = os.path.dirname(os.path.abspath(csv_path))
    for directory in (parent, os.path.dirname(parent)):
        for filename in ("run-config.toml", "bdm.toml"):
            candidate = os.path.join(directory, filename)
            if os.path.isfile(candidate):
                return candidate
    return None


def print_summary(wound=None, fibroblast=None, tumor=None, microenv=None,
                  ph=None, ra=None):
    """Print every observable's screening status and coverage limits."""
    report = validation_report(wound, fibroblast, tumor, microenv, ph, ra)
    print("=" * 60)
    print("  skibidy Validation Summary")
    for name, item in report["coverage"].items():
        if item["status"] == "not_tested":
            print(f"  {name}: NOT TESTED ({item['reason']})")
        else:
            print(f"  {name}: {item['status'].upper()} RMSE = {item['rmse_pct']:.2f}%")
    if wound:
        for name, key in [("Inflammatory 0-3d", "infl_rmse"),
                          ("Proliferative 3-14d", "prolif_rmse"),
                          ("Remodeling 14-28d", "remod_rmse")]:
            score = wound[key]
            value = f"{score:.2f}%" if math.isfinite(score) else "not tested (no reference overlap)"
            print(f"    {name}: {value}")
    if tumor:
        print(f"  Tumor descriptive doubling time: observed={tumor['observed_doubling']:.0f}d reference={tumor['bcc_doubling_days']:.0f}d")
    print(f"  {report['status'].upper()}: {report['tested']} tested observables")
    print(f"  {report['criterion']}")
    print("=" * 60)
    return report["status"] == "pass"
