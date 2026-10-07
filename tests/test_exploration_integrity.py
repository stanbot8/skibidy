"""Exploration must retain distinct replicates and reject incomplete evidence."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from batch import lib, sensitivity, stats, sweep


class ExplorationIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "config.toml"
        self.source.write_text("# test experiment\n")
        self.metrics = self.root / "metrics.csv"
        self.metrics.write_text("time_h,value\n0,1\n24,2\n")
        self.seeds = []
        self.runs = []

    def run_exploration(self, module, failed=False):
        cfg = dict(name="test", skin="normal", study="wound", treatment=None,
                   runs_per_value=2, trajectories=1, levels=4, replicates=2,
                   params=[dict(param="skin.test", values=[1, 2], min=1, max=2)],
                   primary="value", secondary=[], measure="final", source_path=str(self.source))

        def override(name, value):
            if name == "simulation.random_seed":
                self.seeds.append(value)

        def simulate(output_path=None):
            self.runs.append(output_path)
            return not failed, .1

        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(patch.object(module, "__file__", str(self.root / "runner.py")))
            for name in ("build_if_needed", "merge_config", "apply_profile", "apply_study", "setup_run"):
                stack.enter_context(patch.object(lib, name))
            stack.enter_context(patch.object(lib, "override_param", side_effect=override))
            stack.enter_context(patch.object(lib, "run_simulation", side_effect=simulate))
            stack.enter_context(patch.object(lib, "get_metrics_path", return_value=str(self.metrics)))
            if module is sensitivity:
                stack.enter_context(patch.object(sensitivity, "generate_morris_trajectories",
                                                 return_value=[([[0], [2]], [0])]))
                return sensitivity.run_sensitivity(cfg)
            return sweep.run_sweep(cfg)

    def test_sweep_seeds_are_distinct_and_paired_across_points(self):
        self.run_exploration(sweep)
        self.assertEqual(self.seeds, [42, 43, 42, 43])
        self.assertEqual(len(set(self.runs)), 4)

    def test_sensitivity_seeds_are_distinct_and_paired_within_trajectory(self):
        self.run_exploration(sensitivity)
        self.assertEqual(self.seeds, [42, 43, 42, 43])

    def test_morris_grid_is_reproducible_without_global_rng_side_effects(self):
        import random
        state = random.getstate()
        params = [{"param": "a"}, {"param": "b"}]
        before = sensitivity.generate_morris_trajectories(params, 3, 4, seed=42)
        self.assertEqual(before, sensitivity.generate_morris_trajectories(params, 3, 4, seed=42))
        self.assertEqual(state, random.getstate())

    def test_failed_sweep_does_not_publish_summary(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.run_exploration(sweep, failed=True)
        self.assertFalse(list(self.root.rglob("summary.csv")))

    def test_failed_sensitivity_does_not_publish_no_effect(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.run_exploration(sensitivity, failed=True)
        self.assertFalse(list(self.root.rglob("sensitivity.csv")))

    def test_missing_effects_cannot_be_zero_sensitivity(self):
        with self.assertRaises(ValueError):
            sensitivity.summarize_effects({"parameter": {"outcome": []}})

    def test_degenerate_statistics_are_not_no_difference(self):
        for a, b in (([10, 10], [0, 0]), ([0, 0], [0, 0]), ([1], [2, 3])):
            with self.assertRaises(ValueError):
                stats.welch_t_test(a, b)
        with self.assertRaises(ValueError):
            stats.confidence_interval([5])
        self.assertGreater(stats.confidence_interval([1, 2, 3])["ci_hi"], 2)
        self.assertLess(stats.welch_t_test([10, 11, 12], [0, 1, 2])["p_value"], .05)

    def test_foreign_study_treatment_is_rejected_without_mutation(self):
        with patch.object(lib, "apply_overlay") as overlay:
            with self.assertRaises((ValueError, SystemExit)):
                lib.apply_treatment("npwt", "wound")
            overlay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
