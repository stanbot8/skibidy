"""Failure cases that must never become completed biological runs."""
import tempfile
import unittest
from pathlib import Path

from batch.lib import validate_run_metrics


class RunIntegrityTest(unittest.TestCase):
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
