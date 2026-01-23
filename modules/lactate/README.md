> [Home](../../README.md) / [Modules](../../README.md#modules) / Lactate

# Lactate

Lactate is a wound metabolite and tissue repair signal with both hypoxic and aerobic sources. The model represents a normalized lactate field, hypoxic production, perfusion clearance, VEGF signaling and a collagen synthesis modifier.

## Biology

Hypoxia can increase glycolytic lactate production, but it is only one source of wound lactate. [Trabold et al. 2003](https://pubmed.ncbi.nlm.nih.gov/14617293/) describe concentrations of 4 to 12 mM and signaling under normal oxygen conditions. The model's concentration has no established conversion to millimolar units.

[Constant et al. 2000](https://pubmed.ncbi.nlm.nih.gov/11115148/) found increased VEGF expression in lactate-treated cultured macrophages. [Hunt et al. 2007](https://pubmed.ncbi.nlm.nih.gov/17567242/) found HIF-1alpha stabilization and increased VEGF in aerobic human endothelial cell cultures, with increased VEGF and angiogenesis in mouse lactate-polymer implants. These findings support a lactate-driven VEGF signal independent of the hypoxic VEGF trigger. The model does not resolve the responding cell types or HIF molecular kinetics.

In rat wounds, Trabold et al. added 2 to 3 mM lactate using hydrolysable polyglycolide and measured a 50% increase in collagen deposition. This is an intervention-specific deposition result, not a universal doubling of fibroblast synthesis. Oxygen remains necessary for growth and matrix deposition. Hunt et al. found that arterial hypoxia abrogated implant angiogenesis despite lactate exposure.

When the glucose module is active, the model scales hypoxic lactate production with local glucose concentration. Increased production at equal hypoxia under hyperglycemia follows from this assumed linear coupling, rather than a fitted diabetic dose response.

As vascular perfusion is restored through angiogenesis, lactate is cleared via venous washout, providing a natural feedback loop that resolves the metabolic signal as the wound heals.

## Model

Single diffusing continuum field representing normalized tissue lactate concentration.

**Lactate production:**
- Produced in wound voxels where O2 falls below `o2_threshold`
- Production rate scales linearly with hypoxia fraction: `(threshold - O2) / threshold`
- When glucose module is enabled, production also scales with local glucose concentration (anaerobic glycolysis requires glucose substrate)
- Active in both epidermal wound and dermal wound voxels

**Lactate clearance:**
- Background PDE decay, which approaches zero without sources
- Perfusion-driven washout proportional to local vascular density (only where perfusion exceeds 0.1)

**Downstream signaling (via source hook):**
- Lactate-driven VEGF production proportional to `vegf_boost * lactate * base_vegf_rate`, applied in dermal and epidermal wound voxels after injury regardless of the hypoxia threshold
- The base rate retains angiogenesis module enablement, diabetic scaling and time taper. Direct hypoxic VEGF production remains a separate source
- Collagen boost: read by fibroblast behavior to scale collagen deposition by `(1 + collagen_boost * lactate)`

The linear response and its coefficients are assumptions. Hunt et al. describe concentration-dependent responses that decline at high lactate exposure. A physical concentration mapping is needed before introducing that curve. Aerobic lactate production and transport through specific monocarboxylate transporters are not represented. Endogenous production still requires hypoxia, so the corrected signal acts on lactate already produced, retained or diffused into oxygenated wound tissue.

## Parameters

From modules/lactate/config.toml and params.h:

| Parameter | Default | Units | Description | Source |
|-----------|---------|-------|-------------|--------|
| `enabled` | true | bool | Master switch | Convention |
| `diffusion` | 0.01 | - | Tissue diffusion coefficient | Assumed |
| `decay` | 0.02 | per model time | Background field loss | Assumed |
| `production_rate` | 0.003 | per step | Hypoxic lactate production | Assumed |
| `o2_threshold` | 0.3 | normalized | O2 below this triggers lactate production | Assumed |
| `vegf_boost` | 0.03 | multiplier | Lactate-driven VEGF production factor | Assumed |
| `collagen_boost` | 0.03 | multiplier | Collagen synthesis enhancement factor | Assumed |
| `perfusion_clearance` | 0.005 | per step | Perfusion-driven lactate washout rate | Assumed |

## Coupling

### Reads
| Field | Source module | How used |
|-------|-------------|----------|
| O2 | oxygen | Hypoxia fraction drives lactate production (below `o2_threshold`) |
| Glucose | glucose | Scales lactate production by glucose availability (anaerobic glycolysis substrate) |
| Vascular | angiogenesis | Perfusion-driven lactate clearance (venous washout) |

The angiogenesis source hook supplies the VEGF base rate through SignalBoard.

### Writes
| Field | Consumer modules | What is written |
|-------|-----------------|-----------------|
| Lactate | fibroblast (collagen boost) | Hypoxia-driven production, perfusion clearance |
| VEGF | angiogenesis | Lactate-driven VEGF production in both wound tissue compartments |

## Source files

| File | Purpose |
|------|---------|
| `lactate_pde.h` | Lactate diffusion field: initialization (starts at 0, builds from hypoxia) |
| `source_hook.h` | Hypoxia-driven lactate production, perfusion clearance, HIF-1alpha VEGF boost |
| `params.h` | LactateParams struct |
| `config.toml` | Module configuration |
