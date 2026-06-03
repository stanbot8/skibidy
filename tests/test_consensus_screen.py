"""Exercise saved cohort evidence through the real analysis consumers."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from batch.lib import aggregate_csvs, file_sha256, write_csv
from literature.lib import (load_csv, _ref_path, interpolate, evaluate_run,
                            screen_saved_cohort)

ROOT = Path(__file__).resolve().parents[1]


class ConsensusScreenTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.config = {"simulation": {"random_seed": 71},
                       "skin": {"duration_days": 30, "metrics_interval_h": 24,
                                "wound": {"enabled": True}}}

    def tearDown(self):
        self.temp.cleanup()

    def make_cohort(self, offsets=(-40, 40), end=30):
        refs = [("closure_kinetics_punch_biopsy.csv", "closure_pct", "wound_closure_pct"),
                ("inflammation_timecourse.csv", "inflammation_normalized", "mean_infl_wound"),
                ("immune_cell_kinetics.csv", "neutrophils_normalized", "n_neutrophils"),
                ("immune_cell_kinetics.csv", "macrophages_normalized", "n_macrophages")]
        days = list(range(end + 1))
        data = {"time_h": [day * 24 for day in days]}
        for filename, source, column in refs:
            ref = load_csv(_ref_path(filename))
            data[column] = interpolate(ref["day"], ref[source], days)
        paths, records = [], []
        for index, offset in enumerate(offsets):
            folder = self.directory / "raw" / f"run_{index:03d}" / "skibidy"
            folder.mkdir(parents=True)
            metrics = folder / "metrics.csv"
            run = copy.deepcopy(data)
            run["wound_closure_pct"] = [value + offset for value in run["wound_closure_pct"]]
            write_csv(run, metrics)
            config_path = folder / "run-config.toml"
            config_path.write_text(f'[simulation]\nrandom_seed = {71 + index}\n'
                                   f'[skin]\nduration_days = {end}\nmetrics_interval_h = 24\n'
                                   '[skin.wound]\nenabled = true\n', encoding="utf-8")
            records.append(dict(run=index, seed=71 + index, status="ok", success=True,
                                returncode=0, metrics_sha256=file_sha256(metrics),
                                config_sha256=file_sha256(config_path)))
            paths.append(metrics)
        (self.directory / "run-config.toml").write_bytes(config_path.read_bytes())
        mean, spread = aggregate_csvs(paths)
        write_csv(mean, self.directory / "metrics.csv")
        write_csv(dict(mean, **{key + "_std": value for key, value in spread.items()}),
                  self.directory / "consensus.csv")
        self.manifest = dict(status="complete", requested_runs=len(paths), runs=records,
                             metrics_sha256=file_sha256(self.directory / "metrics.csv"),
                             consensus_sha256=file_sha256(self.directory / "consensus.csv"))
        self.save_manifest()
        self.config["skin"]["duration_days"] = end

    def save_manifest(self):
        (self.directory / "cohort.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def screen(self, filename="consensus.csv"):
        path = self.directory / filename
        sim = load_csv(path)
        _, report = evaluate_run(sim, [h / 24 for h in sim["time_h"]], self.config, "normal")
        return screen_saved_cohort(path, report)

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / script), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True)

    def test_failing_seeds_cannot_pass_through_their_average(self):
        self.make_cohort()
        result = self.cli("literature/validate_all.py", self.directory / "consensus.csv", "--quick")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads((self.directory / "validation.json").read_text())
        self.assertEqual(report["consensus_status"], "pass")
        self.assertEqual(report["status"], "fail")
        self.assertEqual([run["status"] for run in report["replicates"]], ["fail", "fail"])
        self.assertFalse(report["empirical_validation"])
        self.assertIn("mean trajectory", result.stdout)
        self.assertIn("Seed 71: FAIL", result.stdout)
        module = self.cli("literature/validators/compare.py", "wound",
                          self.directory / "metrics.csv", "--quick")
        self.assertEqual(module.returncode, 1, module.stdout + module.stderr)
        from scripts.dashboard import run_validation
        self.assertEqual(run_validation(str(self.directory / "metrics.csv"))["status"], "fail")
        from scripts.figures import load_consensus
        load_consensus(str(self.directory / "consensus.csv"))
        analysis = self.cli("batch/analyze.py", self.directory, "--validate")
        self.assertEqual(analysis.returncode, 1, analysis.stdout + analysis.stderr)

    def test_exact_target_runs_pass_with_real_batch_serialization(self):
        self.make_cohort((0, 0))
        self.assertEqual(self.screen()["status"], "pass")
        self.assertEqual(self.screen("metrics.csv")["status"], "pass")
        result = self.cli("literature/validate_all.py", self.directory / "consensus.csv", "--quick")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_manifest_cannot_establish_a_cohort_pass(self):
        self.make_cohort((0, 0))
        (self.directory / "cohort.json").unlink()
        self.assertEqual(self.screen()["status"], "not_tested")
        self.assertEqual(self.screen("metrics.csv")["status"], "not_tested")

    def test_changed_raw_evidence_is_rejected_by_consumers(self):
        self.make_cohort((0, 0))
        (self.directory / "validation.json").write_text('{"status": "pass"}')
        raw = self.directory / "raw/run_000/skibidy/metrics.csv"
        raw.write_text(raw.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "changed metrics_sha256"):
            self.screen()
        result = self.cli("literature/validate_all.py", self.directory / "consensus.csv", "--quick")
        self.assertNotEqual(result.returncode, 0)
        report = json.loads((self.directory / "validation.json").read_text())
        self.assertEqual(report["status"], "not_tested")
        self.assertIn("changed metrics_sha256", report["evidence_error"])

    def test_duplicate_seed_or_changed_configuration_is_rejected(self):
        self.make_cohort((0, 0))
        self.manifest["runs"][1]["seed"] = 71
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.screen()
        self.manifest["runs"][1]["seed"] = 72
        self.save_manifest()
        config = self.directory / "run-config.toml"
        config.write_text(config.read_text().replace("duration_days = 30", "duration_days = 29"))
        with self.assertRaisesRegex(ValueError, "configuration differs"):
            self.screen()

    def test_summary_cannot_disagree_with_runs_even_when_hash_updated(self):
        self.make_cohort((0, 0))
        path = self.directory / "consensus.csv"
        original = load_csv(path)
        for field, message in [("wound_closure_pct", "mean differs"),
                               ("wound_closure_pct_std", "spread differs")]:
            with self.subTest(field=field):
                altered = copy.deepcopy(original)
                altered[field][1] += 1
                write_csv(altered, path)
                self.manifest["consensus_sha256"] = file_sha256(path)
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, message):
                    self.screen()

    def test_missing_spread_cannot_be_presented_as_zero_uncertainty(self):
        self.make_cohort((0, 0))
        path = self.directory / "consensus.csv"
        data = load_csv(path)
        del data["wound_closure_pct_std"]
        write_csv(data, path)
        self.manifest["consensus_sha256"] = file_sha256(path)
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "missing or unexpected"):
            self.screen()

    def test_explicit_config_cannot_reinterpret_a_saved_cohort(self):
        self.make_cohort((0, 0))
        config = self.directory / "alternate.toml"
        saved = (self.directory / "run-config.toml").read_text()
        config.write_text(saved.replace("enabled = true", "enabled = false"))
        result = self.cli("literature/validate_all.py", self.directory / "consensus.csv",
                          "--config", config, "--quick")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads((self.directory / "validation.json").read_text())
        self.assertEqual(report["status"], "not_tested")
        self.assertIn("Selected screening configuration differs", report["evidence_error"])

    def test_partial_window_is_explicit_in_both_console_commands(self):
        self.make_cohort((0, 0), end=14)
        full = self.cli("literature/validate_all.py", self.directory / "consensus.csv", "--quick")
        module = self.cli("literature/validators/compare.py", "wound",
                          self.directory / "consensus.csv", "--quick")
        for result in (full, module):
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PARTIAL reference window: 0.0 to 14.0 days", result.stdout)


if __name__ == "__main__":
    unittest.main()
