# Validation audit

2026-10-07. Validation has both software defects and evidence limitations.
The current screens compare trajectories with qualitative modeling targets.
A mismatch does not establish an error against measured biology.

The audit traced all six shared validation groups, both validation CLIs,
the dashboard computation, publication figures, RA overlays, cohort comparisons,
reference provenance and CSV discovery. It did not re-extract every cited paper
or calibrate physical units. The original code base was
`76e5a6c3a14d672f7e71e916c9f870bebf3edfaa`.

## Confirmed defects and repairs

- Equal weighting of logged samples made scores depend on sampling density.
  RMSE v2 integrates squared residuals over the overlap of the piecewise-linear
  simulation and target curves. Both curves' knots contribute.
- Normalization missed interpolated boundaries. Partial curves were forced to
  their own peak or endpoint while the target retained its full-window scale.
  Both now use the same observed window and target anchor. No extrapolation is
  used. A nonzero normalized trajectory without a scale anchor is untested.
- Publication figures duplicated old scoring, extrapolation and condition rules.
  They now use the shared computation and saved configuration. Diabetic panels
  cannot borrow normal fibroblast, VEGF or fibronectin targets.
- Tumor reporting added occupied binary voxels to active-agent counts.
  Multiple handoffs can occupy the same voxel, so that sum is not a conserved
  cell census. The quantities are separate. Cycling uses active agents as its
  denominator, with an undefined fraction when no active agents remain.
- RA overlays bypassed saved-run integrity and hid enabled zero outputs.
  They now use the shared evaluator. Study-scoped reference CSVs also enter
  the quality checker.
- Fixed normalized plot limits hid collagen excursions many orders above one.
  Large excursions now use a symmetric logarithmic axis. Target legends and
  engineering-screen titles distinguish these plots from measured observations.

The 15% engineering cutoff and simulation parameters were retained.
Reports identify the scoring method, normalization scale, partial coverage,
observable units and the absence of established empirical validation.
Cohort tools reject mixed scoring methods.

## Evidence limitations

[Provenance](../provenance.md) records the source-level findings. Closure mixes
pig partial-thickness data, a human sigmoid fit and a review composite, then
compares that target with modeled voxel occupancy. Collagen mixes synthesis,
estimated deposition, hydroxyproline and tensile-strength proxies.
Diabetic MMP and TGF-beta targets are constructed trajectories. They are not
simple amplitude-scaled normal curves. Burn, pressure, surgical, pH and
rheumatoid targets lack a reproducible numerical extraction and matched cohort
uncertainty.

Peak normalization removes absolute concentration and cell-number differences.
Collagen normalization can amplify relative errors severely near a zero endpoint.
The normal wound seed 42 candidate scores about 244.8 million percent of target
scale for collagen. This is a normalized-shape discrepancy, not a measured
collagen-mass error. Raw final collagen is retained separately.

The non-G0 tumor-agent fraction is a cycling proxy, not a measured Ki-67 index.
The [original Gerdes experiment](https://pubmed.ncbi.nlm.nih.gov/6206131/)
also found Ki-67 in post-mitotic G1, with different behavior during early
G0-to-G1 transition. Source notes now preserve that distinction.
Clinical volume doubling and active-agent doubling are different observables.
The stored tumor linear-growth projection is not consumed by the validator.

Measured human wound RNA, scar, venous-healing and senescence evidence are not
automatically equivalent to the model's protein fields, individual wound closure
or cell census. CSV and citation checks cannot establish those equivalences.

## Frozen-run replay and verification

[Replay JSON](replay.json) and [CSV](replay.csv) retain old and current scores,
input and source hashes, raw final collagen and date coverage. The replay reads
the previous [NO experiment archive](../no-collagen-20261007/evidence.zip)
without modifying it or rerunning simulations.

All 21 runs remain overall failures of the engineering screen. Six observable
labels changed:

| Run | Observable | Previous | Current |
|---|---|---|---|
| Candidate normal full model, seed 43 | Macrophages | fail | pass |
| Candidate normal full model, seed 44 | Macrophages | fail | pass |
| Candidate normal wound, seed 42 | Inflammation | pass | fail |
| Candidate normal wound, seed 43 | pH | pass | fail |
| Control normal wound, seed 42 | Macrophages | fail | pass |
| Control normal wound, seed 43 | Macrophages | fail | pass |

The candidate's near-zero collagen remains in the raw saved metrics. Correcting
validation changes some labels but does not explain away that modeled loss.

Verification includes 81 Python tests with three runtime-dependent skips and
44 literature tests, full and module CLI reports, dashboard
computation equality, generated publication and dashboard plots, and all 43
reference/evidence CSVs including the six rheumatoid targets. Source checks
retain two pre-existing unresolved
citation locators. No C++ simulation code changed in this audit.

Reproduce from the repository root:

```bash
python literature/validation-audit-20261007/replay.py --verify-consumers
```

[Dashboard plot](normal_dashboard.png) and [publication plot](normal_figure.png)
show the current computation. Biological accuracy still requires independent,
condition-matched measurements, a justified observable mapping and uncertainty
appropriate to those measurements.
