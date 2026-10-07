"""Plot deposited human wound RNA group summaries without fitting the model."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / "modules/wound/data/published/GSE209609"


def main():
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


if __name__ == "__main__":
    main()
