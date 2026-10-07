"""User studies must reach actual batch consumers with inspectable evidence.

Set SKIBIDY_RUNTIME_TEST=1 in a sourced BioDynaMo shell for the real API cohort.
"""
import contextlib
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request

from batch import lib
from batch import batch as runner
from scripts import dashboard


class DashboardBatchTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="skibidy-user-study-test-")
        self.users = Path(self.temporary.name) / "users"
        self.patches = contextlib.ExitStack()
        self.patches.enter_context(patch.dict(os.environ, {"SKIBIDY_USER_STUDIES": str(self.users)}))
        self.patches.enter_context(patch.object(dashboard, "USER_STUDIES_DIR", str(self.users)))

    def tearDown(self):
        self.patches.close()
        path = self.temporary.name
        self.temporary.cleanup()
        self.assertFalse(Path(path).exists())

    def create(self):
        result = dashboard.create_study("api-test", .5, "diabetic", [], 'A "quote"\nC:\\data')
        self.assertTrue(result["ok"], result)
        return self.users / result["study"]

    def test_invalid_study_has_no_directory(self):
        for duration, profile, modules in ((float("nan"), "", []), (-1, "", []),
                                            (.5, "missing", []), (.5, "", ["missing"])):
            self.assertFalse(dashboard.create_study("bad", duration, profile, modules)["ok"])
            self.assertFalse(self.users.exists())

    def test_profile_and_escaped_text_roundtrip(self):
        study = self.create()
        self.assertEqual(str(study), lib.resolve_study("api-test"))
        meta = lib.parse_toml(study / "api-test.skibidy")["project"]
        self.assertEqual('A "quote"\nC:\\data', meta["description"])
        self.assertEqual("diabetic", lib.study_profile("api-test"))
        self.assertEqual(.5, lib.parse_toml(study / "preset.toml")["skin"]["duration_days"])
        private_root = Path(self.temporary.name) / "profile-config"
        private_root.mkdir()
        (private_root / "bdm.toml").write_text("[skin]\nduration_days=1\n")
        with patch.object(lib, "ROOT", str(private_root)), \
                patch.object(lib, "merge_config"), patch.object(lib, "apply_profile") as profile, \
                patch.object(lib, "apply_study"), patch.object(lib, "override_param"):
            lib.setup_run(study="api-test")
            profile.assert_called_once_with("diabetic")

    def test_experiment_and_treatment_roundtrip(self):
        study = self.create()
        name, description, label = 'quoted "experiment"', 'line\n"text"', 'a"b\\c'
        result = dashboard.create_experiment("api-test", name, description, "", 2,
                                            [{"label": label, "overrides": {"skin.headless": True}}])
        self.assertTrue(result["ok"], result)
        experiment = lib.parse_toml(study / "experiments" / (result["name"] + ".toml"))["experiment"]
        self.assertEqual((name, description, label),
                         (experiment["name"], experiment["description"], experiment["configs"][0]["label"]))
        self.assertIs(True, experiment["configs"][0]["overrides"]["skin.headless"])
        self.assertFalse(dashboard.create_experiment("api-test", "bad", "", "", 1.5, [{}])["ok"])
        self.assertFalse((study / "experiments" / "bad.toml").exists())
        self.assertFalse(dashboard.create_treatment("api-test", "bad", "[skin\n")["ok"])
        self.assertFalse((study / "treatments" / "bad.toml").exists())
        result = dashboard.create_treatment("api-test", "local", "[skin]\nwater_recovery_rate=0.1\n")
        self.assertTrue(result["ok"], result)
        with patch.object(lib, "apply_overlay") as overlay:
            lib.apply_treatment("local", "api-test")
            overlay.assert_called_once_with(str(study / "treatments" / "local.toml"))

    def run_fake_cohort(self, failed=False, validation_rc=0):
        study = self.create()
        fake_root = Path(self.temporary.name) / "engine"
        fake_root.mkdir()
        (fake_root / "bdm.toml").write_text("[simulation]\nrandom_seed=0\n[skin]\nduration_days=1\n")
        results = study / "results"
        (results / "consensus.csv").write_text("old evidence\n")
        calls = []

        def simulate(output_path):
            path = Path(output_path)
            (path / "skibidy").mkdir(parents=True)
            shutil.copyfile(fake_root / "bdm.toml", path / "run-config.toml")
            metrics = path / "skibidy" / "metrics.csv"
            metrics.write_text("time_h,n_agents\n0,10\n24,12\n")
            lib._last_output[0] = str(metrics.parent)
            ok = not failed or not calls
            calls.append(output_path)
            lib._last_result.update(success=ok, error="" if ok else "process failed", returncode=0 if ok else 3,
                                    config_sha256=lib.file_sha256(path / "run-config.toml"),
                                    metrics_sha256=lib.file_sha256(metrics))
            return ok, .1

        with patch.object(lib, "ROOT", str(fake_root)), patch.object(lib, "setup_run"), \
                patch.object(lib, "build_if_needed"), patch.object(lib, "run_simulation", side_effect=simulate), \
                patch.object(lib, "run_validation", return_value=validation_rc), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = runner.main(["--study", "api-test", "--seed", "71", "-n", "2", "--validate"])
        return rc, results

    def test_failed_process_cannot_publish_consensus_even_with_complete_csv(self):
        rc, results = self.run_fake_cohort(failed=True)
        self.assertEqual(1, rc)
        self.assertFalse((results / "consensus.csv").exists())
        self.assertFalse((results / "metrics.csv").exists())
        self.assertEqual("old evidence\n", next((results / "archive").glob("*/consensus.csv")).read_text())
        cohort = json.loads((results / "cohort.json").read_text())
        self.assertEqual("failed", cohort["status"])
        self.assertEqual([71, 72], [r["seed"] for r in cohort["runs"]])
        self.assertEqual(["ok", "failed"], [r["status"] for r in cohort["runs"]])
        self.assertEqual(3, cohort["runs"][1]["returncode"])
        self.assertTrue(all(r["config_sha256"] and r["metrics_sha256"] for r in cohort["runs"]))

    def test_validation_returncode_propagates(self):
        rc, results = self.run_fake_cohort(validation_rc=7)
        self.assertEqual(7, rc)
        cohort = json.loads((results / "cohort.json").read_text())
        self.assertEqual(7, cohort["validation_returncode"])
        self.assertEqual("complete", cohort["status"])
        self.assertTrue((results / "consensus.csv").is_file())

    def test_nonpositive_cohort_is_rejected_before_writes(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            runner.main(["-n", "0"])
        self.assertFalse(self.users.exists())

    def test_overlay_uses_running_python(self):
        with patch.object(lib.subprocess, "run") as run:
            run.return_value.returncode = 0
            lib.merge_config()
            lib.apply_overlay("test.toml")
            self.assertTrue(all(call.args[0][0] == sys.executable for call in run.call_args_list))

    def test_unicode_metadata_is_valid_toml(self):
        description = "Unicode \U0001f9ec cell"
        self.assertTrue(dashboard.create_study("unicode", .5, "", [], description)["ok"])
        meta = lib.parse_toml(self.users / "unicode" / "unicode.skibidy")["project"]
        self.assertEqual(description, meta["description"])

    def test_saved_condition_metadata_reaches_validation(self):
        from literature.lib import condition_from_config
        private_root = Path(self.temporary.name) / "metadata"
        private_root.mkdir()
        config_path = private_root / "bdm.toml"
        for profile, expected in (("venous", "venous"), ("aged", "aging"),
                                  ("keloid", "keloid"), ("surgical", "surgical"),
                                  ("aged_diabetic", "diabetic")):
            config_path.write_text("[skin]\nduration_days=1\n")
            with patch.object(lib, "ROOT", str(private_root)), patch.object(lib, "merge_config"), \
                    patch.object(lib, "apply_profile"):
                lib.setup_run(skin=profile)
            config = lib.parse_toml(config_path)
            self.assertEqual(profile, config["analysis"]["profile"])
            self.assertEqual(expected, condition_from_config(config))

    @unittest.skipUnless(os.environ.get("SKIBIDY_RUNTIME_TEST") == "1", "requires activated production binary")
    def test_actual_dashboard_api_two_run_cohort(self):
        from scripts.validation.checkpoint_regression import CONFIG
        config_path = Path(lib.ROOT) / "bdm.toml"
        original = config_path.read_bytes() if config_path.exists() else None
        self.patches.enter_context(patch.object(dashboard, "_run_state", {"proc": None, "log": ""}))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), dashboard.DashHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)

        def request(path, data=None):
            req = urllib.request.Request(base + path,
                                         data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.load(response)

        try:
            created = request("/api/create-study", {"name": "api-runtime", "duration": .5,
                              "profile": "diabetic", "modules": [], "description": 'Real "cohort"'})
            self.assertTrue(created["ok"], created)
            study = self.users / "api-runtime"
            (study / "preset.toml").write_text(CONFIG)
            self.assertTrue(request("/api/run?study=api-runtime&n=2")["ok"])
            deadline = time.monotonic() + 180
            while True:
                status = request("/api/run/status")
                if not status["running"]:
                    break
                if time.monotonic() > deadline:
                    self.fail("Actual dashboard batch timed out")
                time.sleep(.2)
            self.assertEqual(0, status["returncode"], status["log"])
            results = study / "results"
            cohort = json.loads((results / "cohort.json").read_text())
            self.assertEqual(("complete", 2, "diabetic"),
                             (cohort["status"], len(cohort["runs"]), cohort["profile"]))
            self.assertEqual(2, len({r["seed"] for r in cohort["runs"]}))
            for record in cohort["runs"]:
                raw = results / "raw" / f"run_{record['run']:03d}"
                cfg = lib.parse_toml(raw / "run-config.toml")
                self.assertTrue(cfg["skin"]["diabetic"]["mode"])
                self.assertEqual({"profile": "diabetic", "condition": "diabetic"}, cfg["analysis"])
                self.assertEqual(record["seed"], cfg["simulation"]["random_seed"])
                self.assertEqual(record["config_sha256"], lib.file_sha256(raw / "run-config.toml"))
                self.assertEqual(record["metrics_sha256"], lib.file_sha256(raw / "skibidy" / "metrics.csv"))
                lib.validate_run_metrics(raw / "skibidy" / "metrics.csv", cfg)
            self.assertTrue(request("/api/results?study=api-runtime"))
            if original is None:
                self.assertFalse(config_path.exists())
            else:
                self.assertEqual(original, config_path.read_bytes())
            evidence = os.environ.get("SKIBIDY_DASHBOARD_TEST_EVIDENCE")
            if evidence:
                target = Path(evidence)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copytree(results, target / "results")
                self.temporary.cleanup()
                self.assertFalse(Path(self.temporary.name).exists())
                (target / "report.json").write_text(json.dumps({"status": "passed", "runs": 2,
                    "profile": "diabetic", "config_restored": True, "temporary_study_cleanup": True,
                    "metrics_sha256": cohort["metrics_sha256"], "consensus_sha256": cohort["consensus_sha256"]}, indent=2))
        finally:
            proc = dashboard._run_state["proc"]
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            if original is None:
                config_path.unlink(missing_ok=True)
            else:
                config_path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
