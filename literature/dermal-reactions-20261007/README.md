# Dermal reaction and immune placement review

The review traced biological screening failures through field producers, fused
reaction dispatch and the actual fibroblast readers. The repair restores existing
mechanisms in their owning tissue compartment. It changes no default parameter
values, reference data, normalization rules or validation thresholds.

## Repairs and biological support

Fibroblasts deposit collagen below z=0, but decorin/tissue TGF-beta clearance,
perfusion washout, lymphatic drainage, MMP reactions and ROS reactions previously
dispatched only in epidermal wound voxels. These local reactions now dispatch in
both layers. Keratinocyte MMP/TIMP production remains epidermal. MMP turnover of
fibronectin, elastin and fibrin also works when fibroblasts are disabled.

Lymphatic density is a diffusing fine-grid field. Its regeneration and drainage
now use the fine voxel index, and regeneration no longer receives structural
coarse-grid weighting. Structural ECM retains its coarse index and weighting.

Immune cells were described as extravasating from wound-bed vasculature, yet both
arrival and recruitment sensing used positive z, where the model initializes no
vascular tissue. They now use negative half-diameter depth. In the baseline mesh
this places macrophage TGF-beta production in the dermal slab that nearby
fibroblasts read. No secretion rate or diffusion coefficient was increased.

Primary experiments support the represented relationships, with specific limits:

- [Yamaguchi et al. 1990](https://pubmed.ncbi.nlm.nih.gov/2374594/) showed
  decorin binding TGF-beta in a cell-system experiment. This supports the feedback
  mechanism, not a human wound clearance coefficient or collagen-as-decorin proxy.
- [Xia et al. 2013](https://onlinelibrary.wiley.com/doi/abs/10.1111/acel.12089)
  demonstrated MMP-1 fragmentation of dermal collagen in human skin organ culture
  and fibroblast collagen lattices. This supports dermal matrix turnover, not the
  model's lumped MMP concentration scale.
- [The 2014 macrophage beta-catenin study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4089463/)
  links wound-bed macrophage migration, fibroblast interaction and TGF-beta1
  production to repair. The model's negative half-diameter placement is a geometric
  implementation choice, not an experimentally measured cell depth.
- [Kataru et al. 2009](https://pubmed.ncbi.nlm.nih.gov/19346498/) supports dermal
  lymphatic clearance and inflammatory resolution in mouse skin. It does not
  identify a TGF-beta-specific drainage rate.

## Reproducible evidence

The [receipt](receipt.json) identifies code and runtime hashes and the
byte-verified [archive](replicate_evidence.zip). The archive retains configurations,
metrics, process logs and individual validation reports for normal, diabetic and
full-model cohorts at seeds 42, 43 and 44. Each code stage uses identical parsed
configurations apart from output directories. The control is the production code
at `7822ee3052db523b8d4eb21ad7bec98fa979bb22`; source patches identify the later stages.
Runtime dependency evidence is `ldd` resolution under the subprocess environment,
not captured process mappings. Executables and libraries remain in local result
storage, while their hashes travel with the evidence.

The fused-operator regressions isolate four TGF-beta sinks, pre-wound and disabled
conditions, bounded removal, fine/coarse meshes, lymphatic regeneration and edema
drainage, matrix degradation, MMP activation/inhibition and independent ROS damage.
The recruitment regression tests actual cell arrival and local fibroblast access
to macrophage TGF-beta. All 171 C++ tests pass locally. The Python suite passes 66
of 69 cases with three opt-in runtime cases skipped; both 22-case literature suites
pass, and all 37 reference CSVs pass data-quality checks. Two previously unresolved
source citations remain warnings.

## Final replicate results

All 27 main simulations completed with finite, structurally valid metrics. Every
run, including all nine final runs, failed at least one biological screen. The
final repair improves some cell and MMP comparisons, but most curve scores worsen.
It establishes corrected spatial behavior, not improved overall biological accuracy.

Selected mean RMSE percentages across the three paired seeds are below; lower is
better. The [complete comparison](comparison.csv) retains every screened quantity.

| Cohort | Quantity | Control | Final |
|---|---|---:|---:|
| Normal wound | Wound closure | 7.00 | 7.37 |
| Normal wound | Macrophages | 16.20 | 14.71 |
| Normal wound | Fibroblasts | 14.68 | 14.04 |
| Normal wound | TGF-beta | 13.34 | 28.83 |
| Diabetic wound | Wound closure | 13.61 | 18.73 |
| Diabetic wound | MMP | 23.34 | 14.22 |
| Full model | Wound closure | 6.93 | 7.55 |
| Full model | Macrophages | 18.23 | 13.85 |
| Full model | Fibroblasts | 11.99 | 11.35 |
| Full model | TGF-beta | 14.07 | 30.17 |

Collagen remains absent or very small in the repaired model. Its mean
end-normalized RMSE rises from 18.67 to approximately 79 million percent in the
normal cohort and from 12.56 to approximately 125 million percent in the full
model. Tiny endpoint denominators amplify those ratios. The
[raw trajectories](trajectories.png) show mean and sample standard deviation
without endpoint normalization, so the underlying loss remains inspectable.

Restoring existing sinks and local immune signaling exposes an unresolved balance
between TGF-beta availability, fibroblast activation and matrix production. The
diagnostics below establish a causal contribution from the sinks in one seed;
they do not identify measured replacement coefficients. Defaults remain unchanged
pending quantitative evidence with tissue, units and experimental conditions
matched to the represented mechanisms.

## Interpreting the intermediate failure

Restoring reactions while retaining epidermal immune placement reduced collagen
to zero in all normal runs and two full-model runs. Full-model seed 43 retained
only `3.64915e-12` at the endpoint, so end normalization inflated its collagen
RMSE to approximately 70 million percent. The unchanged score and raw trajectory
are retained; that ratio does not represent a physical collagen error magnitude.

Three diagnostic ablations of intermediate normal seed 42 isolate the imbalance.
Disabling MMP/ROS collagen loss alone leaves collagen at zero. Disabling the four
TGF-beta sinks restores final collagen to `0.107414`; disabling sinks and loss
restores `0.166213`. Those diagnostic configuration changes are archived separately
and are not new defaults. Initial diagnostics using incorrect configuration paths
were excluded after checking the owning C++ mappings and rerunning valid overrides.

The biological screens remain engineering comparisons against inherited curves
whose patient-level extraction provenance is unestablished. Three stochastic seeds
measure model variability, not clinical uncertainty. Passing a compartment test
does not establish that every biological trajectory is accurate.
