#!/usr/bin/env python3
"""Generate publication-quality figures from consensus and study data.

Produces validation panels, comparison overlays, treatment bar charts, and
synergy heatmaps at 300 DPI in PNG and/or PDF.

Reads consensus CSVs (with mean + _std columns) from batch runs, overlays
published literature curves, and computes RMSE. Also accepts single-run
metrics CSVs (std columns absent; bands are omitted).

Usage:
    python3 scripts/figures.py [options]

Options:
    --normal-consensus PATH     Consensus CSV for normal wound (auto-detect)
    --diabetic-consensus PATH   Consensus CSV for diabetic wound (auto-detect)
    --treatment-csv PATH        Treatment comparison CSV
    --output DIR                Output directory (default: studies/figures/)
    --format png,pdf            Output formats (default: both)
    --fig N                     Generate only figure N (1-5, S for supplementary)
"""

import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

# Resolve the shared computation when invoked by absolute script path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from literature.lib import (load_csv, peak_normalize, validate_wound, validate_fibroblast,
                 validate_microenvironment, evaluate_run, saved_config_path,
                 condition_from_config, wound_comparison_days, show_normalized_range, SIM_COLOR, REF_COLOR)
from batch.lib import parse_toml, validate_run_metrics


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

DIABETIC_COLOR = "#9B59B6"
BAND_ALPHA = 0.2

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

_REF_KW = dict(color=REF_COLOR, linewidth=1.2, linestyle="--",
               marker="o", markersize=3, label="Modeling target", zorder=5)
_SIM_KW = dict(color=SIM_COLOR, linewidth=1.8, label="Simulation", zorder=4)
_DIAB_KW = dict(color=DIABETIC_COLOR, linewidth=1.8, label="Diabetic", zorder=4)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_study_consensus(study_name):
    """Find consensus CSV in a study's results directory."""
    base = os.path.join(os.path.dirname(__file__), os.pardir, "studies",
                        study_name, "results")
    csv_path = os.path.join(base, "consensus.csv")
    return csv_path if os.path.exists(csv_path) else None


def load_consensus(path):
    """Load a consensus CSV. Returns dict with mean values and std values.

    Consensus CSVs have columns like 'metric' and 'metric_std'.
    Returns: {metric: [values], metric_std: [values], ...}
    """
    config_path = saved_config_path(path)
    if config_path is None:
        raise ValueError("No saved run configuration beside figure input")
    config = parse_toml(config_path)
    validate_run_metrics(path, config)
    data = load_csv(path)
    sim_days = [h / 24 for h in data["time_h"]]
    results, report = evaluate_run(data, sim_days, config, condition_from_config(config))
    print(report["evidence"])
    data["_config"], data["_validation"] = config, results
    return data


