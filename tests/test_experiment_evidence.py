import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.study import experiment_evidence as evidence
from scripts.study.experiment_runner import load_experiment, run_experiment_file
from scripts.study.export_experiment_evidence import export_cohort


class ExperimentEvidenceTests(unittest.TestCase):
    def test_incomplete_cohort_cannot_export_success_shaped_products(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "failed"
            output.mkdir()
            (output / "manifest.json").write_text(json.dumps({"status": "failed", "runs": [],
                                                               "requested_runs": 30}))
            destination = Path(td) / "published"
            with self.assertRaisesRegex(ValueError, "incomplete cohort"):
                export_cohort(output, destination)
            self.assertFalse(destination.exists())

    def test_isolated_config_preserves_root_and_retains_future_event(self):
        original = (evidence.ROOT / "bdm.toml").read_bytes() if (evidence.ROOT / "bdm.toml").exists() else None
        experiment = load_experiment(evidence.ROOT / "studies/diabetic-wound/experiments/proresolution_sensitivity.toml")
        with tempfile.TemporaryDirectory() as td:
            path = evidence.prepare_config(experiment["configs"][4], experiment, Path(td) / "run", 43)
            from batch.lib import get_tomllib
            cfg = get_tomllib().loads(path.read_text())
            self.assertEqual(cfg["skin"]["duration_days"], 42)
            self.assertEqual(cfg["simulation"]["random_seed"], 43)
            self.assertFalse(cfg["skin"]["hot_reload"])
            self.assertEqual(cfg["skin"]["diabetic"]["efferocytosis_factor"], .5)
            self.assertEqual(cfg["treatment_schedule"][0]["start_day"], 7)
            self.assertEqual(cfg["analysis"], {"profile": "diabetic", "study": "diabetic-wound",
                                                "condition": "diabetic"})
        if original is not None:
            self.assertEqual((evidence.ROOT / "bdm.toml").read_bytes(), original)

    def test_user_study_profile_treatment_output_and_saved_identity(self):
        with tempfile.TemporaryDirectory() as td:
            study = Path(td) / "diabetic-wound"  # same-name user study takes precedence
            (study / "treatments").mkdir(parents=True)
            (study / "experiments").mkdir()
            (study / "preset.toml").write_text("[skin]\nduration_days=2\n")
            (study / "diabetic-wound.skibidy").write_text('[project]\nprofile="burn"\n')
            (study / "treatments/local.toml").write_text("[skin]\nwater_recovery_rate=0.123\n")
            source = study / "experiments/test.toml"
            source.write_text('[experiment]\nname="User burn"\n[[experiment.configs]]\nlabel="delayed"\n'
                              '[[experiment.configs.schedule]]\ntreatment="local"\nstart_day=1\n')
            with mock.patch.dict(os.environ, {"SKIBIDY_USER_STUDIES": td}):
                experiment = load_experiment(source)
                self.assertEqual(experiment["profile"], "burn")
                path = evidence.prepare_config(experiment["configs"][0], experiment,
                                               Path(td) / "private-run", 12)
                from batch.lib import get_tomllib
                cfg = get_tomllib().loads(path.read_text())
                self.assertEqual(cfg["skin"]["duration_days"], 2)
                self.assertEqual(cfg["analysis"], {"profile": "burn", "study": "diabetic-wound",
                                                    "condition": "burn"})
                params = get_tomllib().loads(cfg["treatment_schedule"][0]["parameters"])
                self.assertEqual(params["skin"]["water_recovery_rate"], .123)
                with mock.patch.object(evidence, "run_complete_experiment") as run:
                    run_experiment_file(source)
                self.assertTrue(Path(run.call_args.args[1]).is_relative_to(study / "results"))

    def test_peak_and_threshold_are_computed_per_replicate_with_censoring(self):
        first = evidence.scalar_outcomes({"time_h": [0, 24, 48], "wound_closure_pct": [50, 80, 90],
                                         "mean_infl_wound": [10, 0, 0]})
        second = evidence.scalar_outcomes({"time_h": [0, 24, 48], "wound_closure_pct": [0, 20, 60],
                                          "mean_infl_wound": [0, 10, 0]})
        self.assertEqual(first["time_to_50pct_days"], 0)
        summary = evidence.summarize_replicates([{"outcomes": first}, {"outcomes": second}])
        self.assertEqual(summary["peak_inflammation"], 10)  # peak of mean curve would be 5
        self.assertIsNone(summary["time_to_90pct_days"])
        self.assertEqual(summary["time_to_90pct_days_n_observed"], 1)

    def test_active_condition_precedes_profile_and_profile_aliases_are_canonical(self):
        from batch.lib import get_tomllib
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.toml"
            path.write_text('[skin.burn]\nmode=true\n')
            evidence.save_analysis_identity(path, {}, {}, "normal", "custom")
            self.assertEqual(get_tomllib().loads(path.read_text())["analysis"]["condition"], "burn")
            for profile, condition in [("aged", "aging"), ("aged_diabetic", "diabetic")]:
                path.write_text('[skin]\nduration_days=2\n')
                evidence.save_analysis_identity(path, {}, {}, profile, "custom")
                self.assertEqual(get_tomllib().loads(path.read_text())["analysis"]["condition"], condition)
            path.write_text('[skin]\nduration_days=2\n')
            evidence.save_analysis_identity(path, {"condition": "surgical"}, {}, "normal", "custom")
            self.assertEqual(get_tomllib().loads(path.read_text())["analysis"]["condition"], "surgical")

    def test_failed_run_keeps_full_seed_plan_and_does_not_publish_summary(self):
        def config(cfg, experiment, directory, seed):
            directory.mkdir(parents=True)
            path = directory / "bdm.toml"
            path.write_text("[skin]\nduration_days=42\n")
            return path

        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "cohort"
            with mock.patch.object(evidence, "freeze_binary", return_value=(Path("/fake/binary"),
                                  {"project_files": [], "dependencies": []}, {})), \
                 mock.patch.object(evidence, "prepare_config", side_effect=config), \
                 mock.patch.object(evidence.subprocess, "run", return_value=mock.Mock(returncode=7)):
                with self.assertRaisesRegex(RuntimeError, "exit 7"):
                    evidence.run_complete_experiment({"configs": [{"label": "baseline"}],
                                                     "runs_per_config": 3, "seed": 42}, output, "/fake/binary")
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual([r["seed"] for r in manifest["runs"]], [42, 43, 44])
            self.assertEqual([r["status"] for r in manifest["runs"]], ["failed", "pending", "pending"])
            self.assertFalse((output / "comparison.csv").exists())
            self.assertFalse((output / "summary.txt").exists())

    def test_pairing_uses_seed_identity_and_rejects_mismatched_cohorts(self):
        def record(seed, value):
            return {"seed": seed, "label": "test", "outcomes": {"closure": value}}
        with tempfile.TemporaryDirectory() as td:
            evidence.write_replicate_tables([
                {"label": "baseline", "replicates": [record(42, 10), record(43, 20)]},
                {"label": "treatment", "replicates": [record(43, 25), record(42, 15)]}], td)
            self.assertIn("treatment,closure,2,5", (Path(td) / "paired_deltas.csv").read_text())
            with self.assertRaisesRegex(ValueError, "mismatched seeds"):
                evidence.write_replicate_tables([
                    {"replicates": [record(42, 10)]}, {"label": "treatment", "replicates": [record(44, 15)]}], td)


if __name__ == "__main__":
    unittest.main()
