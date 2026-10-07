"""Validation must distinguish absence, failed outputs and supported comparisons."""
import unittest
import math
from unittest.mock import patch
from literature.lib import condition_from_config, detect_condition, evaluate_run, interpolate, compute_rmse
from literature.lib import detect_modules, validation_report, validate_microenvironment, validate_wound
from literature.lib import wound_comparison_days, plot_wound_panels


class ValidationCoverageTest(unittest.TestCase):
    def test_delayed_wound_uses_injury_time_and_excludes_preinjury_peak(self):
        sim = {"wound_closure_pct": [0, 45, 80], "mean_infl_wound": [1, .6, .1],
               "n_neutrophils": [1, .5, 0], "n_macrophages": [0, 1, .5]}
        config = {"skin": {"wound": {"enabled": True}}}
        baseline, before = evaluate_run(sim, [0, 7, 14], config, "normal")
        config["skin"]["wound"]["trigger_h"] = 48
        delayed = {key: [1000] + values for key, values in sim.items()}
        results, report = evaluate_run(delayed, [0, 2, 9, 16], config, "normal")
        for name in ("Wound closure", "Inflammation", "Neutrophils", "Macrophages"):
            self.assertEqual(before["coverage"][name], report["coverage"][name])
        self.assertEqual(results["wound"]["simulation_days"], [-2, 0, 7, 14])
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2)
        try:
            plot_wound_panels(results["wound"], [0, 2, 9, 16], axes)
            self.assertEqual(list(axes[0, 0].lines[0].get_xdata()), [-2, 0, 7, 14])
            self.assertEqual(axes[1, 0].get_xlabel(), "Days since wound")
        finally:
            plt.close(fig)

    def test_wound_clock_matches_scheduled_step(self):
        config = {"skin": {"wound": {"trigger_h": 12.37}}}
        self.assertAlmostEqual(wound_comparison_days([1], config)[0], 1 - 12.3 / 24)
        config["skin"]["wound"]["trigger_h"] = 12.9
        self.assertEqual(wound_comparison_days([12.9 / 24], config), [0.0])
        for invalid in (-1, float("nan"), True, "12"):
            config["skin"]["wound"]["trigger_h"] = invalid
            with self.assertRaises(ValueError):
                wound_comparison_days([1], config)

    def test_independent_ra_and_tumor_clocks_are_not_shifted(self):
        config = {"skin": {"wound": {"trigger_h": 48},
                           "ra": {"enabled": True}, "tumor": {"enabled": True}}}
        with patch("literature.lib.validate_ra", return_value={
                "tnf_rmse": .1, "ref_tnf_at_sim": [1, 0]}) as ra, patch(
                "literature.lib.validate_tumor", return_value={"description": "available"}) as tumor:
            results, report = evaluate_run({}, [2, 9], config, condition_from_config(config))
        self.assertEqual(ra.call_args.args[1], [2, 9])
        self.assertEqual(tumor.call_args.args[1], [2, 9])
        self.assertEqual(report["coverage"]["TNF-alpha"]["comparison_dates"]["time_origin"], "simulation")

    def test_reference_is_not_extrapolated(self):
        reference = interpolate([1, 3], [0, 1], [0, 1, 2, 3, 4], extrapolate=False)
        self.assertTrue(math.isnan(reference[0]))
        self.assertTrue(math.isnan(reference[-1]))
        self.assertEqual(compute_rmse([999, 0, .5, 1, 999], reference), 0)

    def test_late_simulation_peak_cannot_change_earlier_score(self):
        columns = ["mean_tgfb_wound", "mean_vegf_wound", "mean_fibronectin_wound", "mean_mmp_wound"]
        before = validate_microenvironment({key: [0, 1, .5] for key in columns}, [0, 7, 28])
        after = validate_microenvironment({key: [0, 1, .5, 1000] for key in columns}, [0, 7, 28, 100])
        for key in ["tgfb_rmse", "vegf_rmse", "fn_rmse", "mmp_rmse"]:
            self.assertEqual(before[key], after[key])

    def test_missing_config_is_not_normal(self):
        with self.assertRaises(FileNotFoundError):
            detect_condition("missing-run-config-982135.toml")

    def test_condition_is_explicit(self):
        self.assertEqual(condition_from_config({"analysis": {"profile": "venous"}}), "venous")
        self.assertEqual(condition_from_config({"simulation": {"output_dir": "surgical"}}), "normal")
        with self.assertRaises(ValueError):
            condition_from_config({"skin": {"diabetic": {"mode": True}, "burn": {"mode": True}}})

    def test_disabled_individual_field_is_not_scored(self):
        config = {"skin": {"wound": {"enabled": True}, "mmp": {"enabled": True}}}
        with patch("literature.lib.validate_wound", return_value=None), patch(
                "literature.lib.validate_microenvironment", return_value={"tgfb_rmse": .1, "vegf_rmse": .1, "fn_rmse": .1, "mmp_rmse": .4}):
            _, report = evaluate_run({}, [0, 1], config, "normal")
        self.assertEqual(report["coverage"]["TGF-b"]["status"], "not_tested")
        self.assertEqual(report["coverage"]["MMP"]["status"], "fail")

    def test_report_retains_actual_overlap_sample_days(self):
        config = {"skin": {"wound": {"enabled": True}}}
        with patch("literature.lib.validate_wound", return_value={
                "closure_rmse": 2, "ref_closure_at_sim": [0, float("nan"), 1]}):
            _, report = evaluate_run({}, [0, .5, 2], config, "normal")
        dates = report["coverage"]["Wound closure"]["comparison_dates"]
        self.assertEqual(dates["sample_days"], [0, 2])

    def test_enabled_zero_is_not_omitted(self):
        config = {"skin": {"wound": {"enabled": True}, "fibroblast": {"enabled": True}}}
        self.assertEqual(detect_modules({}, config)[:2], (True, True))

    def test_no_results_never_pass(self):
        self.assertEqual(validation_report()["status"], "not_tested")
        self.assertEqual(validation_report(tumor={"description": "available"})["status"], "not_tested")

    def test_failed_ra_is_gated(self):
        report = validation_report(ra={"tnf_rmse": .4, "il6_rmse": .1, "cart_rmse": .1})
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["coverage"]["Bone"]["status"], "not_tested")

    def test_mismatched_references_never_used(self):
        self.assertIsNone(validate_microenvironment({}, [], "burn"))
        self.assertIsNone(validate_wound({}, [], "rheumatoid"))

if __name__ == "__main__":
    unittest.main()
