#!/usr/bin/env python3
"""Unit tests for literature/lib.py validation helpers.

Run:
    python literature/test_lib.py
    python literature/test_lib.py -v

Exit codes:
    0 = all tests pass
    non-zero = test failure
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from lib import (
    interpolate, peak_normalize, end_normalize, compute_rmse,
    phase_rmse, surface_fraction,
    load_csv, _ref_path,
)


class TestInterpolate(unittest.TestCase):

    def test_endpoints(self):
        self.assertEqual(interpolate([0, 10], [0, 100], [0, 10]), [0, 100])

    def test_midpoint(self):
        self.assertEqual(interpolate([0, 10], [0, 100], [5]), [50])

    def test_extrapolation_clamps(self):
        self.assertEqual(interpolate([0, 10], [0, 100], [-5, 15]), [0, 100])

    def test_non_uniform_spacing(self):
        result = interpolate([0, 1, 10], [0, 5, 50], [0.5, 5.5])
        self.assertAlmostEqual(result[0], 2.5)
        self.assertAlmostEqual(result[1], 27.5)


class TestNormalize(unittest.TestCase):

    def test_peak_normalize(self):
        out, peak = peak_normalize([1, 2, 4, 2])
        self.assertEqual(peak, 4)
        self.assertEqual(out, [0.25, 0.5, 1.0, 0.5])

    def test_peak_normalize_zero(self):
        out, peak = peak_normalize([0, 0, 0])
        self.assertEqual(peak, 0)
        self.assertEqual(out, [0, 0, 0])

    def test_end_normalize(self):
        out, final = end_normalize([1, 2, 4])
        self.assertEqual(final, 4)
        self.assertEqual(out, [0.25, 0.5, 1.0])

    def test_end_normalize_empty(self):
        out, final = end_normalize([])
        self.assertEqual(final, 0)
        self.assertEqual(out, [])


class TestRMSE(unittest.TestCase):

    def test_perfect_match(self):
        self.assertEqual(compute_rmse([1, 2, 3], [1, 2, 3]), 0.0)

    def test_constant_offset(self):
        self.assertAlmostEqual(compute_rmse([2, 3, 4], [1, 2, 3]), 1.0)

    def test_known_value(self):
        # errors [0, 0, 3] -> mse = 3, rmse = sqrt(3)
        self.assertAlmostEqual(compute_rmse([1, 2, 6], [1, 2, 3]), math.sqrt(3))

    def test_empty(self):
        self.assertTrue(math.isnan(compute_rmse([], [])))


class TestPhaseRMSE(unittest.TestCase):

    def test_full_range(self):
        self.assertEqual(
            phase_rmse([0, 1, 2, 3], [10, 20, 30, 40], [10, 20, 30, 40], 0, 3),
            0.0)

    def test_phase_subset(self):
        # Day range 1..3 sees errors [1, 0, 1]; rmse = sqrt(2/3)
        rmse = phase_rmse([0, 1, 2, 3], [10, 21, 30, 41], [10, 20, 30, 40], 1, 3)
        self.assertAlmostEqual(rmse, math.sqrt(2.0 / 3.0))

    def test_empty_phase(self):
        self.assertTrue(math.isnan(
            phase_rmse([0, 1, 2], [0, 0, 0], [0, 0, 0], 100, 200)))


class TestSurfaceFraction(unittest.TestCase):

    def test_singleton(self):
        self.assertEqual(surface_fraction(1), 1.0)

    def test_monotonic_decrease(self):
        self.assertGreater(surface_fraction(10), surface_fraction(10000))
        self.assertGreater(surface_fraction(10000), 0)

    def test_bounds(self):
        self.assertLessEqual(surface_fraction(1000), 1.0)
        self.assertGreaterEqual(surface_fraction(1000), 0.0)


class TestNewDatasetSemantics(unittest.TestCase):
    """Biology-level invariants of the four new reference CSVs.

    Format-level invariants (column ranges, monotonic time, etc.) are
    covered by literature/check_data_quality.py.
    """

    def test_senescence_oldest_highest(self):
        data = load_csv(_ref_path("p16_p21_age_cross_section.csv"))
        self.assertEqual(max(data["epi_p16_pct"]), data["epi_p16_pct"][-1])
        self.assertEqual(max(data["derm_p21_pct"]), data["derm_p21_pct"][-1])

    def test_posas_monotonically_improving(self):
        data = load_csv(_ref_path("scar_posas_observer_normal.csv"))
        means = data["posas_observer_mean"]
        for i in range(1, len(means)):
            self.assertLess(means[i], means[i - 1])

    def test_mrss_ci_brackets_mean(self):
        data = load_csv(_ref_path("scleroderma_mrss_trajectory.csv"))
        for lo, mean, hi in zip(data["mrss_ci_lo"], data["mrss_mean"],
                                data["mrss_ci_hi"]):
            self.assertLessEqual(lo, mean)
            self.assertLessEqual(mean, hi)

    def test_mrss_canonical_shape(self):
        # Class 4 dcSSc: peak around year 2, regression by year 4.
        data = load_csv(_ref_path("scleroderma_mrss_trajectory.csv"))
        peak_idx = data["mrss_mean"].index(max(data["mrss_mean"]))
        peak_day = data["day"][peak_idx]
        self.assertGreater(peak_day, 365)
        self.assertLess(peak_day, 1100)
        self.assertLess(data["mrss_mean"][-1], data["mrss_mean"][peak_idx])


if __name__ == "__main__":
    unittest.main()
