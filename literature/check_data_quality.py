#!/usr/bin/env python3
"""Validate reference CSV data quality.

For reference curves, extracted cell records, membrane observations, measured
GEO expression tables and study treatment constraints:
  1. Parses as well-formed CSV (quoted fields supported)
  2. Required numeric measurements are finite (no NaN, no inf); categorical
     identities and explicitly missing observations follow their source schema
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
import csv
import glob
from itertools import chain
import math
import os
import re
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

# These schemas are evidence tables, not globally ordered numeric curves.
_SCHEMAS = {
    "study": "study sheet clone generation source_generation duration_cell "
             "duration_h division_type positive_recorded_interval complete_cycle "
             "first_generation fit_eligible",
    "component": "component first_sample_day last_sample_day observation "
                 "measurement n_reported",
    "sample": "gene probe sample subject tissue day rma_log2_expression",
    "mean_log2": "gene probe tissue day n mean_log2 sample_sd_log2 "
                 "log2_difference_from_group_baseline",
    "source_id": "source_id treatment population observable time measurement "
                 "value unit n model_connection calibration_status",
}


def _read_csv_with_comments(path):
    """Return (comment_lines, header, rows). Comment lines start with '#'."""
    comments = []
    rows = []
    header = None
    with open(path, newline="", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                comments.append(line.lstrip("#").strip())
                continue
            # One reader record may consume multiple lines from f. Comments are
            # recognized only between records, never inside a quoted field.
            record = next(csv.reader(chain([raw], f), strict=True))
            record = [c.strip() for c in record]
            if header is None:
                header = record
            else:
                rows.append(record)
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
        if col_idx == cat_idx:
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


def _check_evidence_rows(schema, header, rows, path):
    """Validate source identities, finite measurements and extraction flags.

    Blank durations are unobserved intervals, not zero cycles. Missing sample
    counts and treatment effect sizes remain explicitly missing. Daughter-fate
    and generation labels follow analyze_cycles.py's extraction contract.
    """
    errors = []
    seen = set()
    sample_metadata = {}
    expected = _SCHEMAS[schema].split()
    if set(header) != set(expected):
        return [f"{path}: {schema} schema requires columns {', '.join(expected)}"]

    for row_number, cells in enumerate(rows, 2):
        label = f"{path}: row {row_number}"
        if len(cells) != len(header):
            errors.append(f"{label} has {len(cells)} cells, expected {len(header)}")
            continue
        row = dict(zip(header, cells))

        def fail(message):
            errors.append(f"{label}: {message}")

        def required(*columns):
            for col in columns:
                if not row[col]:
                    fail(f"'{col}' must contain a categorical identity or observation")

        def number(col, minimum=None, integer=False, optional=False):
            value = row[col]
            if optional and value == "":
                return None
            try:
                value = float(value)
            except ValueError:
                fail(f"'{col}' must be numeric" + (" or explicitly blank" if optional else ""))
                return None
            if not math.isfinite(value):
                fail(f"'{col}' contains a non-finite value")
                return None
            if minimum is not None and value < minimum:
                fail(f"'{col}' must be >= {minimum}")
            if integer and not value.is_integer():
                fail(f"'{col}' must be an integer")
            return value

        def unique(*columns):
            key = tuple(row[col] for col in columns)
            if key in seen:
                fail(f"duplicate source identity in {', '.join(columns)}: {key}")
            seen.add(key)

        if schema == "study":
            required("study", "sheet", "clone", "generation", "source_generation", "duration_cell")
            if row["study"] not in {"Xiao2024", "Roshan2016"}:
                fail("unrecognized cell-cycle study")
            if not re.fullmatch(r"(?:Clone|Colony) [1-9]\d*", row["clone"]):
                fail("invalid source clone identity")
            if not re.fullmatch(r"[A-Z]+[1-9]\d*", row["duration_cell"]):
                fail("invalid source worksheet cell")
            generation = row["generation"]
            if not re.fullmatch(r"(?:[1-9]\d*|D[1-9]\d*|Outer[1-9]\d*)", generation):
                fail("invalid generation label")
            if row["source_generation"].removeprefix("G") != generation:
                fail("source_generation disagrees with normalized generation")
            duration = number("duration_h", minimum=0, optional=True)
            fate = row["division_type"]
            if fate not in {"", "P", "D", "U", "PP", "PD", "DP", "DD", "PU", "UP",
                            "DU", "UD", "UU", "Bd", "BD", "DB", "Div"}:
                fail("unrecognized source daughter-fate label")
            positive = duration is not None and duration > 0
            flags = {
                "positive_recorded_interval": positive,
                "complete_cycle": positive and bool(re.fullmatch(r"[PDU]{2}", fate)),
                "first_generation": generation == "1",
                "fit_eligible": generation.isdigit() and int(generation) > 1
                                and row["sheet"] != "NFSK expanding (Fig2a)",
            }
            for col, expected_flag in flags.items():
                if row[col] not in {"True", "False"}:
                    fail(f"'{col}' must be True or False")
                elif (row[col] == "True") != expected_flag:
                    fail(f"'{col}' disagrees with recorded interval, fate or generation")
            unique("study", "sheet", "duration_cell")
        elif schema == "component":
            required("component", "observation", "measurement")
            first = number("first_sample_day", minimum=0)
            last = number("last_sample_day", minimum=0)
            if first is not None and last is not None and last < first:
                fail("last_sample_day precedes first_sample_day")
            number("n_reported", minimum=1, integer=True, optional=True)
        elif schema in {"sample", "mean_log2"}:
            required("gene", "probe", "tissue")
            if row["tissue"] not in {"skin", "palate"}:
                fail("unrecognized GSE209609 tissue")
            number("day", minimum=0)
            if schema == "sample":
                required("sample", "subject")
                if not re.fullmatch(r"GSM[1-9]\d*", row["sample"]):
                    fail("invalid GEO sample accession")
                number("rma_log2_expression")
                unique("gene", "probe", "sample")
                metadata = tuple(row[c] for c in ("subject", "tissue", "day"))
                previous = sample_metadata.setdefault(row["sample"], metadata)
                if previous != metadata:
                    fail("GEO sample has inconsistent subject, tissue or day")
            else:
                number("n", minimum=1, integer=True)
                number("mean_log2")
                number("sample_sd_log2", minimum=0)
                number("log2_difference_from_group_baseline")
                unique("gene", "probe", "tissue", "day")
        elif schema == "source_id":
            required(*(col for col in expected if col not in {"value", "n"}))
            value = number("value", minimum=0, optional=True)
            if value is None and row["unit"] not in {
                    "direction", "direction and P<0.05", "not extracted", "assumed"}:
                fail("missing effect size requires an explicit qualitative/missing unit")
            # Relative increases can exceed 100%; healed proportions and marker
            # reductions cannot. Preserve the source's measurement distinction.
            relative_increase = "increase" in row["measurement"].lower()
            if (value is not None and row["unit"] == "percent" and value > 100
                    and not relative_increase):
                fail("percent value out of [0, 100]")
            # Source counts include ranges, healed/total counts and named groups.
            count = row["n"]
            if count not in {"", "not extracted"}:
                match = re.fullmatch(r"([1-9]\d*)(?:([-\/])([1-9]\d*)| [A-Za-z].*)?", count)
                if not match:
                    fail("invalid reported sample count")
                elif match[2] and int(match[1]) > int(match[3]):
                    fail("reported sample count range/fraction is reversed")
                if re.search(r"(?:^|;)\s*0(?:\s|$)", count):
                    fail("reported group sample counts must be positive")
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
    curves = glob.glob(os.path.join(_MODULES_DIR, "*", "data", "*.csv"))
    measured = glob.glob(os.path.join(_MODULES_DIR, "*", "data", "published", "**", "*.csv"),
                         recursive=True)
    treatments = glob.glob(os.path.join(_PROJECT_ROOT, "studies", "*", "data",
                                       "treatment_constraints.csv"))
    return sorted(set(curves + measured + treatments))


def check_csv(path, sources_index, strict):
    errors = []
    warnings = []
    try:
        comments, header, rows = _read_csv_with_comments(path)
    except (csv.Error, UnicodeError, OSError) as e:
        return [f"{path}: cannot parse CSV: {e}"], warnings
    if header is None:
        errors.append(f"{path}: missing header row")
        return errors, warnings
    if not rows:
        errors.append(f"{path}: no data rows")
        return errors, warnings
    if any(not col for col in header) or len(header) != len(set(header)):
        return [f"{path}: header columns must be nonempty and unique"], warnings
    schema = next((key for key in _SCHEMAS if key in header), None)
    if schema is not None:
        errors.extend(_check_evidence_rows(schema, header, rows, path))
        _check_provenance(path, comments, sources_index, warnings)
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
