#!/usr/bin/env python3
"""Verify and export a complete cohort's data for a reviewable scientific record."""

import argparse
import csv
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from batch.lib import get_tomllib, validate_run_metrics
from literature.lib import condition_from_config
from scripts.study.experiment_evidence import digest, save_json


def verify_future_prefixes(records, experiment):
    baseline = {r["seed"]: r for r in records if r["arm"] == 0}
    checks = []
    def initial(record):
        data = get_tomllib().loads(Path(record["config"]).read_text())
        data.pop("treatment_schedule", None)
        data.pop("analysis", None)
        data.get("simulation", {}).pop("output_dir", None)
        return data
    for record in records:
        cfg = experiment["configs"][record["arm"]]
        events = cfg.get("schedule", [])
        if not events or min(e["start_day"] for e in events) <= 0:
            continue
        control = baseline[record["seed"]]
        if initial(record) != initial(control):
            continue  # different initial biology is not a delayed-control comparison
        with Path(record["metrics"]).open() as f:
            treatment = list(csv.DictReader(f))
        with Path(control["metrics"]).open() as f:
            untreated = list(csv.DictReader(f))
        start_h = 24 * min(e["start_day"] for e in events)
        prefix = [(a, b) for a, b in zip(treatment, untreated) if float(a["time_h"]) < start_h]
        if any(a != b for a, b in prefix):
            raise ValueError("delayed treatment differs before its start boundary")
        checks.append({"arm": record["arm"], "seed": record["seed"], "start_h": start_h,
                       "identical_prefix_rows": len(prefix),
                       "post_start_metrics_differ": any(a != b for a, b in zip(treatment, untreated)
                                                        if float(a["time_h"]) >= start_h)})
    return checks


def export_cohort(output, destination):
    output, destination = Path(output).resolve(), Path(destination).resolve()
    manifest = json.loads((output / "manifest.json").read_text())
    records = manifest["runs"]
    if manifest["status"] != "complete" or len(records) != manifest["requested_runs"]:
        raise ValueError("cannot export an incomplete cohort")
    checked = []
    for record in records:
        if record["status"] != "complete" or record["exit_code"] != 0:
            raise ValueError("cannot export an unsuccessful replicate")
        config_path, metrics = Path(record["config"]), Path(record["metrics"])
        if digest(config_path) != record["config_sha256"] or digest(metrics) != record["metrics_sha256"]:
            raise ValueError("recorded config or metrics hash differs")
        config = get_tomllib().loads(config_path.read_text())
        count, last = validate_run_metrics(metrics, config)
        if count != record["metrics_rows"] or last != record["last_time_h"]:
            raise ValueError("recorded metrics extent differs")
        metadata = config.get("analysis", {})
        identity = {"condition": condition_from_config(config),
                    "profile": metadata.get("profile") or manifest["experiment"].get("profile", "normal"),
                    "study": metadata.get("study") or manifest["experiment"].get("study", "")}
        checked.append(dict(record, analysis=identity))
    prefixes = verify_future_prefixes(records, manifest["experiment"])
    products = ["comparison.csv", "replicate_outcomes.csv", "paired_deltas.csv", "summary.txt",
                "trajectories.png", "trajectories.svg"]
    if any(not (output / name).is_file() for name in products):
        raise ValueError("complete cohort is missing an analysis product")
    destination.mkdir(parents=True, exist_ok=False)
    for name in products:
        shutil.copy2(output / name, destination / name)
    archive = destination / "replicate_evidence.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for record in checked:
            stem = f"arm{record['arm']:02d}_seed{record['seed']}"
            directory = Path(record["directory"])
            zipped.write(record["config"], stem + "/run-config.toml")
            zipped.write(record["metrics"], stem + "/metrics.csv")
            for name in ["stdout.log", "stderr.log"]:
                zipped.write(directory / name, stem + "/" + name)
        zipped.write(output / "binary/receipt.json", "binary_receipt.json")
    save_json(destination / "receipt.json", {
        "status": "complete", "requested_runs": manifest["requested_runs"],
        "experiment": manifest["experiment"], "binary_receipt": manifest["binary_receipt"],
        "elapsed_seconds": manifest["elapsed_seconds"],
        "shared_prefix_checks": prefixes,
        "original_manifest_sha256": digest(output / "manifest.json"),
        "archive_sha256": digest(archive),
        "runs": [{k: value for k, value in record.items()
                  if k not in {"config", "directory", "metrics"}} for record in checked],
        "limits": "Model sensitivity only; no clinical dose fit. Original run configs are byte-preserved. "
                  "Analysis identity is supplemental metadata when absent from the original config. "
                  "Executable and shared library are retained in the local frozen result directory, not this archive."})
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(export_cohort(args.output, args.destination))


if __name__ == "__main__":
    main()
