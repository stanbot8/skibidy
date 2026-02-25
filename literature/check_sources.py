#!/usr/bin/env python3
"""Validate SOURCES.yaml structural integrity and file references.

Checks:
  1. YAML parses cleanly
  2. Every dataset has required top-level fields (description, sources)
  3. Every source entry has required citation fields (id, authors, year, title)
  4. All file paths (consensus, raw_files) resolve to existing files
  5. Parameter-only datasets have 'notes' annotations (warning)
  6. Inline DOI comments in config files match SOURCES.yaml entries (warning)
  7. --verify-dois: HTTP HEAD check that each DOI resolves via doi.org

Exit codes:
  0 = all checks pass
  1 = structural errors found

Usage:
    python3 literature/check_sources.py
    python3 literature/check_sources.py --verify-dois
    python3 literature/check_sources.py --config bdm.toml --config profiles/diabetic.toml
"""

import glob
import os
import re
import sys
import time

import yaml

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_SOURCES_PATH = os.path.join(_DATA_DIR, "SOURCES.yaml")
_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)

# Required fields for every source citation
_SOURCE_REQUIRED = {"id", "authors", "year", "title"}
# At least one locator should be present
_SOURCE_LOCATOR = {"doi", "pmc", "url"}


def load_sources(path=_SOURCES_PATH):
    """Parse SOURCES.yaml. Returns (dict, errors)."""
    errors = []
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return None, [f"SOURCES.yaml not found: {path}"]
    except yaml.YAMLError as e:
        return None, [f"YAML parse error: {e}"]
    if not isinstance(data, dict):
        return None, ["SOURCES.yaml root must be a mapping"]
    return data, errors


def check_source_entry(tag, src):
    """Validate one citation entry. Returns (errors, warnings)."""
    errors = []
    warnings = []
    if not isinstance(src, dict):
        return [f"{tag}: source entry is not a mapping"], []
    src_id = src.get("id", "?")
    for field in _SOURCE_REQUIRED:
        if field not in src:
            errors.append(f"{tag} ({src_id}): missing '{field}'")
    if not any(src.get(loc) for loc in _SOURCE_LOCATOR):
        warnings.append(f"{tag} ({src_id}): no doi/pmc/url")
    return errors, warnings


def check_dataset(name, entry, data_dir=_DATA_DIR):
    """Validate one dataset entry. Returns (errors, warnings)."""
    errors = []
    warnings = []
    if not isinstance(entry, dict):
        return [f"{name}: entry is not a mapping"], []

    if "description" not in entry:
        errors.append(f"{name}: missing 'description'")

    sources = entry.get("sources")
    if not sources:
        errors.append(f"{name}: missing or empty 'sources' list")
    elif not isinstance(sources, list):
        errors.append(f"{name}: 'sources' must be a list")
    else:
        for i, src in enumerate(sources):
            tag = f"{name}.sources[{i}]"
            src_errs, src_warns = check_source_entry(tag, src)
            errors.extend(src_errs)
            warnings.extend(src_warns)

    # File reference checks (timeseries datasets)
    consensus = entry.get("consensus")
    if consensus:
        full = os.path.join(data_dir, consensus)
        if not os.path.isfile(full):
            errors.append(f"{name}: consensus file not found: {consensus}")

    raw_files = entry.get("raw_files")
    if raw_files:
        if not isinstance(raw_files, list):
            errors.append(f"{name}: 'raw_files' must be a list")
        else:
            for rf in raw_files:
                full = os.path.join(data_dir, rf)
                if not os.path.isfile(full):
                    errors.append(f"{name}: raw file not found: {rf}")

    # Parameter-only dataset: warn if no source has notes
    if consensus is None and raw_files is None:
        if sources and isinstance(sources, list):
            has_notes = any(isinstance(s, dict) and s.get("notes") for s in sources)
            if not has_notes:
                warnings.append(
                    f"{name}: parameter-only dataset with no 'notes' on any source"
                )

    return errors, warnings