def add_rmse(ax, rmse, pct=True):
    """Add RMSE text to bottom-right of panel."""
    if pct:
        show_normalized_range(ax)
    fmt = "NOT TESTED" if rmse is None or not math.isfinite(rmse) else f"{rmse * 100 if pct else rmse:.1f}{'%' if pct else ' pp'}"
    ax.text(0.97, 0.05, f"RMSE = {fmt}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="#666666")


def add_label(ax, letter):
    """Add panel letter label."""
    ax.text(-0.15, 1.08, letter, transform=ax.transAxes,
            fontsize=13, fontweight="bold", va="top")


def band(ax, days, mean, std, color=SIM_COLOR, alpha=BAND_ALPHA):
    """Plot mean line with SD band."""
    lo = [m - s for m, s in zip(mean, std)]
    hi = [m + s for m, s in zip(mean, std)]
    ax.fill_between(days, lo, hi, color=color, alpha=alpha, linewidth=0)


def savefig(fig, path, formats):
    """Save figure in requested formats."""
    for fmt in formats:
        out = f"{path}.{fmt}"
        fig.savefig(out, dpi=300)
    plt.close(fig)


def consensus_days(data):
    """Extract days array from consensus data."""
    if "_config" in data:
        return wound_comparison_days([h / 24 for h in data["time_h"]], data["_config"])
    if "time_days" in data:
        return data["time_days"]
    return [h / 24.0 for h in data["time_h"]]


def consensus_std(data, key):
    """Get std column, falling back to zeros."""
    std_key = f"{key}_std"
    if std_key in data:
        return data[std_key]
    return [0.0] * len(data[key])


# ---------------------------------------------------------------------------
# Validation helpers (consensus version of lib.py validate functions)
# ---------------------------------------------------------------------------

def _consensus_group(data, days, group, condition=None):
    """Reuse saved-run comparisons. SD bands are seed spread, not reference CI."""
    if "_validation" in data:
        if condition is not None and condition != condition_from_config(data["_config"]):
            raise ValueError("Figure condition differs from the saved run configuration")
        result = data["_validation"][group]
    else:
        # Pure helpers are also useful for controlled in-memory comparisons.
        validator = {"wound": validate_wound, "fibroblast": validate_fibroblast,
                     "microenv": validate_microenvironment}[group]
        result = validator(data, days, condition or "normal")
    if result is None:
        return None
    result = dict(result)
    mappings = {
        "wound": [("closure", "wound_closure_pct", None),
                  ("infl", "mean_infl_wound", "infl_peak"),
                  ("neut", "n_neutrophils", "neut_peak"),
                  ("mac", "n_macrophages", "mac_peak")],
        "fibroblast": [("myofib", "n_myofibroblasts", "myofib_peak"),
                       ("collagen", "mean_collagen_wound", "collagen_final"),
                       ("fibro", "n_fibroblasts", "fibro_peak")],
        "microenv": [("tgfb", "mean_tgfb_wound", "tgfb_peak"),
                     ("vegf", "mean_vegf_wound", "vegf_peak"),
                     ("fn", "mean_fibronectin_wound", "fn_peak"),
                     ("mmp", "mean_mmp_wound", "mmp_peak")]}
    for prefix, column, scale_key in mappings[group]:
        scale = result.get(scale_key, 0) if scale_key else 1
        result[prefix + "_std"] = [s / scale if scale > 0 else s
                                    for s in consensus_std(data, column)]
    return result
def validate_consensus_wound(data, days, condition="normal"):
    return _consensus_group(data, days, "wound", condition)
def validate_consensus_fibroblast(data, days):
    return _consensus_group(data, days, "fibroblast")
def validate_consensus_microenv(data, days):
    return _consensus_group(data, days, "microenv")


# ---------------------------------------------------------------------------
# Figure 1: Normal wound validation (4x3, 11 panels)
# ---------------------------------------------------------------------------

def fig1_normal_validation(data, days, out_dir, formats):
    """11-panel normal validation with consensus bands."""
    print("  Fig 1: Normal wound validation...")
    wound = validate_consensus_wound(data, days, "normal")
    fibro = validate_consensus_fibroblast(data, days)
    micro = validate_consensus_microenv(data, days)

    fig = plt.figure(figsize=(10, 11))
    gs = gridspec.GridSpec(4, 3, hspace=0.4, wspace=0.35)
    labels = iter("ABCDEFGHIJK")

    # Row 1: closure, inflammation, neutrophils
    panels_r1 = [
        ("Wound closure (%)", wound["sim_closure"], wound["closure_std"],
         wound["ref_closure"]["day"], wound["ref_closure"]["closure_pct"],
         wound["closure_rmse"], False, (-2, 105)),
        ("Inflammation (norm.)", wound["sim_infl"], wound["infl_std"],
         wound["ref_infl"]["day"], wound["ref_infl"]["inflammation_normalized"],
         wound["inflammation_rmse"], True, (-0.05, 1.15)),
        ("Neutrophils (norm.)", wound["sim_neut"], wound["neut_std"],
         wound["ref_immune"]["day"], wound["ref_immune"]["neutrophils_normalized"],
         wound["neut_rmse"], True, (-0.05, 1.15)),
    ]
    for col, (ylabel, sim, std, ref_x, ref_y, rmse, pct, ylim) in enumerate(panels_r1):
        ax = fig.add_subplot(gs[0, col])
        ax.plot(days, sim, **_SIM_KW)
        band(ax, days, sim, std)
        ax.plot(ref_x, ref_y, **_REF_KW)
        if col == 0:
            ax.axhline(90, color="#999", linestyle=":", linewidth=0.6, alpha=0.5)
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7, loc="lower right" if col == 0 else "best")
        ax.grid(True, alpha=0.15)
        add_rmse(ax, rmse, pct=pct)
        add_label(ax, next(labels))

    # Row 2: macrophages, fibroblasts, myofibroblasts
    panels_r2 = [
        ("Macrophages (norm.)", wound["sim_mac"], wound["mac_std"],
         wound["ref_immune"]["day"], wound["ref_immune"]["macrophages_normalized"],
         wound["mac_rmse"], True, (-0.05, 1.15)),
        ("Fibroblasts (norm.)", fibro["sim_fibro"], fibro["fibro_std"],
         fibro["ref_fibro"]["day"], fibro["ref_fibro"]["fibroblasts_normalized"],
         fibro["fibro_rmse"], True, (-0.05, 1.15)),
        ("Myofibroblasts (norm.)", fibro["sim_myofib"], fibro["myofib_std"],
         fibro["ref_myofib"]["day"], fibro["ref_myofib"]["myofibroblasts_normalized"],
         fibro["myofib_rmse"], True, (-0.05, 1.15)),
    ]
    for col, (ylabel, sim, std, ref_x, ref_y, rmse, pct, ylim) in enumerate(panels_r2):
        ax = fig.add_subplot(gs[1, col])
        ax.plot(days, sim, **_SIM_KW)
        band(ax, days, sim, std)
        ax.plot(ref_x, ref_y, **_REF_KW)
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, rmse, pct=pct)
        add_label(ax, next(labels))

    # Row 3: collagen, TGF-b, VEGF
    panels_r3 = [
        ("Collagen (norm.)", fibro["sim_collagen"], fibro["collagen_std"],
         fibro["ref_collagen"]["day"], fibro["ref_collagen"]["collagen_normalized"],
         fibro["collagen_rmse"], True, (-0.05, 1.15)),
        ("TGF-\u03b21 (norm.)", micro["sim_tgfb"], micro["tgfb_std"],
         micro["ref_tgfb"]["day"], micro["ref_tgfb"]["tgfb_normalized"],
         micro["tgfb_rmse"], True, (-0.05, 1.15)),
        ("VEGF (norm.)", micro["sim_vegf"], micro["vegf_std"],
         micro["ref_vegf"]["day"], micro["ref_vegf"]["vegf_normalized"],
         micro["vegf_rmse"], True, (-0.05, 1.15)),
    ]
    for col, (ylabel, sim, std, ref_x, ref_y, rmse, pct, ylim) in enumerate(panels_r3):
        ax = fig.add_subplot(gs[2, col])
        ax.plot(days, sim, **_SIM_KW)
        band(ax, days, sim, std)
        ax.plot(ref_x, ref_y, **_REF_KW)
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, rmse, pct=pct)
        add_label(ax, next(labels))

    # Row 4: fibronectin, MMP
    panels_r4 = [
        ("Fibronectin (norm.)", micro["sim_fn"], micro["fn_std"],
         micro["ref_fn"]["day"], micro["ref_fn"]["fibronectin_normalized"],
         micro["fn_rmse"], True, (-0.05, 1.15)),
        ("MMP activity (norm.)", micro["sim_mmp"], micro["mmp_std"],
         micro["ref_mmp"]["day"], micro["ref_mmp"]["mmp_normalized"],
         micro["mmp_rmse"], True, (-0.05, 1.15)),
    ]
    for col, (ylabel, sim, std, ref_x, ref_y, rmse, pct, ylim) in enumerate(panels_r4):
        ax = fig.add_subplot(gs[3, col])
        ax.plot(days, sim, **_SIM_KW)
        band(ax, days, sim, std)
        ax.plot(ref_x, ref_y, **_REF_KW)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Time (days)")
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, rmse, pct=pct)
        add_label(ax, next(labels))

    fig.suptitle("Normal Wound Engineering Screen (qualitative targets)",
                 fontsize=13, fontweight="bold", y=0.995)
    savefig(fig, os.path.join(out_dir, "fig1_normal_validation"), formats)
    return wound, fibro, micro


