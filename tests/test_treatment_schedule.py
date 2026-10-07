import unittest
import os
import tempfile
from unittest import mock

from scripts.study.gen_treatment_schedule import (
    ALL_TREATMENTS, encode_runtime_schedule, generate_timing_experiment,
    load_treatment, tomllib, validate_runtime_parameters, generate_screen_experiment,
)
from scripts.study import experiment_runner


class TreatmentTimingTests(unittest.TestCase):
    def test_preparation_keeps_baseline_and_embeds_future_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bdm.toml")
            def merge():
                with open(path, "w") as f:
                    f.write("[skin]\nwater_recovery_rate = 0.02\n")
            with mock.patch.object(experiment_runner, "REPO", directory), \
                 mock.patch.object(experiment_runner, "apply_study"), \
                 mock.patch.object(experiment_runner, "merge_config", side_effect=merge):
                experiment_runner.prepare_experiment_config(
                    {"schedule": [{"treatment": "moisture", "start_day": 7}]},
                    {"study": "diabetic-wound", "profile": None})
            with open(path, "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(data["skin"]["water_recovery_rate"], 0.02)
            self.assertEqual(data["treatment_schedule"][0]["start_day"], 7)
            self.assertEqual(tomllib.loads(data["treatment_schedule"][0]["parameters"])["skin"]["water_recovery_rate"], 0.06)

    def test_screen_uses_same_day_zero_event_semantics_as_timing(self):
        configs = tomllib.loads(generate_screen_experiment(["npwt", "moisture"], {}))["experiment"]["configs"]
        self.assertEqual(configs[-1]["schedule"], [{"treatment": "npwt", "start_day": 0},
                                                {"treatment": "moisture", "start_day": 0}])
        self.assertNotIn("treatments", configs[-1])

    def test_consensus_uses_distinct_seeds_and_rejects_incomplete_cohort(self):
        with tempfile.TemporaryDirectory() as directory:
            metrics = os.path.join(directory, "metrics.csv")
            with open(metrics, "w") as f:
                f.write("time_h,value\n0,1\n")
            with mock.patch.object(experiment_runner, "prepare_experiment_config"), \
                 mock.patch.object(experiment_runner, "override_param") as override, \
                 mock.patch.object(experiment_runner, "get_metrics_path", return_value=metrics), \
                 mock.patch.object(experiment_runner, "aggregate_csvs", return_value=({}, {})) as aggregate, \
                 mock.patch.object(experiment_runner, "run_simulation", side_effect=[(True, 1), (True, 1), (False, 1)]):
                with self.assertRaisesRegex(RuntimeError, "cohort is incomplete"):
                    experiment_runner.run_consensus("test", {}, {"seed": 11}, 3, directory)
                self.assertEqual(override.call_args_list, [mock.call("simulation.random_seed", n) for n in [11, 12, 13]])
                aggregate.assert_not_called()

    def test_timing_grid_retains_full_treatments_and_actual_start_days(self):
        data = tomllib.loads(generate_timing_experiment(["npwt", "moisture"], [0, 7], {}))
        configs = data["experiment"]["configs"]
        self.assertEqual(len(configs), 5)
        delayed = configs[-1]
        self.assertNotIn("overrides", delayed)
        self.assertNotIn("treatments", delayed)
        encoded = tomllib.loads(encode_runtime_schedule(delayed["schedule"], "diabetic-wound"))
        self.assertEqual([event["start_day"] for event in encoded["treatment_schedule"]], [7, 7])
        for event in encoded["treatment_schedule"]:
            self.assertEqual(tomllib.loads(event["parameters"])["skin"]["water_recovery_rate"],
                             load_treatment(event["name"])["skin.water_recovery_rate"])

    def test_all_current_treatments_are_schedulable_and_immutable(self):
        schedule = [{"treatment": name, "start_day": 7} for name in ALL_TREATMENTS]
        data = tomllib.loads(encode_runtime_schedule(schedule, "diabetic-wound"))
        self.assertEqual([event["name"] for event in data["treatment_schedule"]], ALL_TREATMENTS)

    def test_rejects_invalid_or_unsafe_events(self):
        for day in [-1, float("nan"), float("inf"), True]:
            with self.assertRaises(ValueError):
                encode_runtime_schedule([{"treatment": "npwt", "start_day": day}], "diabetic-wound")
        for parameters in [{"geometry": {"patch_um": 100}},
                           {"skin": {"mmp": {"enabled": True}}},
                           {"skin": {"water_recovery_rate": float("nan")}}]:
            with self.assertRaises(ValueError):
                validate_runtime_parameters(parameters)

    def test_unknown_treatment_never_runs_as_untreated(self):
        with self.assertRaises(ValueError):
            encode_runtime_schedule([{"treatment": "missing", "start_day": 0}], "diabetic-wound")


if __name__ == "__main__":
    unittest.main()