def check_config_dois(config_paths, sources_data):
    """Cross-check inline DOI comments in config files against SOURCES.yaml."""
    warnings = []

    # Collect all DOIs from SOURCES.yaml (lowercase for comparison)
    all_dois = set()
    for entry in sources_data.values():
        if not isinstance(entry, dict):
            continue
        for src in entry.get("sources", []):
            if isinstance(src, dict) and src.get("doi"):
                all_dois.add(src["doi"].lower().strip())

    doi_re = re.compile(r"doi:(10\.\S+)")
    for path in config_paths:
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                for match in doi_re.finditer(line):
                    doi = match.group(1).rstrip(");,")
                    if doi.lower() not in all_dois:
                        basename = os.path.basename(path)
                        warnings.append(
                            f"{basename}:{lineno}: doi:{doi} not in SOURCES.yaml"
                        )

    return warnings


def verify_dois(sources_data):
    """HTTP HEAD check that each DOI resolves via doi.org.

    Returns (ok_list, fail_list) where each item is (id, doi, status).
    """
    import urllib.request
    import urllib.error

    dois = []
    for entry in sources_data.values():
        if not isinstance(entry, dict):
            continue
        for src in entry.get("sources", []):
            if isinstance(src, dict) and src.get("doi"):
                dois.append((src.get("id", "?"), src["doi"]))

    # Deduplicate by DOI
    seen = set()
    unique = []
    for src_id, doi in dois:
        key = doi.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append((src_id, doi))

    ok = []
    fail = []
    total = len(unique)
    for i, (src_id, doi) in enumerate(unique):
        url = f"https://doi.org/{doi}"
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "skibidy-source-checker/1.0")
            resp = urllib.request.urlopen(req, timeout=10)
            status = resp.getcode()
            if status < 400:
                ok.append((src_id, doi, status))
                mark = "ok"
            else:
                fail.append((src_id, doi, status))
                mark = f"FAIL ({status})"
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            status = getattr(e, "code", str(e))
            fail.append((src_id, doi, status))
            mark = f"FAIL ({status})"
        except Exception as e:
            fail.append((src_id, doi, str(e)))
            mark = f"FAIL ({e})"
        print(f"  [{i+1}/{total}] {mark}: {src_id} -> {doi}")
        time.sleep(0.3)  # rate limit

    return ok, fail


def run_checks(config_paths=None, do_verify_dois=False):
    """Run all source checks. Returns (errors, warnings)."""
    all_errors = []
    all_warnings = []

    data, parse_errors = load_sources()
    all_errors.extend(parse_errors)
    if data is None:
        return all_errors, all_warnings

    for name, entry in data.items():
        errs, warns = check_dataset(name, entry)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    # Auto-discover config files if none specified
    if config_paths is None:
        config_paths = []
        bdm_toml = os.path.join(_PROJECT_ROOT, "bdm.toml")
        if os.path.isfile(bdm_toml):
            config_paths.append(bdm_toml)
        profiles = glob.glob(os.path.join(_PROJECT_ROOT, "profiles", "*.toml"))
        config_paths.extend(sorted(profiles))

    if config_paths:
        doi_warns = check_config_dois(config_paths, data)
        all_warnings.extend(doi_warns)

    if do_verify_dois:
        print("\n  Verifying DOIs online...")
        ok, fail = verify_dois(data)
        print(f"\n  DOI verification: {len(ok)} ok, {len(fail)} failed")
        for src_id, doi, status in fail:
            all_warnings.append(f"DOI failed ({status}): {src_id} -> {doi}")

    return all_errors, all_warnings


def main():
    config_paths = []
    do_verify = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_paths.append(args[i + 1])
            i += 2
        elif args[i].startswith("--config="):
            config_paths.append(args[i].split("=", 1)[1])
            i += 1
        elif args[i] == "--verify-dois":
            do_verify = True
            i += 1
        else:
            i += 1

    errors, warnings = run_checks(
        config_paths=config_paths if config_paths else None,
        do_verify_dois=do_verify,
    )

    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\n  SOURCES check FAILED: {len(errors)} error(s)")
        sys.exit(1)
    else:
        n = len(warnings)
        print(f"  SOURCES check passed ({n} warning{'s' if n != 1 else ''})")
        sys.exit(0)


if __name__ == "__main__":
    main()
