"""Plot deposited human wound RNA group summaries without fitting the model."""
import argparse
import csv
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / "modules/wound/data/published/GSE209609"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from literature.check_data_quality import check_csv, _build_sources_index


def plot_groups():
    errors, _ = check_csv(str(DATA / "timecourse_summary.csv"), _build_sources_index(), False)
    if errors:
        raise ValueError("\n".join(errors))
    with (DATA / "timecourse_summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    genes = ("IL1B", "TGFB1", "MMP1", "MKI67", "COL1A1", "COL4A1")
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True)
    for gene, ax in zip(genes, axes.flat):
        for tissue, color in (("skin", "#2678b8"), ("palate", "#c86024")):
            selected = sorted((r for r in rows if r["gene"] == gene and r["tissue"] == tissue), key=lambda r: float(r["day"]))
            assert len(selected) == 5 and len({r["probe"] for r in selected}) == 1
            ax.errorbar([float(r["day"]) for r in selected],
                        [float(r["mean_log2"]) for r in selected],
                        yerr=[float(r["sample_sd_log2"]) for r in selected],
                        marker="o", capsize=3, color=color, label=tissue)
        ax.set_title(gene)
        ax.set_ylabel("RMA log2 RNA expression")
        ax.set_xlabel("Day after wounding")
        ax.grid(alpha=.15)
    axes[0, 0].legend()
    fig.suptitle("GSE209609: human skin and palate wound RNA (healthy adults)")
    fig.text(.5, .04, "Days 0, 0.25, 1, 3, 7: skin n = 13, 7, 10, 9, 6; palate n = 17, 6, 12, 10, 6. Arithmetic group mean ± sample SD.", ha="center", fontsize=9)
    fig.text(.5, .015, "Incomplete repeated-subject sampling; no paired test or model fit. RNA is not protein, cell count or collagen mass.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .065, 1, .96))
    for extension in ("png", "pdf"):
        fig.savefig(DATA / f"measured_rna_timecourses.{extension}", dpi=180)
    plt.close(fig)


def plot_pairs():
    sources = _build_sources_index()
    for name in ("paired_changes.csv", "paired_timecourse_summary.csv"):
        errors, _ = check_csv(str(DATA / name), sources, False)
        if errors:
            raise ValueError("\n".join(errors))
    with (DATA / "paired_changes.csv").open(newline="", encoding="utf-8") as stream:
        pairs = list(csv.DictReader(stream))
    with (DATA / "paired_timecourse_summary.csv").open(newline="", encoding="utf-8") as stream:
        summaries = list(csv.DictReader(stream))
    genes = ("IL1B", "TGFB1", "MMP1", "MKI67", "COL1A1", "IL6")
    days = (.25, 1, 3, 7)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True)
    for gene, ax in zip(genes, axes.flat):
        selected = [r for r in pairs if r["gene"] == gene and r["tissue"] == "skin"]
        groups = sorted((r for r in summaries if r["gene"] == gene and r["tissue"] == "skin"),
                        key=lambda r: float(r["day"]))
        if len(groups) != 4 or len({r["probe"] for r in groups}) != 1:
            raise ValueError("Paired plot needs one probe and four recorded skin times")
        for index, (day, group) in enumerate(zip(days, groups)):
            if float(group["day"]) != day:
                raise ValueError("Unexpected paired sampling time")
            values = [float(r["delta_log2"]) for r in selected if float(r["day"]) == day]
            if len(values) != int(group["n_pairs"]):
                raise ValueError("Paired plot subject count disagrees with summary")
            # Each dot is one subject at this time. No lines interpolate missing visits.
            offsets = [.24 * (i / max(1, len(values) - 1) - .5) for i in range(len(values))]
            ax.scatter([index + offset for offset in offsets], values, color="#2678b8",
                       alpha=.7, s=25, label="Individual paired change" if index == 0 else None)
            if values:
                sd = float(group["sample_sd_delta_log2"]) if len(values) > 1 else None
                ax.errorbar(index, float(group["mean_delta_log2"]), yerr=sd,
                            marker="D", color="black", capsize=4,
                            label="Paired mean and sample SD" if index == 0 else None)
            ax.text(index, 1.015, f"n={len(values)}", transform=ax.get_xaxis_transform(),
                    ha="center", fontsize=9)
        ax.axhline(0, color="gray", linestyle=":", linewidth=1)
        ax.set_title(gene, pad=24)
        ax.set_ylabel("Paired RNA change (log2)")
        ax.set_xticks(range(4), ["6 h", "Day 1", "Day 3", "Day 7"])
        ax.grid(alpha=.15)
    fig.suptitle("GSE209609: matched-subject skin wound RNA changes")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .058), ncol=2, fontsize=9)
    fig.text(.5, .04, "Separate wounds at each biopsy. Paired subject subsets change across times. SD is observed spread, not a confidence interval.",
             ha="center", fontsize=9)
    fig.text(.5, .016, "No imputation, temporal interpolation, significance test or model fit. RNA does not measure protein, cell count or collagen mass.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .12, 1, .95))
    for extension in ("png", "pdf"):
        fig.savefig(DATA / f"paired_rna_changes.{extension}", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-only", action="store_true", help="Keep existing group plots and render paired changes")
    args = parser.parse_args()
    if not args.paired_only:
        plot_groups()
    plot_pairs()


if __name__ == "__main__":
    main()