# ---------------------------------------------------------------------------
# Figure 2: Diabetic wound validation (2x3, 5 panels)
# ---------------------------------------------------------------------------

def fig2_diabetic_validation(data, days, out_dir, formats):
    """Diabetic validation with consensus bands."""
    print("  Fig 2: Diabetic wound validation...")
    wound = validate_consensus_wound(data, days, "diabetic")

    has_fibro = "n_myofibroblasts" in data
    fibro = validate_consensus_fibroblast(data, days) if has_fibro else None

    has_vegf = ("mean_vegf_wound" in data
                and max(data["mean_vegf_wound"]) > 0)

    n_panels = 4 + (1 if has_vegf else 0)
    ncols = 3
    nrows = 2
    fig = plt.figure(figsize=(10, 6))
    gs = gridspec.GridSpec(nrows, ncols, hspace=0.4, wspace=0.35)
    labels = iter("ABCDE")

    # Panel A: closure
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(days, wound["sim_closure"], **_SIM_KW)
    band(ax, days, wound["sim_closure"], wound["closure_std"])
    ax.plot(wound["ref_closure"]["day"], wound["ref_closure"]["closure_pct"],
            **dict(_REF_KW, label="Lit. (diabetic)"))
    ax.axhline(90, color="#999", linestyle=":", linewidth=0.6, alpha=0.5)
    ax.set_ylabel("Wound closure (%)")
    ax.set_ylim(-2, 105)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(True, alpha=0.15)
    add_rmse(ax, wound["closure_rmse"], pct=False)
    add_label(ax, next(labels))

    # Panel B: inflammation
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(days, wound["sim_infl"], **_SIM_KW)
    band(ax, days, wound["sim_infl"], wound["infl_std"])
    ax.plot(wound["ref_infl"]["day"],
            wound["ref_infl"]["inflammation_normalized"],
            **dict(_REF_KW, label="Lit. (diabetic)"))
    ax.set_ylabel("Inflammation (norm.)")
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlim(0, 30)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.15)
    add_rmse(ax, wound["inflammation_rmse"])
    add_label(ax, next(labels))

    # Panel C: myofibroblasts
    if fibro:
        ax = fig.add_subplot(gs[0, 2])
        ax.plot(days, fibro["sim_myofib"], **_SIM_KW)
        band(ax, days, fibro["sim_myofib"], fibro["myofib_std"])
        ax.plot(fibro["ref_myofib"]["day"],
                fibro["ref_myofib"]["myofibroblasts_normalized"], **_REF_KW)
        ax.set_ylabel("Myofibroblasts (norm.)")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, fibro["myofib_rmse"])
        add_label(ax, next(labels))

    # Panel D: collagen
    if fibro:
        ax = fig.add_subplot(gs[1, 0])
        ax.plot(days, fibro["sim_collagen"], **_SIM_KW)
        band(ax, days, fibro["sim_collagen"], fibro["collagen_std"])
        ax.plot(fibro["ref_collagen"]["day"],
                fibro["ref_collagen"]["collagen_normalized"], **_REF_KW)
        ax.set_ylabel("Collagen (norm.)")
        ax.set_xlabel("Time (days)")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, fibro["collagen_rmse"])
        add_label(ax, next(labels))

    # Panel E: VEGF (no lit reference for diabetic)
    if has_vegf:
        ax = fig.add_subplot(gs[1, 1])
        sim_vegf, vegf_peak = peak_normalize(data["mean_vegf_wound"])
        vegf_std_raw = consensus_std(data, "mean_vegf_wound")
        vegf_std = [s / vegf_peak if vegf_peak > 0 else 0
                    for s in vegf_std_raw]
        ax.plot(days, sim_vegf, **_SIM_KW)
        band(ax, days, sim_vegf, vegf_std)
        ax.set_ylabel("VEGF (norm.)")
        ax.set_xlabel("Time (days)")
        ax.set_ylim(-0.05, 1.15)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_label(ax, next(labels))

    fig.suptitle("Diabetic Wound Engineering Screen (qualitative targets)",
                 fontsize=13, fontweight="bold", y=0.995)
    savefig(fig, os.path.join(out_dir, "fig2_diabetic_validation"), formats)


