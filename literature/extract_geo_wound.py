#!/usr/bin/env python3
"""Extract measured human wound RNA data; never treat it as protein or cell counts.

Usage: python literature/extract_geo_wound.py --cache .git/research
The original GEO processed matrix and its actual custom-CDF platform are cached.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "GSE209609_series_matrix.txt.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE209nnn/GSE209609/matrix/GSE209609_series_matrix.txt.gz",
    "GPL29499_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL29nnn/GPL29499/soft/GPL29499_family.soft.gz",
}
GENES = {"TGFB1", "VEGFA", "FN1", "MMP1", "MMP9", "COL1A1", "COL3A1", "IL1B", "TNF", "IL6", "IDO1", "FMOD", "DCN", "COL4A1", "COL7A1", "LAMA3", "MKI67"}


def _observations(records):
    """Validate and index exact RNA records without averaging duplicates."""
    observations, samples, groups = {}, {}, {}
    for record in records:
        row = dict(record)
        for name in ("gene", "probe", "sample", "subject", "tissue"):
            if not row.get(name):
                raise ValueError(f"Missing {name} in RNA observation")
        row["day"] = float(row["day"])
        row["rma_log2_expression"] = float(row["rma_log2_expression"])
        if (row["tissue"] not in {"skin", "palate"}
                or row["day"] not in {0, .25, 1, 3, 7}
                or not math.isfinite(row["rma_log2_expression"])):
            raise ValueError("Invalid tissue, time or RNA expression")
        key = tuple(row[name] for name in ("gene", "probe", "tissue", "subject", "day"))
        if key in observations:
            raise ValueError("Duplicate subject/tissue/probe/time observation")
        identity = (row["subject"], row["tissue"], row["day"])
        if row["sample"] in samples and samples[row["sample"]] != identity:
            raise ValueError("Inconsistent GEO sample identity")
        samples[row["sample"]] = identity
        observations[key] = row
        groups.setdefault(key[:3] + (row["day"],), []).append(row)
    if not observations:
        raise ValueError("No RNA observations")
    return observations, groups


def group_summaries(records):
    """Reproduce the original group estimates from deposited measurements."""
    _, groups = _observations(records)
    summaries = []
    for (gene, probe, tissue, day), rows in sorted(groups.items()):
        baseline_rows = groups.get((gene, probe, tissue, 0))
        if not baseline_rows:
            raise ValueError("Group baseline unavailable")
        values = [row["rma_log2_expression"] for row in rows]
        baseline = statistics.mean(row["rma_log2_expression"] for row in baseline_rows)
        mean = statistics.mean(values)
        summaries.append(dict(gene=gene, probe=probe, tissue=tissue, day=day,
                              n=len(values), mean_log2=mean,
                              sample_sd_log2=statistics.stdev(values) if len(values) > 1 else "",
                              log2_difference_from_group_baseline=mean - baseline))
    return summaries


def paired_changes(records):
    """Describe same-subject, same-tissue, same-probe baseline changes.

    Biopsies come from separate wounds. Timepoint subsets differ. These are
    descriptive contrasts, not a longitudinal wound trajectory or LIMMA results.
    Never borrow another subject's baseline or average duplicate observations.
    """
    observations, groups = _observations(records)
    pairs, summaries = [], []
    for (gene, probe, tissue, day), rows in sorted(groups.items()):
        if day == 0:
            continue
        baseline_rows = groups.get((gene, probe, tissue, 0), [])
        selected = []
        for row in sorted(rows, key=lambda r: r["subject"]):
            baseline = observations.get((gene, probe, tissue, row["subject"], 0))
            if baseline is None:
                continue
            delta = row["rma_log2_expression"] - baseline["rma_log2_expression"]
            selected.append(dict(gene=gene, probe=probe, tissue=tissue, day=day,
                                 subject=row["subject"], baseline_sample=baseline["sample"],
                                 post_sample=row["sample"], baseline_log2=baseline["rma_log2_expression"],
                                 post_log2=row["rma_log2_expression"], delta_log2=delta))
        pairs.extend(selected)
        deltas = [row["delta_log2"] for row in selected]
        group_delta = (statistics.mean(r["rma_log2_expression"] for r in rows)
                       - statistics.mean(r["rma_log2_expression"] for r in baseline_rows)
                       if baseline_rows else "")
        summaries.append(dict(
            gene=gene, probe=probe, tissue=tissue, day=day,
            n_timepoint=len(rows), n_baseline=len(baseline_rows), n_pairs=len(deltas),
            n_unpaired=len(rows) - len(deltas),
            paired_subjects=";".join(row["subject"] for row in selected),
            mean_delta_log2=statistics.mean(deltas) if deltas else "",
            sample_sd_delta_log2=statistics.stdev(deltas) if len(deltas) > 1 else "",
            min_delta_log2=min(deltas) if deltas else "",
            max_delta_log2=max(deltas) if deltas else "",
            n_increased=sum(v > 0 for v in deltas), n_decreased=sum(v < 0 for v in deltas),
            n_unchanged=sum(v == 0 for v in deltas),
            unpaired_group_delta_log2=group_delta))
    return pairs, summaries


def write_paired_outputs(dest):
    source = dest / "sample_expression.csv"
    with source.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    pairs, summaries = paired_changes(records)
    if not summaries:
        raise ValueError("No post-injury RNA observations")
    pair_fields = ("gene probe tissue day subject baseline_sample post_sample "
                   "baseline_log2 post_log2 delta_log2").split()
    for name, rows, fields in (("paired_changes.csv", pairs, pair_fields),
                               ("paired_timecourse_summary.csv", summaries, list(summaries[0]))):
        with (dest / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    receipt = dict(
        accession="GSE209609", publication="https://pmc.ncbi.nlm.nih.gov/articles/PMC10006330/",
        input_file=source.name, input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        script="literature/extract_geo_wound.py",
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        paired_records=len(pairs), summary_groups=len(summaries),
        method="Exact within-subject, within-tissue, within-probe post minus day-0 RMA log2 expression. Arithmetic paired mean, sample SD, range and sign counts. No imputation, interpolation, fitting or hypothesis tests.",
        limitations="Separate wounds at each biopsy. Changing paired subsets across times. Pair counts are subjects within a timepoint, not independent repeated subjects across time. Sparse late skin samples. SD and range describe observed spread, not a confidence interval or parameter distribution. Not a reproduction of the paper's subject-adjusted LIMMA analysis. RNA is not protein or collagen mass.")
    (dest / "paired_provenance.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(pairs)} paired contrasts and {len(summaries)} descriptive groups")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-only", action="store_true",
                        help="Rebuild paired outputs from saved sample measurements without network access")
    parser.add_argument("--cache", type=Path, default=ROOT / ".git" / "research")
    args = parser.parse_args()
    dest = ROOT / "modules" / "wound" / "data" / "published" / "GSE209609"
    if args.paired_only:
        write_paired_outputs(dest)
        return
    args.cache.mkdir(parents=True, exist_ok=True)
    receipts = []
    for name, url in FILES.items():
        path = args.cache / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=90) as response:
                path.write_bytes(response.read())
        receipts.append(dict(file=name, url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
    # Deposited custom platform uses Ensembl IDs, not the original GPL570 probes.
    def lookup(symbol):
        url = f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{symbol}?content-type=application/json"
        path = args.cache / f"ensembl_{symbol}.json"
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                path.write_bytes(response.read())
        data = json.loads(path.read_bytes())
        if data["display_name"] != symbol or data["species"] != "homo_sapiens":
            raise ValueError(f"Unexpected gene identity: {symbol}")
        return data["id"], symbol, dict(file=path.name, url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with ThreadPoolExecutor(max_workers=4) as pool:
        identities = list(pool.map(lookup, sorted(GENES)))
    ensembl = {identifier: symbol for identifier, symbol, _ in identities}
    receipts.extend(receipt for _, _, receipt in identities)
    mapping = {}
    with gzip.open(args.cache / "GPL29499_family.soft.gz", "rt") as stream:
        for line in stream:
            if line.strip() == "!platform_table_begin":
                break
        rows = csv.DictReader(stream, delimiter="\t")
        for row in rows:
            if row.get("ID", "").startswith("!platform_table_end"):
                break
            identifier = row.get("ORF")
            if identifier in ensembl:
                mapping[row["ID"]] = ensembl[identifier]
    if not mapping:
        raise ValueError("No selected genes mapped; inspect the actual GPL29499 header")
    metadata, expression = {}, {}
    with gzip.open(args.cache / "GSE209609_series_matrix.txt.gz", "rt") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if not row:
                continue
            key = row[0]
            if key == "!Sample_characteristics_ch1":
                label = row[1].split(":", 1)[0]
                metadata[label] = [v.split(":", 1)[1].strip() for v in row[1:]]
            elif key.startswith("!Sample_"):
                metadata[key] = row[1:]
            elif key in mapping:
                expression[key] = [float(v) for v in row[1:]]
    n = len(metadata["!Sample_geo_accession"])
    if set(expression) != set(mapping):
        raise ValueError("Mapped platform probes missing from deposited expression matrix")
    assert n == 96 and set(metadata["!Sample_platform_id"]) == {"GPL29499"}
    assert len(set(metadata["subject"])) == 18
    days = {"0 hours": 0, "6 hours": .25, "Day 1": 1, "Day 3": 3, "Day 7": 7}
    records = []
    for probe, values in expression.items():
        assert len(values) == n and all(math.isfinite(v) for v in values)
        for i, value in enumerate(values):
            tissue, day = metadata["tissue"][i], days[metadata["time"][i]]
            records.append(dict(gene=mapping[probe], probe=probe, sample=metadata["!Sample_geo_accession"][i], subject=metadata["subject"][i], tissue=tissue, day=day, rma_log2_expression=value))
    dest = ROOT / "modules" / "wound" / "data" / "published" / "GSE209609"
    dest.mkdir(parents=True, exist_ok=True)
    def write(name, rows):
        with (dest / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write("sample_expression.csv", records)
    summaries = group_summaries(records)
    write("timecourse_summary.csv", summaries)
    write_paired_outputs(dest)
    provenance = dict(accession="GSE209609", publication="https://pubmed.ncbi.nlm.nih.gov/36571451/", retrieved="2026-10-07", inputs=receipts, platform="GPL29499 / BrainArray HGU133Plus2_Hs_ENSG_V22", processing=metadata["!Sample_data_processing"][0], sample_count=n, subjects=18, genes_found=sorted(set(mapping.values())), genes_missing=sorted(GENES-set(mapping.values())), extraction="Exact deposited RMA log2 values for all mapped selected genes and all samples. Tissue/time group arithmetic mean and sample SD; difference of group means from same-tissue day 0. No probe averaging, interpolation, imputation, hypothesis tests or model fit.", limitations="Bulk RNA, healthy adults age 18-35, incomplete repeated-subject sampling. Group differences are not paired patient estimates. RNA changes do not identify protein concentration, fibroblast count, collagen mass, cell-cycle duration or membrane integrity. Does not calibrate any current parameter.")
    provenance["extracted_utc"] = datetime.now(timezone.utc).isoformat()
    (dest / "provenance.json").write_text(json.dumps(provenance, indent=2)+"\n", encoding="utf-8")
    print(f"Saved {len(records)} measured values, {len(summaries)} groups, {len(provenance['genes_found'])} genes to {dest}")


if __name__ == "__main__":
    main()
