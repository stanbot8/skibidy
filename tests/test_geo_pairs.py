"""Verify donor matching and derived RNA evidence against known contrasts."""
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

from literature.extract_geo_wound import paired_changes, group_summaries, write_paired_outputs
from literature.check_data_quality import check_csv


def observation(subject, day, value, sample, tissue="skin", probe="ENSG1_at"):
    return dict(gene="COL1A1", probe=probe, subject=subject, tissue=tissue,
                sample=f"GSM{sample}", day=day, rma_log2_expression=value)


class PairedRnaTest(unittest.TestCase):
    def save_rows(self, path, rows):
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def setUp(self):
        self.rows = [observation("A", 0, 10, 1), observation("A", 7, 12, 2),
                     observation("B", 0, 20, 3), observation("B", 7, 18, 4),
                     observation("C", 7, 100, 5)]

    def test_changing_cohort_mean_does_not_become_a_paired_effect(self):
        pairs, summaries = paired_changes(self.rows)
        self.assertEqual([r["delta_log2"] for r in pairs], [2, -2])
        summary = summaries[0]
        self.assertEqual(summary["mean_delta_log2"], 0)
        self.assertAlmostEqual(summary["sample_sd_delta_log2"], math.sqrt(8))
        self.assertAlmostEqual(summary["unpaired_group_delta_log2"], 85 / 3)
        self.assertEqual((summary["n_pairs"], summary["n_unpaired"], summary["paired_subjects"]), (2, 1, "A;B"))
        self.assertEqual((summary["n_increased"], summary["n_decreased"]), (1, 1))

    def test_tissue_and_probe_baselines_cannot_be_borrowed(self):
        pairs, summaries = paired_changes([
            observation("A", 0, 10, 1, tissue="palate"),
            observation("A", 0, 20, 2, probe="ENSG2_at"),
            observation("A", 7, 12, 3)])
        self.assertEqual(pairs, [])
        self.assertEqual(summaries[0]["n_pairs"], 0)
        self.assertEqual(summaries[0]["mean_delta_log2"], "")
        self.assertEqual(summaries[0]["sample_sd_delta_log2"], "")

    def test_one_pair_has_no_estimated_sample_sd(self):
        _, summaries = paired_changes(self.rows[:2])
        self.assertEqual(summaries[0]["mean_delta_log2"], 2)
        self.assertEqual(summaries[0]["sample_sd_delta_log2"], "")

    def test_duplicate_and_inconsistent_samples_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            paired_changes(self.rows + [dict(self.rows[0], sample="GSM99")])
        with self.assertRaisesRegex(ValueError, "Inconsistent"):
            paired_changes(self.rows + [observation("D", 3, 7, 1)])
        with self.assertRaisesRegex(ValueError, "Invalid"):
            paired_changes([dict(self.rows[0], rma_log2_expression=float("nan"))])

    def test_actual_checker_rejects_self_consistent_but_false_and_stale_data(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            source = dest / "sample_expression.csv"
            with source.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
                writer.writeheader()
                writer.writerows(self.rows)
            write_paired_outputs(dest)
            path = dest / "paired_changes.csv"
            self.assertEqual(check_csv(str(path), {}, False)[0], [])
            with path.open(newline="") as stream:
                records = list(csv.DictReader(stream))
            records[0]["post_log2"] = "13"
            records[0]["delta_log2"] = "3"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
            self.assertTrue(check_csv(str(path), {}, False)[0])
            summary = dest / "paired_timecourse_summary.csv"
            # Change a recorded baseline directly, without rebuilding derived summaries.
            with source.open(newline="") as stream:
                changed = list(csv.DictReader(stream))
            changed[0]["rma_log2_expression"] = "9"
            with source.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(changed[0]))
                writer.writeheader()
                writer.writerows(changed)
            self.assertTrue(check_csv(str(summary), {}, False)[0])

    def test_no_matched_subjects_is_a_valid_empty_pair_table(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            rows = [observation("A", 0, 10, 1, tissue="palate"),
                    observation("A", 7, 12, 2)]
            self.save_rows(dest / "sample_expression.csv", rows)
            write_paired_outputs(dest)
            for name in ("paired_changes.csv", "paired_timecourse_summary.csv"):
                self.assertEqual(check_csv(str(dest / name), {}, False)[0], [])

    def test_provenance_hash_and_group_mean_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            self.save_rows(dest / "sample_expression.csv", self.rows)
            write_paired_outputs(dest)
            receipt_path = dest / "paired_provenance.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["script_sha256"] = "stale"
            receipt_path.write_text(json.dumps(receipt))
            errors = check_csv(str(dest / "paired_changes.csv"), {}, False)[0]
            self.assertTrue(any("stale paired provenance" in e for e in errors))
            groups = group_summaries(self.rows)
            self.assertAlmostEqual(groups[-1]["mean_log2"], 130 / 3)
            self.assertAlmostEqual(groups[-1]["log2_difference_from_group_baseline"], 85 / 3)
            path = dest / "timecourse_summary.csv"
            self.save_rows(path, groups)
            self.assertEqual(check_csv(str(path), {}, False)[0], [])
            groups[-1]["mean_log2"] += 1
            groups[-1]["log2_difference_from_group_baseline"] += 1
            self.save_rows(path, groups)
            self.assertTrue(check_csv(str(path), {}, False)[0])

    def test_sample_consumer_rejects_equivalent_time_duplicates_and_unrecorded_dates(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample_expression.csv"
            rows = [observation("A", 7, 12, 1), observation("A", "7.0", 13, 2)]
            self.save_rows(path, rows)
            self.assertTrue(any("Duplicate" in e for e in check_csv(str(path), {}, False)[0]))
            self.save_rows(path, [observation("A", 2, 12, 1)])
            self.assertTrue(check_csv(str(path), {}, False)[0])

    def test_stored_day7_collagen_mean_does_not_imply_uniform_induction(self):
        data = Path(__file__).resolve().parents[1] / "modules/wound/data/published/GSE209609"
        with (data / "sample_expression.csv").open(newline="") as stream:
            pairs, summaries = paired_changes(list(csv.DictReader(stream)))
        self.assertEqual((len(pairs), len(summaries)), (935, 136))
        summary = next(r for r in summaries if (r["gene"], r["tissue"], r["day"]) == ("COL1A1", "skin", 7))
        self.assertEqual((summary["n_pairs"], summary["n_increased"], summary["n_decreased"]), (3, 1, 2))
        self.assertAlmostEqual(summary["mean_delta_log2"], .6006070786666667)
        il6 = next(r for r in summaries if (r["gene"], r["tissue"], r["day"]) == ("IL6", "skin", 7))
        self.assertEqual((il6["n_pairs"], il6["n_increased"]), (3, 3))
        self.assertLess(il6["unpaired_group_delta_log2"], 0)
        self.assertAlmostEqual(il6["mean_delta_log2"], .4620400253333335)


if __name__ == "__main__":
    unittest.main()
