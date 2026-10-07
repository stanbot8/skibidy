# Biological variation

Skibidy already uses random phase transitions, stem/TA decisions and division
directions. These random events differ from a persistent biological difference
between cells. Optional keratinocyte variation adds a duration multiplier to
each cell's G1, S, G2 and M transition denominators. A cell retains its multiplier
for its lifetime. Each newly divided daughter samples independently. Its mother
keeps her existing value. Field-created cells initialize once at bootstrap and
other cells initialize on their first cycling step. Changes to configuration do
not resample existing cells.

The default is `fixed` with zero spread. It draws no additional random numbers
and leaves the calibrated duration parameters unchanged. To run an explicitly
exploratory comparison, add this section to the merged configuration:

```toml
[skin.heterogeneity]
cycle_distribution = "lognormal"
cycle_cv = 0.2 # sensitivity assumption, not a measured human wound CV
```

`lognormal` has positive support, arithmetic mean multiplier 1 and coefficient
of variation `cycle_cv`, which must be finite and between 0 and 1. Its log-space
variance is `log(1 + cycle_cv^2)` and log-space mean is minus half that variance.
`normal` samples a standard normal conditioned on the interval [-3,3], then
returns `1 + cycle_cv * z`. Its mean is also 1. Its actual CV is slightly smaller
than the requested underlying normal CV because the tails are removed. The
normal setting permits CV values up to 0.3 so every multiplier stays positive.
Zero width in either mode behaves exactly like `fixed`. Fixed mode requires
zero width. Invalid types, distributions and nonfinite or out-of-range widths
stop configuration loading or validation.

The sampled multiplier is a phase-duration propensity, not a directly sampled
total cycle time. Actual cycle times still depend on the existing random phase
transitions, growth, contact inhibition and local fields. Mean multiplier 1
therefore does not guarantee an unchanged mean wound closure time. A stable
trait and independent daughters are modeling assumptions, not a fitted lineage
correlation model. The continuum basal-density equation and other agent types
retain their existing kinetics. This option affects explicit keratinocytes only.

Downloaded primary numerical supplements are preserved unchanged in
[`modules/tissue/data`](../modules/tissue/data/README.md), with URLs, checksums,
source cells and a reproducible extraction. The following are descriptive
statistics of recorded complete cycles, not configuration recommendations.
CV is sample SD divided by arithmetic mean.

| Adult human culture group | Complete cycles | Colonies with cycles | Mean / median (hours) | SD (hours) | Observed CV |
|---|---:|---:|---:|---:|---:|
| Xiao 2024 expanding, classified daughter fates | 1017 | 13 | 20.60 / 19.00 | 6.90 | 0.335 |
| Xiao 2024 differentiating, classified daughter fates | 174 | 35 | 33.99 / 30.50 | 14.33 | 0.421 |
| Roshan 2016 balanced | 497 | 32 | 17.15 / 15.67 | 7.00 | 0.408 |
| Roshan 2016 expanding | 465 | 6 | 14.87 / 14.50 | 4.14 | 0.279 |

[Xiao et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10935907/) followed primary
adult cultures from three donors, imaging every 20 minutes over 11–16 days.
The classified subset has numeric durations after the founder generation and
PP/PD/DP/DD daughter fates. It reproduces the reported group counts. Its DIF
median is 30.5 hours versus 30 in the paper. There are 1903/221 positive recorded
post-founder intervals in the source, including unknown and other fate labels.
These are retained for audit without assuming every interval is a completed cycle.
Cells untrackable for 48 hours were
classified unknown. Nondivision for 48 hours was used to classify differentiation.
Related cells, tracking loss and preferentially observed completed cycles limit
inference. Expanding colonies suggest stem potential but are not purified stem
cells, and active cycle lengths do not measure time spent quiescent in G0.

[Roshan et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4872834/) measured adult
and neonatal cultures and showed proliferation modes can change with confluence
and scratch repair. The adult rows above use the two adult supplement sheets.
The paper reports 2127 post-plating neonatal cycles across 81 colonies. That
workbook also has subclone generation resets and `Outer` labels. The extraction
does not reconstruct the complete published neonatal cohort and excludes its
expanding sheet from fits. Repeated timestamps cannot establish duplicate cell
identity. Neither adult colony mode identifies a permanent stem/TA trait.

For the four adult groups, marginal normal/lognormal/gamma fits favor positive
skewed families over an unrestricted Gaussian by descriptive AIC. Lognormal
has the lowest AIC in both Xiao groups and Roshan balanced. Gamma is slightly
lower in Roshan expanding. This supports investigating a positive skewed model,
not a universal family or a measured persistent-trait CV. These fits ignore
lineage dependence and censoring and are not significance tests. Observed CV
also includes stochastic cycle progression already present in Skibidy.

[Piedrafita et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7080751/)
inferred gamma-distributed cycle times in mouse homeostatic epithelia from
H2B-GFP dilution. The downloaded Data2 workbook contains 50527 fluorescence
measurements across 27 chase-time columns, not directly observed cycle intervals.
It is inventoried by tissue, time and mouse ID rather than fitted as human
durations. No empirical widths, means or repair coefficients are transferred.

Use distinct replicate seeds, record the merged configuration and thread count,
and compare each spread with a zero-spread cohort. Reproduction requires the same
runtime, seed, scheduling and thread count. Do not call these runs additional
clinical validation or vary means to compensate for a spread-dependent outcome.

The C++ heterogeneity tests cover zero-width random-stream preservation, seeded
replay, persistent traits, independent daughters, positive support, population
moments, the actual S-phase transition and invalid configuration rejection.
