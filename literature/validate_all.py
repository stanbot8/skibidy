#!/usr/bin/env python3
"""Validation dashboard for skibidy.

Single entry point: loads metrics once, computes once, prints once, plots once.
Generates validation_dashboard.png plus per-module PNGs.

Usage:
    python3 literature/validate_all.py [path/to/metrics.csv] [--normal|--diabetic|--burn|--pressure|--surgical|--rheumatoid]

Condition auto-detection reads the run's saved configuration.
Explicit condition flags must agree with that configuration.
"""

import os
import sys
import argparse
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from batch.lib import parse_toml, validate_run_metrics

QUICK = "--quick" in sys.argv
if QUICK:
    sys.argv.remove("--quick")

if not QUICK:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from lib import (load_csv, plots_dir, detect_condition, detect_modules,
                 validate_wound, validate_fibroblast, validate_tumor,
                 validate_microenvironment, validate_ph, validate_ra,
                 print_summary, evaluate_run, saved_config_path)
if not QUICK:
    from lib import (plot_wound_panels, plot_fibroblast_panels,
                     plot_tumor_panels, plot_microenvironment_panels,
                     plot_ph_panel, plot_ra_panels)
from check_sources import run_checks as check_sources


def main():
    # --- Source integrity check (no sim data needed) ---
    src_errors, src_warnings = check_sources()
    for w in src_warnings:
        print(f"  WARN: {w}")
    if src_errors:
        for e in src_errors:
            print(f"  ERROR: {e}")
        print(f"  SOURCES check FAILED: {len(src_errors)} error(s)")
        sys.exit(1)
    n = len(src_warnings)
    print(f"  SOURCES check passed ({n} warning{'s' if n != 1 else ''})")

    # --- Parse CLI args ---
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", nargs="?", default="output/skibidy/metrics.csv")
    parser.add_argument("--config", help="Exact saved configuration for this run")
    parser.add_argument("--report", help="JSON coverage and observable results")
    for name in ("normal", "diabetic", "burn", "pressure", "surgical", "rheumatoid"):
        parser.add_argument("--" + name, action="store_true")
    options = parser.parse_args()
    sim_path = options.metrics
    flags = ["--" + name for name in ("normal", "diabetic", "burn", "pressure", "surgical", "rheumatoid") if getattr(options, name)]
    if len(flags) > 1:
        parser.error("choose only one condition")
    config_path = options.config
    if config_path is None:
        config_path = saved_config_path(sim_path)
    if config_path is None:
        raise ValueError("No saved run configuration. Supply --config to establish condition and enabled mechanisms.")
    config = parse_toml(config_path)

    # Explicit flags assert the saved condition, checked by evaluate_run.
    condition = None
    for f in flags:
        if f == "--diabetic":
            condition = "diabetic"
        elif f == "--burn":
            condition = "burn"
        elif f == "--pressure":
            condition = "pressure"
        elif f == "--surgical":
            condition = "surgical"
        elif f == "--rheumatoid":
            condition = "rheumatoid"
        elif f == "--normal":
            condition = "normal"
    if condition is None:
        condition = detect_condition(config_path)
    print(f"  Condition: {condition}")

    if not os.path.exists(sim_path):
        print(f"Error: {sim_path} not found. Run the simulation first.")
        sys.exit(1)

    if config is not None:
        validate_run_metrics(sim_path, config)
    sim = load_csv(sim_path)
    sim_days = [h / 24.0 for h in sim["time_h"]]
    has_wound, has_fibroblast, has_tumor, has_microenv, has_ph, has_ra = detect_modules(sim, config)

    if not has_wound and not has_tumor and not has_ra:
        print("NOT TESTED: no supported validation target is enabled.")

    # --- Compute once ---
    results, report = evaluate_run(sim, sim_days, config, condition)
    wound_r, fibro_r, tumor_r, micro_r, ph_r, ra_r = [results[k] for k in
        ("wound", "fibroblast", "tumor", "microenv", "ph", "ra")]

    # --- Print once ---
    passed = print_summary(wound=wound_r, fibroblast=fibro_r, tumor=tumor_r,
                           microenv=micro_r, ph=ph_r, ra=ra_r)
    report.update(condition=condition, config=config_path, metrics=os.path.abspath(sim_path),
                  source_warnings=src_warnings)
    passed = report["status"] == "pass"
    report_path = options.report or os.path.join(os.path.dirname(sim_path), "validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, allow_nan=False)
    for name, item in report["coverage"].items():
        if item["status"] == "not_tested":
            print(f"  NOT TESTED: {name}: {item['reason']}")

    if QUICK:
        return passed

    out_dir = plots_dir(sim_path)
    os.makedirs(out_dir, exist_ok=True)

    # --- Per-module PNGs ---
    if wound_r:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        plot_wound_panels(wound_r, sim_days, axes)
        wound_tag = f" [{condition}]" if condition != "normal" else ""
        fig.suptitle(f"Wound Healing Validation{wound_tag}", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(os.path.join(out_dir, "wound_validation.png"), dpi=150)
        plt.close(fig)

    if fibro_r:
        fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
        plot_fibroblast_panels(fibro_r, sim_days, axes)
        fig.suptitle("Fibroblast/Collagen Validation", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(os.path.join(out_dir, "fibroblast_validation.png"), dpi=150)
        plt.close(fig)

    if micro_r:
        mr = 3 if ph_r else 2
        fig, axes = plt.subplots(mr, 2, figsize=(12, 4 * mr))
        plot_microenvironment_panels(micro_r, sim_days, axes[:2])
        if ph_r:
            plot_ph_panel(ph_r, sim_days, axes[2, 0])
            axes[2, 1].set_visible(False)
        fig.suptitle("Microenvironment Validation", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(os.path.join(out_dir, "microenvironment_validation.png"), dpi=150)
        plt.close(fig)

    if tumor_r:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        plot_tumor_panels(tumor_r, sim_days, axes)
        fig.suptitle("Tumor Growth Validation", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.92])
        fig.savefig(os.path.join(out_dir, "tumor_validation.png"), dpi=150)
        plt.close(fig)

    if ra_r:
        has_ext = ra_r.get("has_bone") or ra_r.get("has_tcell") or ra_r.get("has_syn")
        ra_rows = 3 if has_ext else 3
        ra_cols = 2 if has_ext else 1
        if has_ext:
            fig, ax_arr = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
            ra_axes = [ax_arr[0, 0], ax_arr[0, 1], ax_arr[1, 0],
                       ax_arr[1, 1], ax_arr[2, 0], ax_arr[2, 1]]
        else:
            fig, ra_axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
        plot_ra_panels(ra_r, sim_days, ra_axes)
        fig.suptitle("Rheumatoid Arthritis Validation", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(os.path.join(out_dir, "ra_validation.png"), dpi=150)
        plt.close(fig)

    # --- Dashboard PNG (adaptive rows) ---
    nrows = 0
    if has_wound:
        nrows += 2
    if has_fibroblast:
        nrows += 2  # fibroblast now has 3 panels across 2 rows
    if has_microenv:
        nrows += 2
    if has_ph:
        nrows += 1
    if has_tumor:
        nrows += 1
    if has_ra:
        ra_ext = (ra_r and (ra_r.get("has_bone") or ra_r.get("has_tcell")
                            or ra_r.get("has_syn")))
        nrows += 3 if ra_ext else 2  # 6 panels (3x2) or 3 panels (2 rows)

    if nrows > 0:
        fig, axes = plt.subplots(nrows, 2, figsize=(12, 4 * nrows))
        if nrows == 1:
            axes = axes.reshape(1, 2)

        row = 0
        if wound_r:
            plot_wound_panels(wound_r, sim_days, axes[row:row+2])
            row += 2
        if fibro_r:
            # 3 panels: spread across row[0..1] and row[2] (left)
            fibro_axes = [axes[row, 0], axes[row, 1], axes[row+1, 0]]
            plot_fibroblast_panels(fibro_r, sim_days, fibro_axes)
            axes[row+1, 1].set_visible(False)
            row += 2
        if micro_r:
            plot_microenvironment_panels(micro_r, sim_days, axes[row:row+2])
            row += 2
        if ph_r:
            plot_ph_panel(ph_r, sim_days, axes[row, 0])
            axes[row, 1].set_visible(False)
            row += 1
        if tumor_r:
            plot_tumor_panels(tumor_r, sim_days, axes[row])
            row += 1
        if ra_r:
            if ra_ext:
                ra_axes = [axes[row, 0], axes[row, 1], axes[row+1, 0],
                           axes[row+1, 1], axes[row+2, 0], axes[row+2, 1]]
                plot_ra_panels(ra_r, sim_days, ra_axes)
                row += 3
            else:
                ra_axes = [axes[row, 0], axes[row, 1], axes[row+1, 0]]
                plot_ra_panels(ra_r, sim_days, ra_axes)
                axes[row+1, 1].set_visible(False)
                row += 2

        max_day = max(sim_days) if sim_days else 30
        if has_tumor:
            for c in range(2):
                axes[-1, c].set_xlim(0, max(30, max_day))

        cond_tag = f" [{condition}]" if condition != "normal" else ""
        fig.suptitle(f"skibidy Validation Dashboard{cond_tag}", fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        path = os.path.join(out_dir, "validation_dashboard.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  Saved {path}")

    return passed


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
