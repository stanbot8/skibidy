# Measured human wound RNA

[GSE209609](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE209609), from
[the primary publication](https://pubmed.ncbi.nlm.nih.gov/36571451/), contains
96 skin/palate biopsies from 18 healthy adults aged 18–35. Times are baseline,
6 hours and days 1, 3 and 7. Repeated-subject sampling is incomplete.

`sample_expression.csv` preserves 1,632 deposited measurements across 17 genes,
including the actual custom-platform probes, sample IDs, subjects, tissues and
times. `timecourse_summary.csv` reports 170 groups with n, mean and sample SD
in RMA log2 units. Differences from baseline are differences of group means.
They are not paired subject estimates or significance tests.

Skin n is 13, 7, 10, 9 and 6 at the five times. Selected skin baseline differences:

| Gene | Day 1, log2 difference | Day 3 | Day 7 |
|---|---:|---:|---:|
| MMP1 | 7.155 | 6.839 | 4.140 |
| IL1B | 1.444 | 2.262 | 0.681 |
| MKI67 | -0.584 | 1.491 | 1.112 |
| COL1A1 | -0.232 | 0.125 | 1.281 |
| TGFB1 | 1.035 | 0.635 | 0.482 |

Group averages suggest early MMP1 induction,
IL1B elevation through day 3, proliferation-associated MKI67 induction at days
3–7, and collagen-I RNA induction by day 7. Bulk RNA does not measure protein
concentration, enzyme activity, collagen mass, cell counts, cycle durations or
membrane integrity. Changing cell composition can also change the bulk signal.
No current parameter or heterogeneity width is calibrated from these data.
Numerical model comparison needs a justified RNA observation model first.

## Matched-subject evidence

[Paired contrasts](paired_changes.csv) preserve 935 baseline-to-post-injury
gene contrasts across 17 genes and 55 subject/tissue/time combinations.
These are repeated measurements, not 935 independent subjects.
[Paired summaries](paired_timecourse_summary.csv) contain 136 groups with
matched and unmatched counts, paired subject IDs, mean, sample SD, range and
individual increase/decrease counts. Empty estimates mean no available pairs.
Sample SD is unavailable with fewer than two pairs.

Skin has 7, 8, 5 and 3 paired subjects at 6 hours and days 1, 3 and 7.
The subsets change across times. The
[primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10006330/) used separate
wounds for each biopsy. A matched contrast compares one person's same-tissue
RNA with their own unwounded sample. It does not follow one wound longitudinally.
The paper's subject-adjusted LIMMA analysis is a different analysis. These
descriptive contrasts do not reproduce its significance tests or adjusted p-values.

| Skin contrast | Pairs | Mean log2 change | Observed range | Increased / decreased |
|---|---:|---:|---:|---:|
| MMP1, day 1 | 8 | 6.933 | 1.725 to 9.260 | 8 / 0 |
| MKI67, day 3 | 5 | 1.493 | 1.085 to 2.056 | 5 / 0 |
| COL1A1, day 7 | 3 | 0.601 | -0.531 to 2.791 | 1 / 2 |
| IL6, day 7 | 3 | 0.462 | 0.158 to 0.626 | 3 / 0 |

The day-7 COL1A1 group-mean difference is 1.281 log2 units, while the matched
mean is 0.601. Only one of three pairs increases. A positive average therefore
cannot justify uniform collagen-I RNA induction across subjects. Early MMP1
and day-3 MKI67 increases are consistent across their available pairs.
These small, incomplete subsets establish neither a population confidence
interval nor a distribution for model parameters.
IL6 illustrates the effect of changing cohorts even on direction. The day-7
unpaired group difference is -0.508 log2 units, while all three available matched
contrasts are positive. Neither statistic can establish the response of the
unmatched subjects or the entire participant population.

[Matched skin plot](paired_rna_changes.png) shows individual points and paired
mean with sample SD. The [PDF](paired_rna_changes.pdf) is available for export.
No lines interpolate missing visits. Input and script hashes, matching method
and assay limits are recorded in [paired provenance](paired_provenance.json).
The CSV checker and plotters verify group and paired summaries against the sample
measurements. Paired input and extractor hashes are also checked, so a
structurally valid but stale or corrupted summary or provenance receipt fails.

Rebuild these additions without network requests:

```bash
python literature/extract_geo_wound.py --paired-only
python literature/plot_geo_wound.py --paired-only
python literature/check_data_quality.py --strict
```

Verification on 2026-10-07: all nine paired-analysis tests and 44 literature
tests passed. Strict checks covered 45 CSVs with no errors or warnings.
The paired plot was regenerated through its source checks and visually reviewed.
The source registry passed with two existing unresolved citation warnings
outside this dataset. The saved sample measurements and original group table
remain unchanged.

Reproduce from the repository root with `python literature/extract_geo_wound.py
--cache .git/research`. The actual platform is GPL29499, BrainArray Ensembl
custom CDF v22. GPL570 annotations cannot map this processed matrix. Gene
identity lookup URLs and input SHA-256 digests are saved in `provenance.json`.
The extractor does not average probes, interpolate, impute, test hypotheses or
fit parameters.

[Measured time courses](measured_rna_timecourses.png) show six selected genes
with sample SD and both tissues. The [PDF](measured_rna_timecourses.pdf) is
available for export. Rebuild with `python literature/plot_geo_wound.py`.