# ---------------------------------------------------------------------------
# Figure 3: Normal vs Diabetic comparison (2x3, 6 panels)
# ---------------------------------------------------------------------------

def fig3_comparison(norm_data, norm_days, diab_data, diab_days, out_dir, formats):
    """Side-by-side normal vs diabetic comparison."""
    print("  Fig 3: Normal vs Diabetic comparison...")
    fig = plt.figure(figsize=(10, 6))
    gs = gridspec.GridSpec(2, 3, hspace=0.4, wspace=0.35)
    labels = iter("ABCDEF")

    panels = [
        ("Wound closure (%)", "wound_closure_pct", (-2, 105), False),
        ("Inflammation (norm.)", "mean_infl_wound", None, True),
        ("Neutrophils", "n_neutrophils", None, True),
        ("Macrophages", "n_macrophages", None, True),
        ("Collagen (norm.)", "mean_collagen_wound", None, True),
        ("Scar magnitude", "scar_magnitude", None, False),
    ]

    for idx, (ylabel, col, ylim, do_norm) in enumerate(panels):
        row, c = divmod(idx, 3)
        ax = fig.add_subplot(gs[row, c])

        # Normal
        n_vals = norm_data[col]
        n_std = consensus_std(norm_data, col)
        if do_norm:
            n_vals, peak = peak_normalize(n_vals)
            n_std = [s / peak if peak > 0 else 0 for s in n_std]

        ax.plot(norm_days, n_vals, color=SIM_COLOR, linewidth=1.8,
                label="Normal", zorder=4)
        band(ax, norm_days, n_vals, n_std, color=SIM_COLOR)

        # Diabetic
        d_vals = diab_data[col]
        d_std = consensus_std(diab_data, col)
        if do_norm:
            d_vals, dpeak = peak_normalize(d_vals)
            d_std = [s / dpeak if dpeak > 0 else 0 for s in d_std]

        ax.plot(diab_days, d_vals, color=DIABETIC_COLOR, linewidth=1.8,
                label="Diabetic", zorder=3)
        band(ax, diab_days, d_vals, d_std, color=DIABETIC_COLOR)

        ax.set_ylabel(ylabel)
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        if row == 1:
            ax.set_xlabel("Time (days)")
        add_label(ax, next(labels))

    fig.suptitle("Normal vs Diabetic Wound Healing",
                 fontsize=13, fontweight="bold", y=0.995)
    savefig(fig, os.path.join(out_dir, "fig3_condition_comparison"), formats)


