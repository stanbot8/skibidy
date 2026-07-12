#!/usr/bin/env python3
"""Validate reference CSV data quality.

For every modules/*/data/*.csv used by the validation pipeline:
  1. Parses as well-formed CSV (header + numeric body)
  2. All cells finite (no NaN, no inf)
  3. X-axis column (day, week, month, year, age) starts at >= 0 and is
     strictly increasing; CSVs with no recognized x-axis (categorical) skip
     this check
  4. Peak-normalized columns (suffix _normalized) lie in [0, 1.05]
  5. Percentage columns (suffix _pct) lie in [0, 100]
  6. Provenance: header comment block carries a DOI/year, OR the
     corresponding modules/<m>/SOURCES.yaml has entries (warning only)

Exit codes:
  0 = all checks pass
  1 = quality issues found

Usage:
    python literature/check_data_quality.py
    python literature/check_data_quality.py --strict   # treat warnings as errors
    python literature/check_data_quality.py --csv modules/scar/data/foo.csv
"""

import argparse
import glob
import math
import os
import sys

_PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))
_MODULES_DIR = os.path.join(_PROJECT_ROOT, "modules")

# Columns whose values represent peak-normalized fractions (0..~1).
_PEAK_NORMALIZED_SUFFIXES = (
    "_normalized",
)

# Columns whose values represent absolute percentage (0..100).
_PERCENT_SUFFIX = "_pct"

# Columns recognized as the independent axis.
_X_COLUMN_NAMES = ("day", "week", "month", "year", "age", "age_years")

# Categorical-key first-column names (categorical CSVs, not timecourses).
_CATEGORICAL_KEY_COLUMNS = ("tumor_type",)


def _read_csv_with_comments(path):
    """Return (comment_lines, header, rows). Comment lines start with '#'."""
    comments = []
    rows = []
    header = None
    with open(path, newline="") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                comments.append(line.lstrip("#").strip())
                continue
            if header is None:
                header = [c.strip() for c in line.split(",")]
                continue
            rows.append([c.strip() for c in line.split(",")])
    return comments, header, rows


def _categorical_key_idx(header):
    """Return index of a categorical-key column if the first column is one."""
    if header and header[0] in _CATEGORICAL_KEY_COLUMNS:
        return 0
    return None


def _parse_numeric(rows, header, path):
    """Return (rows_as_floats, errors). Skips a categorical key column."""
    errors = []
    out = []
    cat_idx = _categorical_key_idx(header)
    for i, row in enumerate(rows):
        if len(row) != len(header):
            errors.append(
                f"{path}: row {i + 2} has {len(row)} cells, expected {len(header)}")
            continue
        try:
            parsed = [None if j == cat_idx else float(c)
                      for j, c in enumerate(row)]
        except ValueError as e:
            errors.append(f"{path}: row {i + 2} non-numeric: {e}")
            continue
        out.append(parsed)
    return out, errors


def _check_x_axis(header, rows, path):
    errors = []
    x_idx = None
    for name in _X_COLUMN_NAMES:
        if name in header:
            x_idx = header.index(name)
            break
    if x_idx is None:
        # No recognized x-axis column: skip this check.
        return errors
    xs = [r[x_idx] for r in rows]
    if not xs:
        errors.append(f"{path}: empty body")
        return errors
    if xs[0] < 0:
        errors.append(f"{path}: first {header[x_idx]} = {xs[0]} (expected >= 0)")
    for i in range(1, len(xs)):
        if xs[i] <= xs[i - 1]:
            errors.append(
                f"{path}: {header[x_idx]} not strictly increasing at row "
                f"{i + 2}: {xs[i - 1]} -> {xs[i]}")
    return errors


def _check_value_ranges(header, rows, path):
    errors = []
    cat_idx = _categorical_key_idx(header)
    for col_idx, col_name in enumerate(header):
        if col_idx == cat_idx or col_name in _X_COLUMN_NAMES:
            continue
        vals = [r[col_idx] for r in rows]
        for v in vals:
            if math.isnan(v) or math.isinf(v):
                errors.append(f"{path}: column '{col_name}' contains non-finite value")
                break
        if col_name.endswith(_PERCENT_SUFFIX):
            for v in vals:
                if not (-0.01 <= v <= 100.5):
                    errors.append(
                        f"{path}: column '{col_name}' value {v} out of [0, 100]")
                    break
        elif any(col_name.endswith(s) for s in _PEAK_NORMALIZED_SUFFIXES):
            for v in vals:
                if not (-0.01 <= v <= 1.05):
                    errors.append(
                        f"{path}: peak-normalized column '{col_name}' value {v} "
                        f"out of [0, 1.05]")
                    break
    return errors


def _module_for_csv(csv_path):
    try:
        rel = os.path.relpath(csv_path, _MODULES_DIR)
    except ValueError:
        return None
    parts = rel.split(os.sep)
    if len(parts) < 2 or parts[1] != "data" or parts[0].startswith(".."):
        return None
    return parts[0]


def _check_provenance(csv_path, comments, sources_index, warnings):
    module = _module_for_csv(csv_path)
    if module is None:
        return
    has_comment_provenance = any(
        ("doi" in c.lower() or any(y in c for y in ("19", "20")))
        for c in comments
    )
    has_sources_yaml = module in sources_index and sources_index[module]
    if not has_comment_provenance and not has_sources_yaml:
        warnings.append(
            f"{csv_path}: no provenance (no header comment with DOI/year and "
            f"no entries in modules/{module}/SOURCES.yaml)")


def _build_sources_index():
    """Map module name -> list of DOIs found in its SOURCES.yaml."""
    index = {}
    for path in glob.glob(os.path.join(_MODULES_DIR, "*", "SOURCES.yaml")):
        module = os.path.basename(os.path.dirname(path))
        dois = []
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("doi:"):
                    dois.append(stripped[4:].strip())
        index[module] = dois
    return index


def discover_csvs():
    return sorted(glob.glob(os.path.join(_MODULES_DIR, "*", "data", "*.csv")))


def check_csv(path, sources_index, strict):
    errors = []
    warnings = []
    comments, header, rows = _read_csv_with_comments(path)
    if header is None:
        errors.append(f"{path}: missing header row")
        return errors, warnings
    if not rows:
        errors.append(f"{path}: no data rows")
        return errors, warnings
    numeric_rows, parse_errors = _parse_numeric(rows, header, path)
    errors.extend(parse_errors)
    if parse_errors:
        return errors, warnings
    errors.extend(_check_x_axis(header, numeric_rows, path))
    errors.extend(_check_value_ranges(header, numeric_rows, path))
    _check_provenance(path, comments, sources_index, warnings)
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", action="append", default=None,
                        help="Specific CSV(s) to check; default: all")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    args = parser.parse_args()

    csvs = args.csv if args.csv else discover_csvs()
    sources_index = _build_sources_index()

    total_errors = 0
    total_warnings = 0
    for path in csvs:
        errors, warnings = check_csv(path, sources_index, args.strict)
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        for w in warnings:
            print(f"WARN:  {w}")
        total_errors += len(errors)
        total_warnings += len(warnings)

    print(f"\nChecked {len(csvs)} CSV(s): "
          f"{total_errors} error(s), {total_warnings} warning(s)")
    if total_errors or (args.strict and total_warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
