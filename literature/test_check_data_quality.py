#!/usr/bin/env python3
"""Unit tests for literature/check_data_quality.py.

Exercises the checker against synthetic CSVs in a temp dir to verify it
detects the failure modes it claims to detect, and against the real
modules/*/data/ corpus to verify the corpus passes today.

Run:
    python literature/test_check_data_quality.py
    python literature/test_check_data_quality.py -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from check_data_quality import check_csv, discover_csvs, _build_sources_index


def _write(path, content):
    with open(path, "w") as f:
        f.write(content)


class TestSyntheticCSVs(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sources_index = {"_synthetic": ["10.0/example"]}

    def _path(self, name):
        return os.path.join(self.tmp, name)

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


if __name__ == "__main__":
    unittest.main()
