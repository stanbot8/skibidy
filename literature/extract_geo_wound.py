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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".git" / "research")
    args = parser.parse_args()
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
    records, groups = [], {}
    for probe, values in expression.items():
        assert len(values) == n and all(math.isfinite(v) for v in values)
        for i, value in enumerate(values):
            tissue, day = metadata["tissue"][i], days[metadata["time"][i]]
            records.append(dict(gene=mapping[probe], probe=probe, sample=metadata["!Sample_geo_accession"][i], subject=metadata["subject"][i], tissue=tissue, day=day, rma_log2_expression=value))
            groups.setdefault((mapping[probe], probe, tissue, day), []).append(value)
    dest = ROOT / "modules" / "wound" / "data" / "published" / "GSE209609"
    dest.mkdir(parents=True, exist_ok=True)
    def write(name, rows):
        with (dest / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write("sample_expression.csv", records)
    summaries = []
    for (gene, probe, tissue, day), values in sorted(groups.items()):
        baseline = statistics.mean(groups[(gene, probe, tissue, 0)])
        mean = statistics.mean(values)
        summaries.append(dict(gene=gene, probe=probe, tissue=tissue, day=day, n=len(values), mean_log2=mean, sample_sd_log2=statistics.stdev(values) if len(values)>1 else 0, log2_difference_from_group_baseline=mean-baseline))
    write("timecourse_summary.csv", summaries)
    provenance = dict(accession="GSE209609", publication="https://pubmed.ncbi.nlm.nih.gov/36571451/", retrieved="2026-10-07", inputs=receipts, platform="GPL29499 / BrainArray HGU133Plus2_Hs_ENSG_V22", processing=metadata["!Sample_data_processing"][0], sample_count=n, subjects=18, genes_found=sorted(set(mapping.values())), genes_missing=sorted(GENES-set(mapping.values())), extraction="Exact deposited RMA log2 values for all mapped selected genes and all samples. Tissue/time group arithmetic mean and sample SD; difference of group means from same-tissue day 0. No probe averaging, interpolation, imputation, hypothesis tests or model fit.", limitations="Bulk RNA, healthy adults age 18-35, incomplete repeated-subject sampling. Group differences are not paired patient estimates. RNA changes do not identify protein concentration, fibroblast count, collagen mass, cell-cycle duration or membrane integrity. Does not calibrate any current parameter.")
    provenance["extracted_utc"] = datetime.now(timezone.utc).isoformat()
    (dest / "provenance.json").write_text(json.dumps(provenance, indent=2)+"\n", encoding="utf-8")
    print(f"Saved {len(records)} measured values, {len(summaries)} groups, {len(provenance['genes_found'])} genes to {dest}")


if __name__ == "__main__":
    main()
