#!/usr/bin/env python3
"""Standalone single-module validation.

Usage:
    python3 literature/validators/compare.py wound [path/to/metrics.csv] [--diabetic|--normal|...]
    python3 literature/validators/compare.py fibroblast [path/to/metrics.csv]
    python3 literature/validators/compare.py microenvironment [path/to/metrics.csv]
    python3 literature/validators/compare.py tumor [path/to/metrics.csv]
    python3 literature/validators/compare.py immune [path/to/metrics.csv] [--diabetic|--normal]
    python3 literature/validators/compare.py ra [path/to/metrics.csv]
"""

import os
import sys
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from batch.lib import parse_toml, validate_run_metrics
from literature.lib import (load_csv, plots_dir, condition_from_config, surface_fraction,
                 evaluate_run, saved_config_path,
                 plot_wound_panels, plot_fibroblast_panels, plot_tumor_panels,
                 plot_microenvironment_panels, plot_ph_panel, plot_ra_panels,
                 SIM_KW, REF_KW)


def _save(fig, out_dir, filename):
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, filename), dpi=150)
    plt.close(fig)
    print(f"  Saved {out_dir}/{filename}")


def run_wound(results, sim_days, condition, out_dir):
    r = results["wound"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    plot_wound_panels(r, sim_days, axes)
    fig.suptitle("Wound Healing Validation", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, out_dir, "wound_validation.png")


def run_fibroblast(results, sim_days, _condition, out_dir):
    r = results["fibroblast"]
    fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    plot_fibroblast_panels(r, sim_days, axes)
    fig.suptitle("Fibroblast/Collagen Validation", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, out_dir, "fibroblast_validation.png")


def run_microenvironment(results, sim_days, _condition, out_dir):
    r, ph_r = results["microenv"], results["ph"]
    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    if r is not None:
        plot_microenvironment_panels(r, sim_days, axes[:2])
    else:
        for ax in axes[:2].flat:
            ax.set_visible(False)
    if ph_r:
        plot_ph_panel(ph_r, sim_days, axes[2, 0])
    else:
        axes[2, 0].set_visible(False)
    axes[2, 1].set_visible(False)
    fig.suptitle("Microenvironment Validation", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, out_dir, "microenvironment_validation.png")


def run_tumor(results, sim_days, _condition, out_dir):
    r = results["tumor"]
    print(r["interpretation"])
    if r["occupied_voxels"]:
        print(f"  Final occupied handoff voxels: {r['occupied_voxels'][-1]:.0f}")
    n_init = r["n_init"]
    n_final = r["obs_final"]
    print(f"\n  Illustrative spherical geometry (active-agent census):")
    print(f"    Initial cells:              {n_init:.0f}  (surface fraction {surface_fraction(n_init):.0%})")
    print(f"    Final cells:                {n_final:.0f}  (surface fraction {surface_fraction(n_final):.0%})")
    print(f"    Established BCC (~10^5):    surface fraction {surface_fraction(1e5):.0%}")
    print(f"    Reference Ki-67 ({r['bcc_ki67_pct']:.1f}%) applies at established-tumor scale.")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    plot_tumor_panels(r, sim_days, axes)
    fig.suptitle("Tumor Growth Validation", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    _save(fig, out_dir, "tumor_validation.png")


def run_immune(results, sim_days, condition, out_dir):
    r = results["wound"]
    sim_days = r["simulation_days"]
    print(f"Immune cell kinetics validation ({len(sim_days)} sim points vs literature)")
    print(f"  Neutrophils:  RMSE = {r['neut_rmse'] * 100:.2f} %  (normalization scale = {r['neut_peak']:.0f})")
    print(f"  Macrophages:  RMSE = {r['mac_rmse'] * 100:.2f} %  (normalization scale = {r['mac_peak']:.0f})")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax1.plot(sim_days, r["sim_neut"], **SIM_KW)
    ax1.plot(r["ref_immune"]["day"], r["ref_immune"]["neutrophils_normalized"], **REF_KW)
    ax1.set_ylabel("Neutrophils (normalized)")
    ax1.set_title("Immune Cell Kinetics: Simulation vs Modeling Target")
    ax1.set_ylim(-0.05, 1.15)
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    ax1.text(0.98, 0.85, f"RMSE = {r['neut_rmse'] * 100:.1f}%",
             transform=ax1.transAxes, ha="right", va="top", fontsize=9, color="gray")
    ax2.plot(sim_days, r["sim_mac"], **SIM_KW)
    ax2.plot(r["ref_immune"]["day"], r["ref_immune"]["macrophages_normalized"], **REF_KW)
    ax2.set_xlabel("Days since wound")
    ax2.set_ylabel("Macrophages (normalized)")
    ax2.set_xlim(0, 30)
    ax2.set_ylim(-0.05, 1.15)
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)
    ax2.text(0.98, 0.85, f"RMSE = {r['mac_rmse'] * 100:.1f}%",
             transform=ax2.transAxes, ha="right", va="top", fontsize=9, color="gray")
    fig.tight_layout()
    _save(fig, out_dir, "immune_validation.png")


def run_ra(results, sim_days, _condition, out_dir):
    r = results["ra"]
    print(f"RA validation ({len(sim_days)} sim points vs literature)")
    print(f"  TNF-alpha:  RMSE = {r['tnf_rmse'] * 100:.2f} %  (normalization scale = {r['tnf_peak']:.4f})")
    print(f"    Flare 0-7d:   RMSE = {r['tnf_flare_rmse'] * 100:.2f} %")
    print(f"    Chronic 7-30d: RMSE = {r['tnf_chronic_rmse'] * 100:.2f} %")
    print(f"  IL-6:       RMSE = {r['il6_rmse'] * 100:.2f} %  (normalization scale = {r['il6_peak']:.4f})")
    print(f"  Cartilage:  RMSE = {r['cart_rmse'] * 100:.2f} %")
    if r.get("has_bone"):
        print(f"  Bone:       RMSE = {r['bone_rmse'] * 100:.2f} %")
    if r.get("has_tcell"):
        print(f"  T cells:    RMSE = {r['tcell_rmse'] * 100:.2f} %  (normalization scale = {r['tcell_peak']:.4f})")
    if r.get("has_syn"):
        print(f"  Pannus:     RMSE = {r['syn_rmse'] * 100:.2f} %  (normalization scale = {r['syn_peak']:.4f})")
    has_ext = r.get("has_bone") or r.get("has_tcell") or r.get("has_syn")
    if has_ext:
        fig, ax_arr = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
        axes = [ax_arr[0, 0], ax_arr[0, 1], ax_arr[1, 0],
                ax_arr[1, 1], ax_arr[2, 0], ax_arr[2, 1]]
    else:
        fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    plot_ra_panels(r, sim_days, axes)
    fig.suptitle("Rheumatoid Arthritis Validation", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, out_dir, "ra_validation.png")


MODULES = {
    "wound": run_wound,
    "fibroblast": run_fibroblast,
    "microenvironment": run_microenvironment,
    "microenv": run_microenvironment,
    "tumor": run_tumor,
    "immune": run_immune,
    "ra": run_ra,
}


OBSERVABLES = {
    "wound": ("Wound closure", "Inflammation", "Neutrophils", "Macrophages"),
    "fibroblast": ("Fibroblasts", "Myofibroblasts", "Collagen"),
    "microenvironment": ("TGF-b", "VEGF", "Fibronectin", "MMP", "pH"),
    "tumor": ("Tumor",), "immune": ("Neutrophils", "Macrophages"),
    "ra": ("TNF-alpha", "IL-6", "Cartilage", "Bone", "T cells", "Synovium"),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=sorted(MODULES))
    parser.add_argument("metrics", nargs="?", default="output/skibidy/metrics.csv")
    parser.add_argument("--config", help="Exact saved configuration for this run")
    parser.add_argument("--report", help="JSON coverage and observable results")
    parser.add_argument("--quick", action="store_true", help="Skip plots")
    conditions = parser.add_mutually_exclusive_group()
    for name in ("normal", "diabetic", "burn", "pressure", "surgical", "rheumatoid"):
        conditions.add_argument("--" + name, dest="condition", action="store_const", const=name)
    options = parser.parse_args(argv)
    config_path = options.config or saved_config_path(options.metrics)
    if config_path is None:
        parser.error("No saved run configuration. Supply --config to establish condition and enabled mechanisms.")
    config = parse_toml(config_path)
    condition = options.condition or condition_from_config(config)
    validate_run_metrics(options.metrics, config)
    sim = load_csv(options.metrics)
    sim_days = [h / 24.0 for h in sim["time_h"]]
    results, report = evaluate_run(sim, sim_days, config, condition)
    module = "microenvironment" if options.module == "microenv" else options.module
    report["coverage"] = {name: report["coverage"][name] for name in OBSERVABLES[module]}
    tested = [item for item in report["coverage"].values() if item["status"] != "not_tested"]
    report.update(tested=len(tested), module=module, config=os.path.abspath(config_path),
                  metrics=os.path.abspath(options.metrics),
                  status="fail" if any(item["status"] == "fail" for item in tested)
                  else "pass" if tested else "not_tested")
    report_path = options.report or os.path.join(os.path.dirname(options.metrics), f"validation_{module}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(f"Condition: {condition}")
    for name, item in report["coverage"].items():
        unit = "pp" if name == "Wound closure" else "%"
        detail = item.get("reason", f"RMSE = {item.get('rmse_pct', 0):.2f}{unit}")
        print(f"  {name}: {item['status'].upper()} ({detail})")
    print(f"{report['status'].upper()}: {len(tested)} tested observables")
    print(report["criterion"])
    print(report["scoring_method"])
    print(report["evidence"])
    groups = {"immune": ("wound",), "microenvironment": ("microenv", "ph")}
    if not options.quick and any(results[key] is not None for key in groups.get(module, (module,))):
        MODULES[options.module](results, sim_days, condition, plots_dir(options.metrics))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
