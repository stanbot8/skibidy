> [Home](../../README.md) / [Modules](../../README.md#modules) / Nitric Oxide

# Nitric Oxide

Nitric oxide (NO) is produced by inducible nitric oxide synthase (iNOS) during wound inflammation. The model represents immune-cell production, vasodilation and antimicrobial activity with an arbitrary-unit field. Its diffusion, decay and coupling strengths are assumed model values, not measured NO exposure.

## Biology

Nitric oxide is a small gaseous signaling molecule produced by NOS isoforms. This model assigns immune NO production to M1 macrophages and neutrophils and no production to M2 macrophages. That source selection is a model simplification, not a universal claim about macrophage phenotypes.

NO mediates vasodilation by activating soluble guanylyl cyclase in vascular smooth muscle cells, increasing cyclic GMP and causing relaxation. In wounds, this increases local perfusion and oxygen delivery to the healing tissue (Luo and Chen 2005). NO also serves as a direct antimicrobial effector: reactive nitrogen species (peroxynitrite, nitrogen dioxide) generated from NO are toxic to bacteria and suppress biofilm growth (Fang 1997).

### Collagen evidence and limits

NOS inhibition reduced wound collagen accumulation and breaking strength in [Schaffer et al. 1996](https://pubmed.ncbi.nlm.nih.gov/8661204/). This paper does not support blanket NO-mediated collagen suppression. [Witte et al. 2000](https://pubmed.ncbi.nlm.nih.gov/11139365/) found increased collagen synthesis in dermal fibroblasts exposed to SNAP. [Obayashi et al. 2006](https://pubmed.ncbi.nlm.nih.gov/16171977/) found increased type I collagen synthesis in normal human dermal fibroblasts exposed to NO donors.

Exposure context matters. [Excessive NO in an inflammatory rat granuloma model](https://pubmed.ncbi.nlm.nih.gov/23290597/) impaired collagen accumulation. The field has no physical dose mapping, and donor concentration is not free NO concentration. Direct NO regulation of collagen is therefore unmodeled. The former linear inhibitory multiplier and `collagen_suppression` setting were removed. Old configurations containing that key no longer affect collagen deposition. A stimulatory, inhibitory or biphasic curve cannot be quantitatively justified in these field units.

In diabetic rats, [Schaffer et al. 1997](https://pubmed.ncbi.nlm.nih.gov/9142149/) associated impaired repair with decreased wound NO synthesis. This supports a qualitative NO deficit, not a fixed 40% reduction in iNOS expression or per-cell production. The model's `diabetic.no_factor = 0.6` remains an assumed production modifier.

The [matched simulation report](../../literature/no-collagen-20261007/README.md)
records this repair's regression and its failure to restore wound collagen,
alongside the MMP breakdown diagnostic.

## Model

Single diffusing continuum field with assumed diffusion and decay. The field is not calibrated to the physical half-life of NO in tissue.

**NO production:**
- M1 macrophages produce NO at `m1_production` rate, tapered by M1 state age (declining iNOS expression over time)
- Neutrophils produce NO at `neutrophil_production` rate, tapered by cell age
- In diabetic mode, production rates are multiplied by the assumed `diabetic.no_factor` (0.6)
- Production uses agent-level deposition via ScaledGrid

**NO decay:**
- PDE decay coefficient is 0.05 in simulation units
- Diffusion coefficient is 0.02 in simulation units

**Downstream effects (consumed by other modules):**
- Vasodilation: angiogenesis source hook boosts effective perfusion by `angio_rate * vasodilation_factor * NO` in wound voxels
- Antimicrobial: biofilm post hook scales effective growth rate by `max(0, 1 - antimicrobial_factor * NO)`

## Parameters

From modules/nitric_oxide/config.toml and sim_param.h:

| Parameter | Default | Units | Description | Source |
|-----------|---------|-------|-------------|--------|
| `enabled` | true | bool | Master switch | Convention |
| `diffusion` | 0.02 | simulation units | Field diffusion | Assumed |
| `decay` | 0.05 | simulation units | Field decay | Assumed |
| `m1_production` | 0.01 | per step | M1 NO source | Assumed magnitude, qualitative source rationale in Witte and Barbul 2002 |
| `neutrophil_production` | 0.005 | per step | Neutrophil NO source | Assumed magnitude, qualitative source rationale in Witte and Barbul 2002 |
| `vasodilation_factor` | 0.05 | multiplier | Perfusion boost per unit NO | Assumed magnitude, qualitative rationale in Luo and Chen 2005 |
| `antimicrobial_factor` | 0.3 | multiplier | Biofilm growth suppression per unit NO | Assumed |

## Coupling

### Reads
| Field | Source module | How used |
|-------|-------------|----------|
| (Agent positions) | immune | M1 macrophages and neutrophils deposit NO at their locations via iNOS |

### Writes
| Field | Consumer modules | What is written |
|-------|-----------------|-----------------|
| NitricOxide | angiogenesis (vasodilation boost), biofilm (antimicrobial suppression) | iNOS production from M1 macrophages and neutrophils |

## Source files

| File | Purpose |
|------|---------|
| `nitric_oxide_pde.h` | NO diffusion field (starts at 0, produced by immune cells) |
| `params.h` | NitricOxideParams struct (enabled flag; remaining params in sim_param.h) |
| `config.toml` | Module configuration |
