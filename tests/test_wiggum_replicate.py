import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import wiggum_replicate as runner


class ReplicateRuntimeTest(unittest.TestCase):
    def test_selected_build_controls_resolution_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binary, library = directory / "skibidy", directory / "libskibidy.so"
            binary.write_bytes(b"executable")
            library.write_bytes(b"selected library")
            with mock.patch.dict(os.environ, {"LD_LIBRARY_PATH": "/other/build"}), \
                 mock.patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                     [], 0, f"libskibidy.so => {library} (0x0)\n", "")) as resolve:
                receipt, env = runner.runtime_identity(binary)
            self.assertEqual(env["LD_LIBRARY_PATH"], str(directory.resolve()) + ":/other/build")
            self.assertEqual(resolve.call_args.kwargs["env"], env)
            self.assertEqual(receipt["dependencies"][0]["sha256"], hashlib.sha256(library.read_bytes()).hexdigest())

    def test_missing_dependency_rejected(self):
        with mock.patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, "libskibidy.so => not found\n", "")):
            with self.assertRaisesRegex(RuntimeError, "unresolved"):
                runner.runtime_identity("build/skibidy")

    def test_config_bytes_and_cwd_restored_on_success_and_failure(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                config = root / "bdm.toml"
                original = b"# bytes\r\n[skin]\r\nheadless = false\r\n"
                config.write_bytes(original)
                previous = Path.cwd()

                def work():
                    config.write_bytes(b"mutated")
                    if fail:
                        raise RuntimeError("simulation failed")

                with mock.patch.object(runner.lib, "ROOT", str(root)), \
                     mock.patch.object(runner, "run_cohorts", side_effect=work):
                    if fail:
                        with self.assertRaisesRegex(RuntimeError, "simulation failed"):
                            runner.main()
                    else:
                        runner.main()
                self.assertEqual(config.read_bytes(), original)
                self.assertEqual(Path.cwd(), previous)

    @unittest.skipUnless(os.environ.get("SKIBIDY_REPLICATE_RUNTIME_TEST") == "1", "opt-in actual loader proof")
    def test_actual_alternate_binary_and_unsupported_condition(self):
        from scripts.study.experiment_evidence import set_parameter
        root = Path(runner.lib.ROOT)
        output = Path(tempfile.mkdtemp(prefix="wiggum-runtime-proof-", dir=root / "output"))
        original = (root / "bdm.toml").read_bytes()
        template = root / "batch/results/baseline-20261007-run2/normal-wound/seed42/bdm.toml"
        selected = root / ".git/baseline-runtime/build"

        def setup(**kwargs):
            target = root / "bdm.toml"
            target.write_bytes(template.read_bytes())
            for key, value in {"skin.duration_days": 0.125, "skin.metrics_interval_h": 0.1,
                               "analysis.condition": "aging", "analysis.profile": "aged"}.items():
                set_parameter(target, key, value)

        argv = ["wiggum_replicate.py", "--n", "2", "--skin", "aging", "--out-dir", str(output),
                "--build-dir", str(selected)]
        with mock.patch.object(runner.lib, "setup_run", side_effect=setup), \
             mock.patch.object(runner.sys, "argv", argv), \
             mock.patch.dict(os.environ, {"LD_DEBUG": "libs"}):
            runner.main()
        self.assertEqual((root / "bdm.toml").read_bytes(), original)
        receipt = json.loads((output / "runtime.json").read_text())
        self.assertTrue(any(Path(item["path"]) == selected / "libskibidy.so" for item in receipt["dependencies"]))
        for seed in (42, 43):
            directory = output / "aging-wound" / f"seed{seed}"
            stderr = (directory / "stderr.log").read_text()
            self.assertIn("calling init: " + str(selected / "libskibidy.so"), stderr)
            self.assertNotIn("unrecognized arguments: --aging", (directory / "validation.txt").read_text())


if __name__ == "__main__":
    unittest.main()
