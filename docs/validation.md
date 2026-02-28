# Validation

Validation framework documentation lives in [`literature/README.md`](../literature/README.md) to keep the validation suite self-contained and portable.

See also:
- [SOURCES.yaml](../literature/data/SOURCES.yaml) is the structured bibliography with DOI provenance
- [Metrics columns](#metrics-columns) below for CSV output format

## Metrics columns

The CSV written to `output/skibidy/metrics.csv` has 35 columns:

| Column | Units | Description | Non-zero when |
|--------|-------|-------------|---------------|
| `step` | - | Simulation step | always |
| `time_h` | hours | Simulated time (step * dt) | always |
| `time_days` | days | Simulated time in days (time_h / 24) | always |
| `n_agents` | count | Active keratinocyte agents | agents spawned |
| `n_stem` | count | Stem cell agents | agents spawned |
| `n_ta` | count | Transit-amplifying agents (cycling, non-stem) | agents spawned |
| `n_g0` | count | Quiescent (G0) agents | agents spawned |
| `n_basal` | count | Agents in stratum basale | agents spawned |
| `n_spinous` | count | Agents in stratum spinosum | agents spawned |
| `n_granular` | count | Agents in stratum granulosum | agents spawned |
| `n_cornified` | count | Agents in stratum corneum | agents spawned |
| `n_neutrophils` | count | Active neutrophil agents | `[skin.wound] enabled` |
| `n_macrophages` | count | Active macrophage agents | `[skin.wound] enabled` |
| `wound_closure_pct` | % | Fraction of wound voxels with Stratum > 0.5 | `[skin.wound] enabled` |
| `mean_o2_wound` | normalized | Mean O2 in wound cylinder | `[skin.wound] enabled` |
| `mean_ca_wound` | mM | Mean Ca2+ in wound cylinder | `[skin.wound] enabled` |
| `mean_infl_wound` | a.u. | Mean inflammation in wound cylinder | `[skin.wound] enabled` |
| `scar_magnitude` | a.u. | Mean scar field in wound cylinder | `[skin.scar] enabled` |
| `mean_anti_infl_wound` | a.u. | Mean anti-inflammatory in wound | `[skin.inflammation] split_enabled` |
| `n_fibroblasts` | count | Active fibroblast agents (all states) | `[skin.fibroblast] enabled` |
| `n_myofibroblasts` | count | Myofibroblast-state fibroblasts | `[skin.fibroblast] enabled` |
| `mean_tgfb_wound` | a.u. | Mean TGF-beta in wound | `[skin.fibroblast] enabled` |
| `mean_collagen_wound` | a.u. | Mean collagen in wound | `[skin.fibroblast] enabled` |
| `mean_perfusion_wound` | normalized | Mean vascular perfusion in wound dermis | `[skin.wound] enabled` |
| `n_tumor_cells` | count | Active tumor cell agents | `[skin.tumor] enabled` |
| `n_tumor_cycling` | count | Tumor agents not in G0 (Ki-67 proxy) | `[skin.tumor] enabled` |
| `tumor_field_cells` | count | Tumor field voxels > 0.5 (handoff) | `[skin.tumor] enabled` |
| `mean_biofilm_wound` | a.u. | Mean biofilm in wound | `[skin.biofilm] enabled` |
| `mean_vegf_wound` | a.u. | Mean VEGF in wound | `[skin.angiogenesis] enabled` |
| `mean_mmp_wound` | a.u. | Mean MMP in wound | `[skin.mmp] enabled` |
| `mean_fibronectin_wound` | a.u. | Mean fibronectin in wound | `[skin.fibronectin] enabled` |
| `mean_elastin_wound` | a.u. | Mean elastin in wound | `[skin.elastin] enabled` |
| `mean_hyaluronan_wound` | a.u. | Mean hyaluronan in wound | `[skin.hyaluronan] enabled` |
| `mean_dermis_papillary` | normalized | Mean dermis integrity in papillary wound voxels | `[skin.dermis] enabled` |
| `mean_dermis_reticular` | normalized | Mean dermis integrity in reticular wound voxels | `[skin.dermis] enabled` |
| `mean_dermis_hypodermis` | normalized | Mean dermis integrity in hypodermis wound voxels | `[skin.dermis] enabled` |

`scripts/analysis/plot_metrics.py` generates figures from this CSV in `output/plots/`.