# ---------------------------------------------------------------------------
# Figure 4: Treatment efficacy (1x2, bar charts)
# ---------------------------------------------------------------------------

TREAT_COLORS = {
    "anti_inflammatory": "#E74C3C",
    "growth_factor": "#27AE60",
    "hbo": "#3498DB",
    "doxycycline": "#F39C12",
    "moisture": "#1ABC9C",
    "msc": "#8E44AD",
    "npwt": "#2C3E50",
    "combination": "#E67E22",
}

TREAT_LABELS = {
    "anti_inflammatory": "Anti-inflammatory",
    "growth_factor": "Growth factor",
    "hbo": "HBO",
    "doxycycline": "Doxycycline",
    "moisture": "Moisture",
    "msc": "MSC",
    "npwt": "NPWT",
    "combination": "Combination",
}


def fig4_treatment_efficacy(treat_csv, out_dir, formats):
    """Bar charts of single-treatment efficacy."""
    print("  Fig 4: Treatment efficacy...")
    data = load_csv(treat_csv)

    # Extract single treatments only (no + combos)
    singles = []
    baseline_idx = None
    for i, name in enumerate(data["treatment"]):
        if name == "baseline":
            baseline_idx = i
        elif "+" not in name and name != "combination":
            singles.append(i)

    if baseline_idx is None:
        print("    Warning: no baseline found in treatment CSV")
        return

    bl_time = data["time_to_90pct_days"][baseline_idx]
    bl_scar = data["scar_magnitude"][baseline_idx]

    # Sort by time to 90%
    singles_by_time = sorted(singles,
                             key=lambda i: data["time_to_90pct_days"][i])
    # Sort by scar
    singles_by_scar = sorted(singles,
                             key=lambda i: data["scar_magnitude"][i])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: Time to 90% closure
    names_t = [data["treatment"][i] for i in singles_by_time]
    vals_t = [data["time_to_90pct_days"][i] for i in singles_by_time]
    colors_t = [TREAT_COLORS.get(n, "#999") for n in names_t]
    labels_t = [TREAT_LABELS.get(n, n) for n in names_t]

    y_pos = range(len(names_t))
    ax1.barh(y_pos, vals_t, color=colors_t, height=0.6, zorder=3)
    ax1.axvline(bl_time, color="#999", linestyle="--", linewidth=1.2,
                label=f"Baseline ({bl_time:.0f}d)", zorder=2)
    ax1.set_yticks(list(y_pos))
    ax1.set_yticklabels(labels_t)
    ax1.set_xlabel("Time to 90% closure (days)")
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.15, axis="x")
    ax1.invert_yaxis()
    add_label(ax1, "A")

    # Panel B: Scar magnitude
    names_s = [data["treatment"][i] for i in singles_by_scar]
    vals_s = [data["scar_magnitude"][i] for i in singles_by_scar]
    colors_s = [TREAT_COLORS.get(n, "#999") for n in names_s]
    labels_s = [TREAT_LABELS.get(n, n) for n in names_s]

    ax2.barh(range(len(names_s)), vals_s, color=colors_s, height=0.6, zorder=3)
    ax2.axvline(bl_scar, color="#999", linestyle="--", linewidth=1.2,
                label=f"Baseline ({bl_scar:.2f})", zorder=2)
    ax2.set_yticks(list(range(len(names_s))))
    ax2.set_yticklabels(labels_s)
    ax2.set_xlabel("Scar magnitude")
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.15, axis="x")
    ax2.invert_yaxis()
    add_label(ax2, "B")

    fig.suptitle("Single Treatment Efficacy (Diabetic Wound)",
                 fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "fig4_treatment_efficacy"), formats)


