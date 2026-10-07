#!/usr/bin/env python3
"""Fetch primary records to ignored output and record reproducible provenance.

Numeric constraints are curated in studies/diabetic-wound/data/treatment_constraints.csv;
this command never changes model parameters or treats a paper's protocol as an effect size.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
SOURCES = {
    "tang2013.xml": (BASE + "PMC3554373/fullTextXML", "10.2337/db12-0684", "xml"),
    "senolytic_xml.xml": (BASE + "PMC6796530/fullTextXML", "10.1016/j.ebiom.2019.08.069", "xml"),
    "hbo_xml.xml": (BASE + "PMC2858204/fullTextXML", "10.2337/dc09-1754", "xml"),
    "npwt.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A16291063", "10.1016/s0140-6736(05)67695-7", "json"),
    "pdgf.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A10564562", "10.1046/j.1524-475x.1999.00335.x", "json"),
    "lobmann2002.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A12136400", "10.1007/s00125-002-0868-8", "json"),
    "npwt_basic.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A9188970", "10.1097/00000637-199706000-00001", "json"),
    "msc_primary.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A28842435", "10.1152/physiolgenomics.00090.2016", "json"),
    "winter_original.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A14007593", "10.1038/193293a0", "json"),
    "anti.json": (BASE + "search?format=json&resultType=core&query=EXT_ID%3A23493576", "10.2337/db12-1450", "json"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "output/treatment-evidence")
    parser.add_argument("--cached", action="store_true", help="Inspect existing downloads without network requests")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    records = []
    for name, (url, doi, kind) in SOURCES.items():
        path = args.cache / name
        record = {"file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                  "url": url, "doi": doi, "format": kind,
                  "inspected_utc": datetime.now(timezone.utc).isoformat(), "cached": args.cached}
        try:
            if not args.cached:
                with urllib.request.urlopen(url, timeout=45) as response:
                    content = response.read()
                    record.update(http_status=response.status, content_type=response.headers.get("Content-Type"))
                path.write_bytes(content)
            content = path.read_bytes()
            if kind == "xml":
                document = ET.fromstring(content)
                if document.tag != "article":
                    raise ValueError("response is not a research article")
                identifiers = ["".join(node.itertext()) for node in document.findall(".//article-id")]
                if doi.lower() not in [value.lower() for value in identifiers]:
                    raise ValueError("article DOI differs from requested source")
                record["supplementary_material_nodes"] = len(document.findall(".//supplementary-material"))
            else:
                document = json.loads(content)
                hits = document["resultList"]["result"]
                selected = [hit for hit in hits if hit.get("doi", "").lower() == doi.lower()]
                if not selected:
                    raise ValueError("no primary record matches requested DOI")
                record["pmid"] = selected[0]["id"]
            record.update(status="verified", bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        except Exception as exc:
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        records.append(record)
    destination = ROOT / "studies/diabetic-wound/data/treatment_provenance.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"sources": records,
        "limits": "Summary extraction only. No individual subject data or model parameter fit. Tang XML contains no supplementary-material nodes; outcome magnitudes are in inaccessible figure assets."}, indent=2) + "\n")
    print(f"{sum(r['status']=='verified' for r in records)}/{len(records)} verified: {destination}")


if __name__ == "__main__":
    main()
