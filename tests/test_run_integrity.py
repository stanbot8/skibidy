"""Failure cases that must never become completed biological runs."""
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from batch import lib
from batch.lib import validate_run_metrics, simulation_environment


class RunIntegrityTest(unittest.TestCase):
    def test_ordinary_environment_removes_all_checkpoint_controls(self):
        controls = {name: "sentinel" for name in (
            "SKIBIDY_CKPT_SAVE_DIR", "SKIBIDY_CKPT_LOAD_DIR", "SKIBIDY_CKPT_STEP",
            "SKIBIDY_CHECKPOINT_LEGACY", "SKIBIDY_STATE_SIGNATURE_FILE")}
        controls.update(OMP_NUM_THREADS="1", LD_LIBRARY_PATH="libraries")
        self.assertEqual(simulation_environment(controls),
                         {"OMP_NUM_THREADS": "1", "LD_LIBRARY_PATH": "libraries"})
        self.assertIn("SKIBIDY_CKPT_STEP", controls)

    @unittest.skipUnless(os.environ.get("SKIBIDY_RUNTIME_TEST") == "1", "requires BioDynaMo")
    def test_batch_and_replicate_loader_ignore_inherited_checkpoint_controls(self):
        from scripts.run_replicates import runtime_identity
        from scripts.config.merge_config import merge
        root = Path(lib.ROOT)
        with tempfile.TemporaryDirectory(prefix="skibidy-checkpoint-isolation-") as directory:
            private = Path(directory)
            (private / "build").symlink_to(root / "build", target_is_directory=True)
            merge(str(root / "bdm.core.toml"), str(root / "modules"),
                  str(private / "bdm.toml"))
            save_dir, witness = private / "checkpoint", private / "witness.json"
            controls = {"SKIBIDY_CKPT_SAVE_DIR": str(save_dir),
                        "SKIBIDY_CKPT_LOAD_DIR": str(private / "missing-checkpoint"),
                        "SKIBIDY_CKPT_STEP": "1", "SKIBIDY_STATE_SIGNATURE_FILE": str(witness)}
            with patch.dict(os.environ, controls), patch.object(lib, "ROOT", str(private)):
                for name, value in (("skin.duration_days", .1), ("skin.metrics_interval_h", .1),
                                    ("skin.metrics_autoopen", False)):
                    lib.override_param(name, value)
                _, env = runtime_identity(private / "build/skibidy")
                self.assertTrue(all(name not in env for name in controls))
                ok, _ = lib.run_simulation(output_path=str(private / "run"))
                self.assertTrue(ok, lib._last_result)
                self.assertFalse(save_dir.exists())
                self.assertFalse(witness.exists())

    def check_csv(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.csv"
            path.write_text(text)
            return validate_run_metrics(path, {"skin": {
                "duration_days": 1, "metrics_interval_h": 2}})

    def test_complete(self):
        self.assertEqual((3, 24), self.check_csv(
            "time_h,n_agents\n0,10\n12,11\n24,12\n"))

    def test_failed_outputs(self):
        for text in ("time_h,n_agents\n", "time_h,n_agents\n0,10\n12,11\n",
                     "time_h,n_agents\n0,10\n24,nan\n",
                     "time_h,n_agents\n0,10\n24\n",
                     "time_h,n_agents\n24,10\n24,11\n",
                     "time_h,n_agents\n0,10\n48,11\n",
                     "time_h,n_agents\n0,10\n24,11,12\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check_csv(text)


if __name__ == "__main__":
    unittest.main()