# ---------------------------------------------------------------------------
# Figure 5: Treatment synergy heatmap
# ---------------------------------------------------------------------------

def fig5_synergy_heatmap(treat_csv, out_dir, formats):
    """Pairwise treatment interaction heatmap."""
    print("  Fig 5: Treatment synergy heatmap...")
    data = load_csv(treat_csv)

    treatments = ["anti_inflammatory", "doxycycline", "growth_factor",
                   "hbo", "moisture", "msc", "npwt"]
    n = len(treatments)

    # Find baseline
    bl_time = None
    for i, name in enumerate(data["treatment"]):
        if name == "baseline":
            bl_time = data["time_to_90pct_days"][i]
            break
    if bl_time is None or bl_time == 0:
        print("    Warning: no valid baseline found")
        return

    # Build lookup: treatment name -> time_to_90pct_days
    lookup = {}
    for i, name in enumerate(data["treatment"]):
        lookup[name] = data["time_to_90pct_days"][i]

    # Compute pairwise improvement matrix
    matrix = [[float("nan")] * n for _ in range(n)]

    for i in range(n):
        # Diagonal: single treatment improvement
        t = treatments[i]
        if t in lookup:
            matrix[i][i] = 100 * (1 - lookup[t] / bl_time)

    for i in range(n):
        for j in range(i + 1, n):
            # Find all combos containing both treatments[i] and treatments[j]
            t_i, t_j = treatments[i], treatments[j]
            improvements = []
            for name, val in lookup.items():
                parts = set(name.split("+"))
                if t_i in parts and t_j in parts:
                    improvements.append(100 * (1 - val / bl_time))
            if improvements:
                avg = sum(improvements) / len(improvements)
                matrix[i][j] = avg
                matrix[j][i] = avg

    fig, ax = plt.subplots(figsize=(7, 6))
    labels = [TREAT_LABELS.get(t, t) for t in treatments]

    # Plot heatmap manually with imshow
    arr = []
    for row in matrix:
        arr.append([v if not math.isnan(v) else 0 for v in row])

    im = ax.imshow(arr, cmap="RdYlGn", aspect="auto",
                   vmin=-10, vmax=60)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=8)

    # Add text annotations
    for i in range(n):
        for j in range(n):
            val = matrix[i][j]
            if not math.isnan(val):
                color = "white" if val < 10 or val > 50 else "black"
                ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                        fontsize=8, color=color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label="% improvement over baseline")
    ax.set_title("Pairwise Treatment Synergy (Time to 90% Closure)",
                 fontsize=11, fontweight="bold", pad=12)
    fig.tight_layout()
    savefig(fig, os.path.join(out_dir, "fig5_treatment_synergy"), formats)


