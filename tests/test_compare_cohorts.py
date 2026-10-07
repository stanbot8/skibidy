"""Protect the scientific meaning of replicate and paired reports."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.compare_replicates import load_cohort, summarize
from scripts.compare_cohorts import compare


def cohort(values=(2, 20)):
    runs = {}
    for seed, value in zip((42, 43), values):
        item = dict(status="fail" if value > 15 else "pass", rmse_pct=value,
                    comparison_dates=dict(start_day=0, end_day=2,
                                          simulation_samples=3, sample_days=[0, 1, 2]))
        runs[seed] = dict(seed=seed, condition="diabetic", profile="diabetic",
                          validation=dict(status=item["status"], coverage={"Neutrophils": item}))
    return runs


class CohortComparisonTest(unittest.TestCase):
    def test_mean_cannot_hide_individual_failure(self):
        report = summarize(cohort())
        self.assertEqual(report["coverage"]["Neutrophils"]["mean_rmse_pct"], 11)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["coverage"]["Neutrophils"]["status"], "fail")
        self.assertAlmostEqual(report["coverage"]["Neutrophils"]["sample_sd_pct"], 18 / 2**.5)

    def test_paired_deltas_and_missing_seed(self):
        control, candidate = cohort((10, 12)), cohort((6, 10))
        item = compare(control, candidate)["coverage"]["Neutrophils"]
        self.assertEqual(item["per_seed"], {"42": -4, "43": -2})
        self.assertEqual(item["mean_delta_pct"], -3)
        candidate.pop(43)
        with self.assertRaisesRegex(ValueError, "identical seed"):
            compare(control, candidate)

    def test_untested_is_never_zero_error(self):
        candidate = cohort()
        candidate[43]["validation"] = dict(status="not_tested",
            coverage={"Neutrophils": dict(status="not_tested")})
        item = compare(cohort(), candidate)["coverage"]["Neutrophils"]
        self.assertEqual(item["status"], "not_tested")
        self.assertNotIn("mean_delta_pct", item)

    def test_interior_dates_and_condition_must_match(self):
        for mutation in ("dates", "condition"):
            candidate = copy.deepcopy(cohort())
            if mutation == "dates":
                candidate[42]["validation"]["coverage"]["Neutrophils"]["comparison_dates"]["sample_days"] = [0, .5, 2]
            else:
                candidate[42]["condition"] = "normal"
            with self.assertRaises(ValueError):
                compare(cohort(), candidate)

    def test_single_run_has_no_sample_sd(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            summarize({42: cohort()[42]})

    def test_loader_uses_saved_diabetic_config_and_rejects_mixed_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for seed in (42, 43):
                directory = root / f"seed{seed}"
                (directory / "skibidy").mkdir(parents=True)
                (directory / "bdm.toml").write_text(
                    f"[simulation]\nrandom_seed = {seed}\n[skin]\nduration_days = 1\n"
                    "metrics_interval_h = 24\n[skin.diabetic]\nmode = true\n")
                (directory / "skibidy/metrics.csv").write_text("time_h\n0\n24\n")
            with patch("scripts.compare_replicates.evaluate_run", return_value=(None,
                       dict(status="not_tested", coverage={}))) as evaluate:
                runs = load_cohort(root)
                self.assertEqual({r["condition"] for r in runs.values()}, {"diabetic"})
                self.assertEqual(evaluate.call_args.args[-1], "diabetic")
                path = root / "seed43/bdm.toml"
                path.write_text(path.read_text() + "macrophage_apoptosis_factor = 0.3\n")
                with self.assertRaisesRegex(ValueError, "mix configurations"):
                    load_cohort(root)


if __name__ == "__main__":
    unittest.main()
