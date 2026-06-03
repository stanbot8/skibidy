import tempfile
import unittest
from pathlib import Path
from batch.lib import load_csv, aggregate_csvs


class CsvEvidenceTest(unittest.TestCase):
    def test_reject_corrupt_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.csv"
            for content in ("time_h,x\n0,1\n1,\n", "time_h,x\n0,1\n1\n",
                            "time_h,x\n0,1\x00\n", "time_h,x\n0,NaN\n"):
                path.write_text(content)
                with self.subTest(content=content), self.assertRaises((ValueError, ArithmeticError)):
                    load_csv(path)

    def test_reject_misaligned_or_empty_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.csv", Path(tmp) / "b.csv"
            a.write_text("time_h,x\n0,1\n1,2\n")
            for content in ("time_h,x\n0,1\n", "time_h,x\n0,1\n2,2\n", "time_h,x\n"):
                b.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    aggregate_csvs([a, b])


if __name__ == "__main__":
    unittest.main()
