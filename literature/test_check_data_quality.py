#!/usr/bin/env python3
"""Unit tests for literature/check_data_quality.py.

Exercises the checker against synthetic CSVs in a temp dir to verify it
detects the failure modes it claims to detect, and against the real
modules/*/data/ corpus to verify the corpus passes today.

Run:
    python literature/test_check_data_quality.py
    python literature/test_check_data_quality.py -v
"""

import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from check_data_quality import check_csv, discover_csvs, _build_sources_index, _SCHEMAS


def _write(path, content):
    with open(path, "w") as f:
        f.write(content)


class TestSyntheticCSVs(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = temp.name
        self.sources_index = {"_synthetic": ["10.0/example"]}

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def _evidence(self, schema, records):
        path = self._path("evidence.csv")
        with open(path, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=_SCHEMAS[schema].split())
            writer.writeheader()
            writer.writerows(records)
        return check_csv(path, {}, strict=False)[0]

    def _cell(self, **changes):
        record = dict(study="Xiao2024", sheet="EXP", clone="Colony 1",
                      generation="2", source_generation="2", duration_cell="C6",
                      duration_h="19", division_type="PD", positive_recorded_interval="True",
                      complete_cycle="True", first_generation="False", fit_eligible="True")
        record.update(changes)
        return record

    def test_quoted_categorical_key_and_malformed_quote(self):
        path = self._path("quoted.csv")
        _write(path, 'tumor_type,growth_rate\n"BCC, infiltrative",1\n')
        self.assertEqual(check_csv(path, {}, False)[0], [])
        _write(path, 'tumor_type,growth_rate\n"unclosed,1\n')
        self.assertTrue(any("cannot parse CSV" in e for e in check_csv(path, {}, False)[0]))

    def test_nonfinite_axis_and_duplicate_header(self):
        path = self._path("axis.csv")
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                _write(path, f"day,closure_pct\n{value},1\n")
                self.assertTrue(any("non-finite" in e for e in check_csv(path, {}, False)[0]))
        _write(path, "day,day\n0,1\n")
        self.assertTrue(any("unique" in e for e in check_csv(path, {}, False)[0]))

    def test_cell_records_preserve_missing_censored_and_founder_intervals(self):
        records = [self._cell(),
                   self._cell(duration_cell="D6", duration_h="", division_type="D",
                              positive_recorded_interval="False", complete_cycle="False"),
                   self._cell(duration_cell="E6", generation="1", source_generation="1",
                              first_generation="True", fit_eligible="False"),
                   self._cell(study="Roshan2016", clone="Clone 1", duration_cell="F6",
                              generation="Outer2", source_generation="Outer2", fit_eligible="False")]
        self.assertEqual(self._evidence("study", records), [])

    def test_cell_malformed_measurements_flags_fates_and_identity(self):
        cases = [{"duration_h": "-1"}, {"duration_h": "NaN"}, {"complete_cycle": "False"},
                 {"positive_recorded_interval": "yes"}, {"division_type": "XX"},
                 {"generation": "2.5"}, {"source_generation": "G3"},
                 {"duration_cell": "unknown"}, {"clone": ""},
                 {"duration_h": "", "positive_recorded_interval": "True"}]
        for change in cases:
            with self.subTest(change=change):
                self.assertTrue(self._evidence("study", [self._cell(**change)]))
        self.assertTrue(any("duplicate source identity" in e
                            for e in self._evidence("study", [self._cell(), self._cell()])))

    def test_cell_unresolved_neonatal_sheet_cannot_be_fit_eligible(self):
        row = self._cell(study="Roshan2016", clone="Clone 1",
                         sheet="NFSK expanding (Fig2a)", fit_eligible="False")
        self.assertEqual(self._evidence("study", [row]), [])
        row["fit_eligible"] = "True"
        self.assertTrue(any("fit_eligible" in e for e in self._evidence("study", [row])))

    def test_membrane_quoted_multiline_observation_and_unknown_n(self):
        row = dict(component="collagen_IV", first_sample_day="2", last_sample_day="4",
                   observation="not detected, then detected\n# observation continues",
                   measurement="qualitative immunohistochemistry", n_reported="")
        self.assertEqual(self._evidence("component", [row, dict(row, component="laminin")]), [])
        for change in ({"last_sample_day": "1"}, {"first_sample_day": "-2"},
                       {"last_sample_day": "inf"}, {"n_reported": "0"},
                       {"n_reported": "1.5"}, {"observation": ""}):
            with self.subTest(change=change):
                self.assertTrue(self._evidence("component", [dict(row, **change)]))

    def test_geo_repeated_days_are_per_sample_not_global_axes(self):
        row = dict(gene="DCN", probe="ENSG1_at", sample="GSM6380487", subject="115",
                   tissue="skin", day="1", rma_log2_expression="-0.25")
        other = dict(row, gene="COL1A1", probe="ENSG2_at")
        self.assertEqual(self._evidence("sample", [row, other]), [])
        for change in ({"rma_log2_expression": "nan"}, {"sample": "bad"},
                       {"day": "-1"}, {"tissue": "unknown"}, {"subject": ""}):
            with self.subTest(change=change):
                self.assertTrue(self._evidence("sample", [dict(row, **change)]))
        self.assertTrue(self._evidence("sample", [row, row]))
        self.assertTrue(any("inconsistent" in e for e in
                            self._evidence("sample", [row, dict(other, subject="116")])))

    def test_geo_summary_bounds_and_identical_days_across_tissues(self):
        row = dict(gene="DCN", probe="ENSG1_at", tissue="skin", day="0", n="17",
                   mean_log2="8", sample_sd_log2="0.6", log2_difference_from_group_baseline="-1")
        self.assertEqual(self._evidence("mean_log2", [row, dict(row, tissue="palate")]), [])
        for change in ({"n": "0"}, {"n": "1.5"}, {"sample_sd_log2": "-0.1"},
                       {"mean_log2": "inf"}, {"log2_difference_from_group_baseline": ""}):
            with self.subTest(change=change):
                self.assertTrue(self._evidence("mean_log2", [dict(row, **change)]))
        self.assertTrue(self._evidence("mean_log2", [row, row]))

    def test_treatment_missing_effect_sizes_are_explicit_and_counts_are_validated(self):
        row = dict(source_id="trial2020", treatment="hbo", population="humans, diabetic ulcers",
                   observable="healing", time="1 year", measurement="healed", value="52",
                   unit="percent", n="25/48", model_connection="closure", calibration_status="not fitted")
        qualitative = dict(row, value="", unit="direction", n="not extracted")
        relative = dict(row, measurement="rate increase mean", value="140")
        self.assertEqual(self._evidence("source_id", [row, qualitative, relative]), [])
        for change in ({"value": "nan"}, {"value": "101"}, {"value": ""},
                       {"n": "0"}, {"n": "48/25"}, {"n": "9-5"}, {"source_id": ""}):
            with self.subTest(change=change):
                self.assertTrue(self._evidence("source_id", [dict(row, **change)]))

    def test_evidence_requires_complete_schema_and_correct_row_width(self):
        path = self._path("partial.csv")
        _write(path, "component,first_sample_day\nlaminin,2\n")
        self.assertTrue(any("schema requires" in e for e in check_csv(path, {}, False)[0]))
        _write(path, _SCHEMAS["component"].replace(" ", ",") + "\nlaminin,2,4\n")
        self.assertTrue(any("cells, expected" in e for e in check_csv(path, {}, False)[0]))

    def test_clean_csv_passes(self):
        path = self._path("clean.csv")
        _write(path,
               "# DOI 10.0/example, year 2020\n"
               "day,closure_pct\n"
               "0,0\n"
               "10,50\n"
               "20,100\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertEqual(errors, [])

    def test_missing_header_caught(self):
        path = self._path("noheader.csv")
        _write(path, "")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("missing header" in e for e in errors))

    def test_no_data_rows_caught(self):
        path = self._path("emptybody.csv")
        _write(path, "day,closure_pct\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("no data rows" in e for e in errors))

    def test_non_numeric_caught(self):
        path = self._path("nan.csv")
        _write(path,
               "day,closure_pct\n"
               "0,zero\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("non-numeric" in e for e in errors))

    def test_non_monotonic_day_caught(self):
        path = self._path("nonmonotonic.csv")
        _write(path,
               "# DOI 10.0/example\n"
               "day,closure_pct\n"
               "0,0\n"
               "5,30\n"
               "5,50\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("not strictly increasing" in e for e in errors))

    def test_negative_first_day_caught(self):
        path = self._path("negstart.csv")
        _write(path,
               "# DOI 10.0/example\n"
               "day,closure_pct\n"
               "-1,0\n"
               "5,50\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("first day" in e for e in errors))

    def test_percentage_out_of_range_caught(self):
        path = self._path("badpct.csv")
        _write(path,
               "# DOI 10.0/example\n"
               "day,closure_pct\n"
               "0,0\n"
               "5,150\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(any("out of [0, 100]" in e for e in errors))

    def test_peak_normalized_overshoot_caught(self):
        path = self._path("overshoot.csv")
        _write(path,
               "# DOI 10.0/example\n"
               "day,foo_normalized\n"
               "0,0\n"
               "5,1.5\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertTrue(
            any("peak-normalized" in e and "out of" in e for e in errors))

    def test_peak_normalized_tiny_overshoot_tolerated(self):
        # Float roundoff up to 1.05 should pass.
        path = self._path("tinyovershoot.csv")
        _write(path,
               "# DOI 10.0/example\n"
               "day,foo_normalized\n"
               "0,0\n"
               "5,1.001\n")
        errors, _ = check_csv(path, self.sources_index, strict=False)
        self.assertEqual(errors, [])

    def test_external_path_does_not_crash(self):
        # CSVs outside modules/ skip the provenance check rather than crash
        # (relpath across drives raises ValueError on Windows).
        path = self._path("noprov.csv")
        _write(path,
               "day,closure_pct\n"
               "0,0\n"
               "5,50\n")
        errors, _ = check_csv(path, {}, strict=False)
        self.assertEqual(errors, [])


class TestRealCorpus(unittest.TestCase):
    """Smoke-test that today's CSV corpus passes the checker."""

    def test_all_csvs_pass(self):
        sources_index = _build_sources_index()
        all_errors = []
        for path in discover_csvs():
            errors, _ = check_csv(path, sources_index, strict=False)
            all_errors.extend(errors)
        self.assertEqual(all_errors, [],
                         msg="Existing CSV corpus failed quality check:\n"
                             + "\n".join(all_errors))

    def test_discovery_includes_measured_geo_and_treatment_constraints(self):
        names = {os.path.basename(path) for path in discover_csvs()}
        self.assertTrue({"sample_expression.csv", "timecourse_summary.csv",
                         "treatment_constraints.csv", "human_complete_cycle_records.csv",
                         "germain1995_timing.csv"}.issubset(names))


if __name__ == "__main__":
    unittest.main()
