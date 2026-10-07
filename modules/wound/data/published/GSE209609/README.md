# Measured human wound RNA

[GSE209609](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE209609), from
[the primary publication](https://pubmed.ncbi.nlm.nih.gov/36571451/), contains
96 skin/palate biopsies from 18 healthy adults aged 18–35. Times are baseline,
6 hours and days 1, 3 and 7. Repeated-subject sampling is incomplete.

`sample_expression.csv` preserves 1,632 deposited measurements across 17 genes,
including the actual custom-platform probes, sample IDs, subjects, tissues and
times. `timecourse_summary.csv` reports 170 groups with n, mean and sample SD
in RMA log2 units. Differences from baseline are differences of group means;
they are not paired subject estimates or significance tests.

Skin n is 13, 7, 10, 9 and 6 at the five times. Selected skin baseline differences:

| Gene | Day 1, log2 difference | Day 3 | Day 7 |
|---|---:|---:|---:|
| MMP1 | 7.155 | 6.839 | 4.140 |
| IL1B | 1.444 | 2.262 | 0.681 |
| MKI67 | -0.584 | 1.491 | 1.112 |
| COL1A1 | -0.232 | 0.125 | 1.281 |
| TGFB1 | 1.035 | 0.635 | 0.482 |

These measurements support temporal constraints: early MMP1 induction,
IL1B elevation through day 3, proliferation-associated MKI67 induction at days
3–7, and collagen-I RNA induction by day 7. Bulk RNA does not measure protein
concentration, enzyme activity, collagen mass, cell counts, cycle durations or
membrane integrity. Changing cell composition can also change the bulk signal.
No current parameter or heterogeneity width is calibrated from these data.
Numerical model comparison needs a justified RNA observation model first.

Reproduce from the repository root with `python literature/extract_geo_wound.py
--cache .git/research`. The actual platform is GPL29499, BrainArray Ensembl
custom CDF v22; GPL570 annotations cannot map this processed matrix. Gene
identity lookup URLs and input SHA-256 digests are saved in `provenance.json`.
The extractor does not average probes, interpolate, impute, test hypotheses or
fit parameters.

[Measured time courses](measured_rna_timecourses.png) show six selected genes
with sample SD and both tissues. The [PDF](measured_rna_timecourses.pdf) is
available for export. Rebuild with `python literature/plot_geo_wound.py`.
