> [Home](../../README.md) / [Modules](../../README.md#modules) / MMP

# MMP

Matrix metalloproteinase dynamics mediating extracellular matrix remodeling during wound healing.

## Biology

Matrix metalloproteinases (MMPs) are zinc-dependent endopeptidases that degrade extracellular matrix components. During wound healing, M1 macrophages produce MMP-9 (gelatinase B) for debris clearance, while fibroblasts produce MMP-1 (interstitial collagenase) and MMP-3 (stromelysin) for ECM remodeling. MMPs degrade collagen, fibronectin, dermis, and elastin. Tissue inhibitors of metalloproteinases (TIMPs) provide natural negative regulation.

[Lobmann et al. 2002](https://doi.org/10.1007/s00125-002-0868-8) measured proteins in chronic diabetic ulcer biopsies compared with acute traumatic wounds. MMP-1 was 65-fold higher, MMP-9 14-fold higher, pro-MMP-2 threefold higher, active MMP-2 sixfold higher and MMP-8 twofold higher. TIMP-2 was reduced by half. These isoform-specific concentrations support a protease/inhibitor imbalance. They do not measure per-cell production rates or justify one threefold multiplier for all MMPs, a TIMP-1 production factor or halving a decay constant.

## Model

Separate active MMP, inactive pro-MMP and TIMP fields represent coarse protease and inhibitor pools. MMP diffusion is 0.02 and residual non-TIMP decay is 0.015. TIMP inhibition is explicit second-order neutralization, capped by the smaller pool and removing equal model amounts of MMP and TIMP. The model does not resolve MMP isoforms, inhibitor complexes or measured molar stoichiometry.

Immune cells and fibroblasts supply pro-MMP through their configured production rates. Basal and autocatalytic activation transfers pro-MMP into the active pool. Fibroblasts, M2 macrophages and wound-edge keratinocytes supply TIMP. Diabetic production modifiers remain phenomenological assumptions. Background degradation of each field is distinct from TIMP neutralization.

Degradation targets (applied in FusedWoundPostOp, capped by available substrate):
- Collagen: `collagen -= collagen_degradation * local_mmp` per step
- Fibronectin: `fibronectin -= fibronectin_degradation * local_mmp` per step
- Dermis: `dermis -= dermis_mmp_degradation * local_mmp` per step (from dermis module)
- Elastin: `elastin -= elastin_mmp_degradation * local_mmp` per step (from elastin module)

Local pH and temperature modify effective MMP activity. AGE accumulation can reduce collagen susceptibility. Fibrin degradation and matrix-fragment feedback are also processed by the post hook. These pooled kinetics do not constitute isoform-specific enzyme fits.

## Parameters

From modules/mmp/config.toml:

| Parameter | Default | Units | Description | Source |
|-----------|---------|-------|-------------|--------|
| `enabled` | true | bool | Master switch | Convention |
| `diffusion` | 0.02 | - | MMP diffusion coefficient | Assumed |
| `residual_decay` | 0.015 | per model time | Non-TIMP MMP loss | Assumed |
| `m1_rate` | 0.003 | per step | Pro-MMP source per M1 macrophage | Assumed |
| `fibroblast_rate` | 0.0002 | per step | Pro-MMP source per fibroblast | Assumed |
| `collagen_degradation` | 0.002 | per step | MMP-mediated collagen loss | Assumed |
| `fibronectin_degradation` | 0.008 | per step | MMP-mediated fibronectin loss | Assumed |

Additional pro-MMP and TIMP defaults are listed in [config.toml](config.toml). The literature motivates mechanisms and comparisons, without deriving these numerical rates.

## Coupling

### Reads
| Field | Source module | How used |
|-------|-------------|----------|
| Pro-MMP, TIMP | mmp | Zymogen activation and inhibitor neutralization |
| Collagen, fibronectin, dermis, elastin, fibrin | matrix modules | Available degradation substrates |
| pH, temperature, AGE | ph, temperature, diabetic | Effective activity and collagen resistance |

### Writes
| Field | Consumer modules | What is written |
|-------|-----------------|-----------------|
| MMP | collagen (degradation), fibronectin (degradation), dermis (degradation), elastin (degradation) | Active protease from zymogen activation and matrix-fragment feedback |
| Pro-MMP, TIMP | mmp | Production, activation and neutralization |
| Matrix substrates | matrix modules | Proteolytic loss |

## Validation

| Dataset | Observable | Sources | Notes |
|---------|-----------|--------|-------|
| `mmp_ecm_remodeling` | MMP levels, collagen/fibronectin degradation | Lobmann 2002, Nagase 1999, Ladwig 2002 | Biological rationale and diabetic imbalance, not numerical parameter derivation |

An [isolated collagen-breakdown diagnostic](../../literature/no-collagen-20261007/README.md#mmp-diagnostic)
preserves substantially more wound collagen in three normal-wound seeds when
only the collagen degradation coefficient is set to zero. This identifies
the modeled sink as a major contributor to near-zero collagen output; it does
not validate disabling remodeling or determine replacement kinetics. The
production coefficient is unchanged, and all diagnostic runs still fail
biological validation.

## Literature data

Reference curves for validation (full citations in [SOURCES.yaml](SOURCES.yaml)):

| Dataset | File | Normalization |
|---------|------|---------------|
| MMP kinetics | [mmp_kinetics.csv](data/mmp_kinetics.csv) | Peak = 1.0 |

## Metrics

| Column | Units | Description |
|--------|-------|-------------|
| `mean_mmp_wound` | a.u. | Mean MMP in wound |

## Source files

| File | Purpose |
|------|---------|
| `mmp_pde.h` | Active MMP field with residual non-TIMP loss |
| `prommp_pde.h`, `timp_pde.h` | Zymogen and inhibitor fields |
| `post_hook.h` | Activation, inhibition and matrix degradation |
| `config.toml` | Module configuration |
