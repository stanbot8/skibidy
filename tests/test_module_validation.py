"""Exercise the maintained module CLI with saved run evidence."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "literature/validators/compare.py"


class ModuleValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "saved-run"
        self.run.mkdir()
        self.metrics = self.run / "metrics.csv"
        self.config = self.run / "run-config.toml"
        self.report = self.run / "report.json"
        # Today's configuration must not override the completed run.
        (self.root / "bdm.toml").write_text("[skin.diabetic]\nmode = false\n")
        self.save_config()
        self.save_metrics()

    def save_config(self, condition="normal", enabled=True, trigger=0):
        self.config.write_text(
            "[skin]\nduration_days = 16\nmetrics_interval_h = 24\n"
            f"[skin.wound]\nenabled = {str(enabled).lower()}\ntrigger_h = {trigger}\n"
            "[skin.fibroblast]\nenabled = true\n[skin.mmp]\nenabled = true\n"
            "[skin.ph]\n[skin.diabetic]\n"
            f"mode = {str(condition == 'diabetic').lower()}\n")

    def save_metrics(self, closure=(0, 0, 0), days=(0, 7, 16)):
        with self.metrics.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("time_h", "wound_closure_pct", "mean_infl_wound",
                             "n_neutrophils", "n_macrophages", "mean_tgfb_wound",
                             "mean_mmp_wound", "mean_ph_wound", "n_myofibroblasts",
                             "n_fibroblasts", "mean_collagen_wound", "mean_vegf_wound",
                             "mean_fibronectin_wound"))
            for day, value in zip(days, closure):
                writer.writerow((day * 24, value, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    def invoke(self, module, *args, quick=True):
        command = [sys.executable, str(COMMAND), module, str(self.metrics),
                   "--report", str(self.report), *args]
        if quick:
            command.append("--quick")
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True)

    def read_report(self):
        return json.loads(self.report.read_text())

    def test_enabled_zero_fails_instead_of_disappearing(self):
        result = self.invoke("wound")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = self.read_report()
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["coverage"]["Wound closure"]["status"], "fail")
        self.assertEqual(report["tested"], 4)

    def test_selected_immune_can_pass_while_other_wound_screens_fail(self):
        from literature.lib import interpolate, load_csv
        reference = load_csv(ROOT / "modules/immune/data/immune_cell_kinetics.csv")
        days = list(range(17))
        self.save_metrics([0] * len(days), days)
        with self.metrics.open(newline="") as f:
            rows = list(csv.DictReader(f))
        for column, reference_column in (("n_neutrophils", "neutrophils_normalized"),
                                          ("n_macrophages", "macrophages_normalized")):
            values = interpolate(reference["day"], reference[reference_column], days)
            for row, value in zip(rows, values):
                row[column] = value
        with self.metrics.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        result = self.invoke("immune")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_report()["status"], "pass")
        self.assertEqual(self.invoke("wound").returncode, 1)

    def test_saved_diabetic_condition_and_unsupported_fibroblasts(self):
        self.save_config("diabetic")
        result = self.invoke("fibroblast")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = self.read_report()
        self.assertEqual(report["condition"], "diabetic")
        self.assertEqual(report["status"], "not_tested")
        self.assertEqual(report["tested"], 0)

    def test_disabled_wound_is_not_scored_despite_positive_output(self):
        self.save_config(enabled=False)
        self.save_metrics((0, 70, 95))
        result = self.invoke("immune")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.read_report()["status"], "not_tested")

    def test_condition_mismatch_and_missing_config_rejected(self):
        self.save_config("diabetic")
        result = self.invoke("wound", "--normal")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from saved run condition", result.stderr)
        self.assertFalse(self.report.exists())
        self.config.unlink()
        (self.root / "bdm.toml").unlink()
        result = self.invoke("wound")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No saved run configuration", result.stderr)

    def test_truncated_run_rejected_before_scoring(self):
        self.save_metrics(days=(0, 1, 2))
        result = self.invoke("wound")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete duration", result.stderr)
        self.assertFalse(self.report.exists())

    def test_delayed_full_and_module_reports_agree(self):
        self.save_config(trigger=48)
        self.save_metrics((0, 45, 80), (2, 9, 16))
        result = self.invoke("wound", quick=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        full_path = self.run / "full.json"
        full = subprocess.run([sys.executable, str(ROOT / "literature/validate_all.py"),
                               str(self.metrics), "--quick", "--report", str(full_path)],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(full.returncode, 1, full.stderr)
        selected = self.read_report()["coverage"]
        all_coverage = json.loads(full_path.read_text())["coverage"]
        for name, item in selected.items():
            self.assertEqual(item, all_coverage[name])
        self.assertEqual(selected["Wound closure"]["comparison_dates"]["sample_days"], [0, 7, 14])
        self.assertTrue((self.run / "plots/wound_validation.png").is_file())

    def test_diabetic_microenvironment_does_not_borrow_normal_references(self):
        self.save_config("diabetic")
        result = self.invoke("microenv", quick=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        coverage = self.read_report()["coverage"]
        for name in ("pH", "VEGF", "Fibronectin"):
            self.assertEqual(coverage[name]["status"], "not_tested")
        self.assertTrue((self.run / "plots/microenvironment_validation.png").is_file())

    def test_publication_figures_share_saved_clock_and_condition_rules(self):
        from scripts import figures
        from literature.lib import evaluate_run
        from batch.lib import parse_toml
        self.save_config(trigger=48)
        data = figures.load_consensus(str(self.metrics))
        days = figures.consensus_days(data)
        self.assertEqual(days, [-2, 5, 14])
        result = figures.validate_consensus_wound(data, days)
        expected, _ = evaluate_run(data, [0, 7, 16], parse_toml(self.config), "normal")
        self.assertEqual(result["closure_rmse"], expected["wound"]["closure_rmse"])
        self.save_config("diabetic")
        data = figures.load_consensus(str(self.metrics))
        days = figures.consensus_days(data)
        self.assertIsNone(figures.validate_consensus_fibroblast(data, days))
        with self.assertRaises(ValueError):
            figures.validate_consensus_wound(data, days, "normal")
        figures.supplementary_panels(data, days, "diabetic", str(self.root), ["png"])
        self.assertFalse((self.root / "figS_diabetic_collagen.png").exists())
        self.assertTrue((self.root / "figS_diabetic_mmp.png").exists())

    def test_ra_dashboard_renders_enabled_zero_cytokines(self):
        from literature.validators.ra_dashboard import load_run
        self.config.write_text(
            "[skin]\nduration_days = 30\nmetrics_interval_h = 24\n"
            "[skin.wound]\nenabled = false\n[skin.ra]\nenabled = true\n")
        with self.metrics.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("time_h", "mean_tnf_alpha_wound", "mean_il6_wound",
                             "mean_cartilage_wound", "mean_bone_wound",
                             "mean_tcell_wound", "mean_synovial_wound"))
            for day in (0, 15, 30):
                writer.writerow((day * 24, 0, 0, 1, 1, 0, 0))
        _, _, results = load_run(str(self.metrics))
        self.assertGreater(results["tnf_rmse"], 0)
        result = subprocess.run(
            [sys.executable, str(ROOT / "literature/validators/ra_dashboard.py"),
             str(self.metrics)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.run / "plots/ra_dashboard.png").is_file())

    def test_ra_dashboard_rejects_disabled_and_truncated_saved_runs(self):
        from literature.validators.ra_dashboard import load_run
        self.save_config(enabled=False)
        with self.assertRaisesRegex(ValueError, "RA is disabled"):
            load_run(str(self.metrics))
        self.save_metrics(days=(0, 1, 2))
        with self.assertRaisesRegex(ValueError, "incomplete duration"):
            load_run(str(self.metrics))


if __name__ == "__main__":
    unittest.main()