# ---------------------------------------------------------------------------
# Supplementary: individual panels
# ---------------------------------------------------------------------------

def supplementary_panels(data, days, condition, out_dir, formats):
    """Save individual panels as standalone figures."""
    tag = condition
    print(f"  Supplementary panels ({tag})...")
    wound = validate_consensus_wound(data, days, condition)

    panels = [
        (f"figS_{tag}_closure", "Wound closure (%)",
         wound["sim_closure"], wound["closure_std"],
         wound["ref_closure"]["day"], wound["ref_closure"]["closure_pct"],
         wound["closure_rmse"], False, (-2, 105)),
        (f"figS_{tag}_inflammation", "Inflammation (norm.)",
         wound["sim_infl"], wound["infl_std"],
         wound["ref_infl"]["day"], wound["ref_infl"]["inflammation_normalized"],
         wound["inflammation_rmse"], True, (-0.05, 1.15)),
        (f"figS_{tag}_neutrophils", "Neutrophils (norm.)",
         wound["sim_neut"], wound["neut_std"],
         wound["ref_immune"]["day"], wound["ref_immune"]["neutrophils_normalized"],
         wound["neut_rmse"], True, (-0.05, 1.15)),
        (f"figS_{tag}_macrophages", "Macrophages (norm.)",
         wound["sim_mac"], wound["mac_std"],
         wound["ref_immune"]["day"], wound["ref_immune"]["macrophages_normalized"],
         wound["mac_rmse"], True, (-0.05, 1.15)),
    ]

    has_fibro = "n_myofibroblasts" in data
    fibro = validate_consensus_fibroblast(data, days) if has_fibro else None
    if fibro is not None:
        panels.extend([
            (f"figS_{tag}_fibroblasts", "Fibroblasts (norm.)",
             fibro["sim_fibro"], fibro["fibro_std"],
             fibro["ref_fibro"]["day"],
             fibro["ref_fibro"]["fibroblasts_normalized"],
             fibro["fibro_rmse"], True, (-0.05, 1.15)),
            (f"figS_{tag}_myofibroblasts", "Myofibroblasts (norm.)",
             fibro["sim_myofib"], fibro["myofib_std"],
             fibro["ref_myofib"]["day"],
             fibro["ref_myofib"]["myofibroblasts_normalized"],
             fibro["myofib_rmse"], True, (-0.05, 1.15)),
            (f"figS_{tag}_collagen", "Collagen (norm.)",
             fibro["sim_collagen"], fibro["collagen_std"],
             fibro["ref_collagen"]["day"],
             fibro["ref_collagen"]["collagen_normalized"],
             fibro["collagen_rmse"], True, (-0.05, 1.15)),
        ])

    micro = validate_consensus_microenv(data, days) if "mean_tgfb_wound" in data else None
    if micro is not None:
        for prefix, label, reference_column in (
                ("tgfb", "TGF-beta1", "tgfb_normalized"),
                ("vegf", "VEGF", "vegf_normalized"),
                ("fn", "Fibronectin", "fibronectin_normalized"),
                ("mmp", "MMP activity", "mmp_normalized")):
            ref = micro["ref_" + prefix]
            if ref is None or micro[prefix + "_rmse"] is None:
                continue
            panels.append((f"figS_{tag}_{prefix}", label + " (norm.)",
                           micro["sim_" + prefix], micro[prefix + "_std"],
                           ref["day"], ref[reference_column],
                           micro[prefix + "_rmse"], True, (-0.05, 1.15)))

    for name, ylabel, sim, std, ref_x, ref_y, rmse, pct, ylim in panels:
        fig, ax = plt.subplots(figsize=(4.5, 3.5))
        ax.plot(days, sim, **_SIM_KW)
        band(ax, days, sim, std)
        ax.plot(ref_x, ref_y, **_REF_KW)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Time (days)")
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 30)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.15)
        add_rmse(ax, rmse, pct=pct)
        fig.tight_layout()
        savefig(fig, os.path.join(out_dir, name), formats)

    print(f"    {len(panels)} panels saved")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    normal_path = None
    diabetic_path = None
    treat_path = os.path.join(os.path.dirname(__file__), os.pardir,
                              "studies", "diabetic-example",
                              "treatment_comparison.csv")
    out_dir = os.path.join(os.path.dirname(__file__), os.pardir,
                           "studies", "figures")
    formats = ["png", "pdf"]
    only_fig = None

    i = 0
    while i < len(args):
        if args[i] == "--normal-consensus" and i + 1 < len(args):
            normal_path = args[i + 1]; i += 2
        elif args[i] == "--diabetic-consensus" and i + 1 < len(args):
            diabetic_path = args[i + 1]; i += 2
        elif args[i] == "--treatment-csv" and i + 1 < len(args):
            treat_path = args[i + 1]; i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            out_dir = args[i + 1]; i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            formats = args[i + 1].split(","); i += 2
        elif args[i] == "--fig" and i + 1 < len(args):
            only_fig = args[i + 1]; i += 2
        elif args[i] in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)

    # Auto-detect consensus paths from studies
    if normal_path is None:
        normal_path = find_study_consensus("wound")
        if normal_path is None:
            print("Error: no normal consensus found. Run batch first or use --normal-consensus.")
            sys.exit(1)
    if diabetic_path is None:
        diabetic_path = find_study_consensus("diabetic-wound")

    os.makedirs(out_dir, exist_ok=True)
    print(f"Generating figures in {out_dir}/")
    print(f"  Normal consensus: {normal_path}")
    if diabetic_path:
        print(f"  Diabetic consensus: {diabetic_path}")
    if os.path.exists(treat_path):
        print(f"  Treatment data: {treat_path}")
    print()

    # Load data
    norm_data = load_consensus(normal_path)
    norm_days = consensus_days(norm_data)

    diab_data = None
    diab_days = None
    if diabetic_path and os.path.exists(diabetic_path):
        diab_data = load_consensus(diabetic_path)
        diab_days = consensus_days(diab_data)

    do = lambda f: only_fig is None or only_fig == f

    # Fig 1: Normal validation
    if do("1"):
        fig1_normal_validation(norm_data, norm_days, out_dir, formats)

    # Fig 2: Diabetic validation
    if do("2") and diab_data:
        fig2_diabetic_validation(diab_data, diab_days, out_dir, formats)

    # Fig 3: Normal vs Diabetic comparison
    if do("3") and diab_data:
        fig3_comparison(norm_data, norm_days, diab_data, diab_days,
                        out_dir, formats)

    # Fig 4: Treatment efficacy
    if do("4") and os.path.exists(treat_path):
        fig4_treatment_efficacy(treat_path, out_dir, formats)

    # Fig 5: Treatment synergy
    if do("5") and os.path.exists(treat_path):
        fig5_synergy_heatmap(treat_path, out_dir, formats)

    # Supplementary
    if do("S"):
        supp_dir = os.path.join(out_dir, "supplementary")
        os.makedirs(supp_dir, exist_ok=True)
        supplementary_panels(norm_data, norm_days, "normal", supp_dir, formats)
        if diab_data:
            supplementary_panels(diab_data, diab_days, "diabetic",
                                 supp_dir, formats)

    print("\nDone.")


if __name__ == "__main__":
    main()
