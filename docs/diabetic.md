> [Home](../README.md) / [Docs](README.md) / Diabetic

# Diabetic Wound Healing

Skin BioDynaMo (SkiBiDy) models impaired wound healing in diabetes as a set of compounding dysfunctions across immune, keratinocyte, fibroblast, vascular, and ECM remodeling systems. Enable with `--skin=diabetic --preset=diabetic_wound` or `[skin.diabetic] mode = true`. See also: [Wound Healing](wound-healing.md) | [Parameters](parameters.md) | [Batch & Sweeps](../batch/README.md)

For the full mechanistic model, all scaling factors with literature sources, and coupling details, see the [diabetic module README](../modules/diabetic/README.md).

## Overview

Diabetic wounds heal slowly or fail to heal because multiple biological systems are simultaneously impaired. Rather than modeling this as a single "healing speed" knob, each dysfunction is implemented independently with its own literature-derived scaling factor. The compounding of these factors produces emergent chronic wound behavior.

```bash
./run.sh --skin=diabetic --preset=diabetic_wound   # single diabetic run
./run.sh --compare                                  # normal vs diabetic side-by-side
python3 batch/sweep.py batch/configs/diabetic_factors.toml  # sweep M1 duration factor
```

## Dysfunction summary

Each dysfunction axis targets a specific module. See the [diabetic module README](../modules/diabetic/README.md) for the complete parameter table with DOI-linked sources.

| System | Key factors | Effect |
|--------|------------|--------|
| Immune | M1 duration 3x, resolution 0.3x, neutrophils 1.8x | Sustained inflammation, failed resolution |
| Keratinocyte | Proliferation 0.5x, migration 0.6x | Delayed re-epithelialization |
| Fibroblast | Activation 2x delay, collagen 0.4x, lifespan 0.6x | Impaired ECM repair |
| MMP/TIMP | MMP 3x, TIMP 0.5x | ECM degradation imbalance |
| Vascular | Perfusion 0.7, angio rate 0.002 | Reduced O2/water delivery |
| Chronic inflammation | Baseline 0.001/step | AGE/RAGE prevents full resolution |

## Emergent chronic wound behavior

No single factor is sufficient to produce a chronic wound. The emergent non-healing phenotype arises from their compounding:

```
Hyperglycemia
  |
  +-- Excess neutrophils (1.8x) + delayed apoptosis (1.5x lifespan)
  |     -> Sustained inflammation -> Suppressed proliferation/migration
  |
  +-- Failed M1 to M2 transition (3x M1 duration, 0.3x resolution)
  |     -> Inflammation never resolves -> Wound stuck in inflammatory phase
  |
  +-- Impaired fibroblasts (2x activation delay, 0.4x collagen)
  |     -> Less provisional matrix -> Slower keratinocyte migration
  |
  +-- MMP/TIMP imbalance (3x MMP, 0.5x TIMP)
  |     -> Matrix degraded faster than deposited -> No scaffold
  |
  +-- Microangiopathy (0.7 perfusion, 0.002 angio rate)
  |     -> Less O2/water -> Both gate proliferation and migration
  |
  +-- Baseline inflammation (0.001/step)
        -> Prevents full resolution even when immune cells clear
```

The `--compare` mode runs normal and diabetic simulations back-to-back and generates a side-by-side comparison showing these effects on wound closure, inflammation, and immune cell kinetics.

## Diabetic reference data

The validation suite includes diabetic-specific reference curves derived from literature scaling factors:

| Observable | Normal reference | Diabetic scaling | Source |
|-----------|-----------------|-----------------|--------|
| Wound closure | Eaglstein 1978 | 40 to 60% delayed at day 14 | Galiano 2004, Michaels 2007 |
| Inflammation | Eming 2007 | 2 to 3x peak, 2x duration | Mirza & Koh 2011, Wetzler 2000 |
| Neutrophils | Kim 2008 | 1.5 to 2x peak, delayed clearance | Khanna 2010 |
| Macrophages | Wilgus 2013 | Prolonged M1 plateau | Mirza & Koh 2011 |

Reference curves are in `literature/data/consensus/diabetic_*.csv`.
