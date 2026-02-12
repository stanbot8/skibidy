> [Home](../README.md) / Modules

# Skibidy Modules

Each module directory contains a `config.toml` and a `README.md` documenting the biological mechanism, computational model, parameters with literature sources, cross-module coupling, and validation datasets.

## Core

| Module | Biology | Fields |
|--------|---------|--------|
| [tissue](tissue/README.md) | Epidermal homeostasis, cell cycle, calcium-driven differentiation | Calcium, KGF, O2, Water, Stratum |

## Wound healing cascade

| Module | Biology | Fields |
|--------|---------|--------|
| [wound](wound/README.md) | Punch biopsy event, margin cell spawning | Stratum (zeros) |
| [inflammation](inflammation/README.md) | Cytokine signaling, Hill-function gating | Inflammation, ImmunePressure |
| [immune](immune/README.md) | Neutrophils, macrophages, M1/M2 polarization | (agents) |
| [fibroblast](fibroblast/README.md) | TGF-beta cascade, myofibroblast differentiation, collagen deposition | TGF-beta, Collagen |
| [mmp](mmp/README.md) | Matrix metalloproteinase ECM remodeling | MMP |
| [fibronectin](fibronectin/README.md) | Provisional matrix scaffold for migration | Fibronectin |
| [scar](scar/README.md) | Emergent scar formation from collagen | Scar |
| [perfusion](perfusion/README.md) | Vascular perfusion, angiogenesis recovery | Vascular |
| [angiogenesis](angiogenesis/README.md) | VEGF-driven vessel sprouting | VEGF |
| [dermis](dermis/README.md) | Dermal tissue integrity, sub-layer profile | Dermis |

## Pathology modifiers

| Module | Biology | Fields |
|--------|---------|--------|
| [diabetic](diabetic/README.md) | Chronic wound impairment across all systems | (modifier) |
| [biofilm](biofilm/README.md) | Bacterial biofilm colonization, PAMP feedback | Biofilm |

## Neoplasia

| Module | Biology | Fields |
|--------|---------|--------|
| [tumor](tumor/README.md) | Basal cell carcinoma, soft contact inhibition | Tumor |

## ECM groundwork

| Module | Biology | Fields |
|--------|---------|--------|
| [elastin](elastin/README.md) | Elastic fiber network, slow turnover | Elastin |
| [hyaluronan](hyaluronan/README.md) | Hyaluronic acid, water retention, migration scaffold | Hyaluronan |
