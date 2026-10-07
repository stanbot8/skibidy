# Treatment Interventions

Computational treatment studies modeling therapeutic interventions across six clinical domains. Each treatment is a TOML overlay modifying specific biological parameters based on published mechanisms of action.

Treatments are available as TOML overlays in study-scoped `treatments/` directories (plus shared treatments in `studies/shared/treatments/`). For summary tables, see [studies/README.md#treatments](../studies/README.md#treatments).

## Running treatments

```bash
# Single treatment
./run.sh --study=diabetic-wound --skin=diabetic --treatment=hbo

# Full comparison study (all 9 treatments + baseline)
python3 scripts/study/treatment_study.py

# Specific treatments only
python3 scripts/study/treatment_study.py --treatments=hbo,msc,combination

# List available treatments
./run.sh --list-treatments
```

## How treatments work

Treatments are TOML overlays applied after the profile and study config. The
resolved study's `treatments/` directory is searched before
`studies/shared/treatments/`. A same-name user study under `~/.skibidy/studies/`
(or `SKIBIDY_USER_STUDIES`) takes precedence over the repository study. Missing
treatments are rejected. The configuration sequence is:

```
bdm.core.toml + modules/*/config.toml           (merge)
  + profiles/diabetic.toml                        (biology)
  + studies/diabetic-wound/preset.toml            (experiment)
  + studies/diabetic-wound/treatments/hbo.toml    (intervention)
  = bdm.toml                                      (runtime)
```

The original presets move selected diabetic dysfunction parameters toward healthy values using the documented literature mappings. Exploratory presets below state their assumed effect sizes separately; a supported mechanism does not establish a calibrated clinical dose response.

## Treatment mechanisms

### Scheduled timing experiments

The treatment schedule generator writes `[[experiment.configs.schedule]]` events
with `treatment` and `start_day`. Screening uses the same event mechanism at day
zero. The experiment runner embeds each treatment's complete TOML text in
`[[treatment_schedule]]` entries in the saved run config, making the intervention
independent of later preset edits. Start days are absolute simulation days;
events apply at the first timestep boundary at or after that day, before wound,
immune, source, and agent biology. No treatment parameter changes before its
event. The preset's full numerical values apply at its start, with no fractional
day-zero approximation.

Events run in chronological order. Equal-time events retain their declared
order, and the last event to write a shared parameter wins. Values persist until
another event or an explicit safe interactive edit changes them. Overlapping
presets are sequential interventions, not an inferred additive drug model.

Only numeric parameters in
[`runtime_treatment_keys.inc`](../src/core/runtime_treatment_keys.inc) may change
at runtime. Geometry, module enable flags, field topology, and schedules cannot
be changed through an overlay or interactive reload. Required modules must be
enabled in the initial profile/study config. Coupled inflammation and MMP/TIMP
grid decay coefficients refresh when interventions change their owners.

Interactive hot reload applies only keys edited since the last accepted file,
preserving scheduled values on unchanged keys. An unsafe edit or removal rejects
the whole reload without changing simulation state. Checks occur before biology
at the metrics interval; a scheduled event at the same boundary follows the
reload and takes precedence. Batch runs disable hot reload. Consensus replicates
use distinct paired seeds and reject a cohort when any requested run fails.

### Anti-inflammatory (anti-TNF-alpha)

The preset assumes that TNF-alpha neutralization improves the failed M1-to-M2
macrophage transition through these effective parameter changes:
- Releasing the M1-to-M2 brake (m1_duration_factor: 3.0 to 1.5)
- Restoring M2 anti-inflammatory resolution (resolution_factor: 0.3 to 0.7)
- Reducing AGE/RAGE-driven baseline inflammation (0.001 to 0.0002)
- Restoring keratinocyte proliferation and migration

### Hyperbaric oxygen (HBO)

HBO corrects the tissue hypoxia that drives much of diabetic wound dysfunction:
- Restores HIF-1alpha/VEGF cycling (vegf_factor: 0.4 to 1.0)
- Improves microcirculation (perfusion basal: 0.7 to 0.85)
- Accelerates angiogenesis (angio_rate: 0.002 to 0.008)
- Partially rescues collagen synthesis via prolyl hydroxylase O2 supply

### Negative pressure wound therapy (NPWT)

Multi-modal mechanical intervention:
- Blood-flow support motivated by a fourfold laser-Doppler increase in pig wounds
- Microdeformation stimulates cell proliferation
- Macrodeformation assists wound edge advancement (inward_bias: 0.3 to 0.5)
- Sealed dressing controls moisture and clears inflammatory exudate

### Doxycycline (sub-antimicrobial MMP inhibitor)

Targets the MMP/TIMP imbalance that destroys ECM in diabetic wounds:
- Assumes lower aggregate MMP production (mmp_factor: 2.5 to 1.5)
- Restores TIMP production (timp_production_factor: 0.4 to 0.76)
- Preserves collagen and fibronectin scaffolds
- Mild anti-inflammatory effect via TACE inhibition

### Growth factor (PDGF-BB / becaplermin)

FDA-approved recombinant growth factor for DFU:
- Potent fibroblast mitogen (density_factor: 1.0 to 1.8)
- Rapid fibroblast activation (activation_factor: 2.0 to 1.0)
- Does not directly change the model's collagen synthesis factor

### Mesenchymal stem cell (MSC) therapy

Broadest-acting intervention via paracrine secretome:
- M1-to-M2 macrophage reprogramming (IL-6, PGE2)
- VEGF production as an assumed paracrine target
- Fibroblast activation (PDGF, TGF-beta)
- Keratinocyte proliferation/migration (EGF, bFGF, HGF)

### Moisture dressings

Maintains optimal wound hydration:
- Assumed 83% reduction of the model's surface-loss parameter (0.03 to 0.005)
- Hydrogel moisture donation (recovery_rate: 0.02 to 0.06)
- Exudate absorption clears inflammatory mediators

### Senolytic therapy (dasatinib + quercetin)

Targeted clearance of senescent cells that accumulate in chronic diabetic wounds:
- Assumed senescent-cell clearance (senolytic_clearance: 0.0 to 0.005)
- Reduced SASP burden (inflammation, MMP, TGF-beta output from senescent cells)
- Restored proliferative capacity in surrounding tissue
- Lower baseline inflammation from SASP-driven chronic signaling

### Combination therapy

Rational multi-target approach addressing all four diabetic dysfunction axes:
1. **Immune**: anti-TNF-alpha (M1/M2 transition)
2. **Vascular**: HBO (O2/VEGF/angiogenesis)
3. **ECM**: doxycycline (MMP/collagen preservation)
4. **Moisture**: advanced dressing (hydration)

## Treatment scheduling

The schedule generator creates experiment TOMLs with full treatment presets applied at their actual start days. Use the event semantics described above.

```bash
# Single treatment schedules (NPWT/HBO/MSC at days 0, 7, 14, 21)
python3 scripts/study/gen_treatment_schedule.py --treatments npwt,hbo,msc --days 0,7,14,21

# Pairwise combinatorial scheduling (cross-product of start days)
python3 scripts/study/gen_treatment_schedule.py --treatments npwt,hbo,msc --days 0,7,14,21 --combo

# Run all generated schedules
python3 studies/run_experiments.py studies/diabetic-wound/experiments/schedule_*.toml
```

Output goes to `studies/diabetic-wound/experiments/schedule_*.toml`. Each experiment includes an untreated diabetic baseline and configs for each start day.

### Exploratory pro-resolution study

The opt-in [pro-resolution sensitivity experiment](../studies/diabetic-wound/experiments/proresolution_sensitivity.toml)
tests restoration of macrophage efferocytosis and inflammation resolution with
the existing model targets. Tang et al. reported that local Resolvin D1 improved
wound closure and reduced apoptotic-cell and macrophage accumulation in diabetic
mice; diabetic macrophage phagocytosis also improved. This establishes the
mechanism direction in that experimental setting. [Primary study: Diabetes 2013,
doi:10.2337/db12-0684](https://diabetesjournals.org/diabetes/article/62/2/618/15619/Proresolution-Therapy-for-the-Treatment-of-Delayed).

The three new overlays assume 25%, 50%, or 75% recovery of the gap between the
existing diabetic factors and the healthy value 1.0. Efferocytosis factors are
0.625, 0.75, and 0.875; resolution factors are 0.475, 0.65, and 0.825. These
magnitudes are sensitivity assumptions, with no fitted dose response. The
experiment compares all three day-zero assumptions and the middle assumption
at days 7 and 14 against untreated diabetes, using paired seeds 42 through 46.
Existing profiles and the original nine treatment presets stay fixed. This
experiment explicitly sets 42 days; the study's existing default is 35 days.

```bash
python3 scripts/study/experiment_runner.py studies/diabetic-wound/experiments/proresolution_sensitivity.toml
```

Each execution uses a fresh result directory and freezes the executable and
project library. The binary receipt records their hashes and loaded dependencies;
the cohort manifest retains every planned seed, exact saved config, metrics hash,
log, and completed/failed/pending status. Runs use one OpenMP thread and private
working directories. An incomplete cohort cannot publish a comparison. Scalar
outcomes are calculated per replicate before averaging; paired differences use
matching seeds. Unreached closure thresholds remain censored, with observed
counts reported. Figures show mean and population standard deviation across five
seeds; scalar and paired summaries report sample standard deviations.

The model represents the mediator through two effective biological factors;
receptor signaling, drug concentration, exposure duration, and dose toxicity are
not represented. Results are hypotheses about the model's response to restored
resolution, with no claim of human efficacy or quantitative reproduction of the
mouse experiment. Runtime verification of scheduling is maintained in
`scripts/validation/treatment_regression.py`.

The [2026-10-07 complete cohort](../studies/diabetic-wound/data/proresolution_20261007/receipt.json)
contains 30 successful runs with paired seeds 42–46. Its
[replicate archive](../studies/diabetic-wound/data/proresolution_20261007/replicate_evidence.zip)
preserves the exact configs, metrics and logs, alongside
[paired differences](../studies/diabetic-wound/data/proresolution_20261007/paired_deltas.csv)
and [trajectories](../studies/diabetic-wound/data/proresolution_20261007/trajectories.png).
All arms reached 100% closure; that endpoint cannot rank treatments here.
The table reports replicate mean ± sample SD, with five observations per value.

| Assumed recovery and start | T50 (days) | T90 (days) | Final scar magnitude (model units) |
|---|---:|---:|---:|
| Untreated | 17.67 ± 0.70 | 32.83 ± 1.62 | 0.468 ± 0.196 |
| 25%, day 0 | 17.00 ± 1.26 | 33.67 ± 1.51 | 0.611 ± 0.117 |
| 50%, day 0 | 16.83 ± 0.70 | 32.17 ± 0.95 | 0.639 ± 0.155 |
| 75%, day 0 | 16.83 ± 0.70 | 33.50 ± 1.09 | 0.522 ± 0.082 |
| 50%, day 7 | 17.17 ± 0.95 | 33.83 ± 2.40 | 0.425 ± 0.212 |
| 50%, day 14 | 17.17 ± 0.75 | 33.33 ± 1.56 | 0.484 ± 0.266 |

For the 50% day-zero assumption, paired T50 decreased by 0.83 ± 0.83 days,
while scar magnitude increased by 0.171 ± 0.135 model units. This model response
does not establish an optimal treatment or a monotonic effect on later closure.
Metrics are sampled every 20 hours: T50/T90 are first observed threshold crossings,
without interpolation. The configured simulation lasts 1008 hours (42 days);
its last regular metrics sample is at hour 1000. Day-seven and day-fourteen arms
matched their untreated partner in every saved pre-start metric row (nine and
17 rows, respectively) for all five seeds and differed afterward. The untreated
cohort's eventual healing and the small paired cohort limit conclusions about
chronic human ulcers. No parameter was fitted to these outputs.

## Creating custom treatments

Create a new TOML file in the study's `treatments/` directory (or `studies/shared/treatments/` for cross-study treatments):

```toml
# Treatment: my_therapy
# Literature: Author et al. Year
# Mechanism: what it does biologically

[skin.diabetic]
m1_duration_factor = 2.0    # override diabetic dysfunction
prolif_factor = 0.7          # partially restore proliferation

[skin.perfusion]
angio_rate = 0.005           # override vascular params
```

The treatment file only needs to contain the parameters it modifies. All other parameters remain at their diabetic profile values.

## Output

The treatment study script produces:
- `output/treatment_study/metrics_<treatment>.csv` contains full metrics for each run
- `output/treatment_study/treatment_comparison.csv` contains the summary comparison table
- Console output with closure rates, inflammation peaks, healing times

## Biological validity

Published evidence supports several mechanism directions and outcome constraints.
It does not identify the current effective factors or establish a dose response.
The curated [measurement table](../studies/diabetic-wound/data/treatment_constraints.csv),
[primary-source catalog](../studies/diabetic-wound/SOURCES.yaml), and
[download provenance](../studies/diabetic-wound/data/treatment_provenance.json)
separate measured outcomes, treatment protocols, and model assumptions.

| Intervention | Primary measurement available | Connection and remaining calibration gap |
|---|---|---|
| RvD1 | Splinted 5-mm db/db mouse wounds received 100 ng/wound daily starting 24 h after injury; closure improved after eight treatment days. | Closure maps to `wound_closure_pct`. Day-five apoptotic/macrophage histology supports resolution direction. The XML has no numerical closure effect size or supplementary-material nodes; figure assets were inaccessible. A 0.1 nmol/L macrophage experiment measures opsonized-zymosan uptake, not the model's apoptotic-cell efferocytosis rate. [Tang 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3554373/) |
| HBO | At one year, 25/48 (52%) HBOT ulcers versus 12/42 (29%) placebo ulcers healed. | This selected-patient complete-healing fraction is not a mean wound-area trajectory or a fitted VEGF/perfusion/angiogenesis factor, and exceeds the 42-day horizon. [Londahl 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2858204/) |
| NPWT | In partial diabetic-foot amputation wounds, 43/77 (56%) versus 33/85 (39%) healed by 112 days. Pig experiments reported fourfold blood flow and granulation increases of 63.3% (continuous) or 103% (intermittent suction). | Different wound type, species, and endpoint; these values do not directly identify the model's angiogenesis, inward-bias, or collagen factors. [Armstrong 2005](https://doi.org/10.1016/S0140-6736(05)67695-7), [Morykwas 1997](https://doi.org/10.1097/00000637-199706000-00001) |
| Doxycycline | Diabetic/control biopsy ratios differed by isoform: MMP1 65-fold, proMMP2 3-fold, activeMMP2 6-fold, MMP8 2-fold, MMP9 14-fold; TIMP2 was half the control level. | This disease comparison contains no doxycycline exposure. Isoform concentrations cannot calibrate aggregate MMP production 2.5 to 1.5 or TIMP production 0.4 to 0.76. [Lobmann 2002](https://doi.org/10.1007/s00125-002-0868-8) |
| PDGF-BB | A pooled four-trial analysis (922 patients) estimated healing probability 50% versus 36% and the 35th percentile of complete-healing time 14.1 versus 20.1 weeks for 100 microg/g becaplermin versus placebo. | Cohort probability and a complete-healing percentile are distinct from fibroblast density 1.8 and mean model T50. [Smiell 1999](https://doi.org/10.1046/j.1524-475X.1999.00335.x) |
| Senolytic | Nine diabetic-kidney-disease participants received dasatinib 100 mg plus quercetin 1000 mg for three days. Epidermal p16-positive and p21-positive cells/mm decreased 20% and 31%, assessed 11 days later. | Primary epidermal measurements differ from secondary review figures. This open-label marker study has no wound-healing endpoint and cannot identify a constant per-step clearance rate of 0.005. [Hickson 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6796530/) |
| MSC | A primary murine study reports decreased activated MMP9 at days three and seven and improved collagen I. | Supports direction; no extracted magnitude calibrates the preset's many targets. Its Cao 2017 citation is a review, and the Li 2024 author/year citation is insufficiently specific for a numeric constraint. [Xu 2017](https://doi.org/10.1152/physiolgenomics.00090.2016) |
| Anti-inflammatory | Local IL-1beta blockade improved macrophage phenotype and repair in db/db mice. | This is a different cytokine target from the anti-TNF preset; it does not calibrate that preset's rates. [Mirza 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3712034/) |
| Moisture | Winter's original pig study supports the moist-covering mechanism. | No extracted primary measurement establishes an 83% TEWL effect or recovery 0.06. The 83% value is arithmetic on the model's assumed loss-rate change. [Winter 1962](https://doi.org/10.1038/193293a0) |
| Combination | Component evidence above. | No matching combination cohort establishes additivity, synergy, or a fitted combined effect; overlapping keys follow declared replacement order. |

Raw source records are downloaded to ignored `output/treatment-evidence/` with
`python3 scripts/study/fetch_treatment_evidence.py`. Use `--cached` to verify an
existing copy without another download. DOI identity and SHA256 hashes are saved;
failed sources remain visible in provenance. No individual-subject dataset or
parameter fit has been recovered. This evidence audit covers the diabetic-wound
treatments; the other clinical-domain presets below retain their existing
mechanistic descriptions and have not received this quantitative audit.

## RA treatment mechanisms

Five biologic and DMARD treatments target the dual TNF-alpha/IL-6 inflammatory axis in rheumatoid arthritis.

### Anti-TNF (infliximab/adalimumab/etanercept)

Monoclonal antibody neutralization of soluble and membrane-bound TNF-alpha:
- Direct TNF clearance (anti_tnf_clearance: 0.0 to 0.05)
- Reduced NF-kB inflammatory amplification (tnf_inflammation_coupling: 0.01 to 0.004)
- Lower MMP transcription (tnf_mmp_boost: 0.008 to 0.003)
- Pannus regression via VEGF reduction (tnf_vegf_boost: 0.005 to 0.002)
- Partial M1 duration normalization (m1_prolongation: 2.0 to 1.4)

### Tocilizumab (anti-IL-6R)

Humanized monoclonal antibody blocking IL-6 receptor signaling:
- IL-6R blockade (anti_il6r_clearance: 0.0 to 0.04)
- Suppressed JAK/STAT3 amplification (il6_inflammation_coupling: 0.008 to 0.003)
- Reduced RANKL-mediated bone erosion (il6_cartilage_boost: 0.002 to 0.0008)

### Methotrexate (conventional DMARD)

Folate antagonist with broad immunosuppressive effects:
- Reduced autoimmune TNF/IL-6 source (autoimmune_source halved)
- Lower NF-kB and JAK/STAT3 amplification
- Moderate MMP reduction (tnf_mmp_boost: 0.008 to 0.005)
- Reduced FLS hyperplasia (pannus_fibroblast_boost: 2.0 to 1.5)

### JAK inhibitor (tofacitinib/baricitinib)

Small molecule inhibitor blocking JAK1/JAK3 intracellular signaling:
- Blocks JAK/STAT pathway downstream of multiple cytokine receptors
- Suppressed T cell proliferation and recruitment
- Reduced IL-6 amplification via STAT3 blockade
- Oral small molecule (faster onset than biologics)

### RA triple combination

Combined anti-TNF + tocilizumab + methotrexate:
- All three clearance and suppression mechanisms active simultaneously
- Near-normal M1 duration and FLS proliferation
- Strongest cartilage protection (all three erosion pathways suppressed)

Note: dual biologic therapy (anti-TNF + tocilizumab) is not standard clinical practice due to infection risk. This combination is modeled for mechanistic study of maximal cytokine blockade.

## Burn treatments

Five treatments in `studies/burn/treatments/` targeting thermal injury:

| Treatment | File | Mechanism |
|-----------|------|-----------|
| Cooling | `cooling.toml` | Immediate cold water first aid, preserves stasis zone |
| Debridement | `debridement.toml` | Surgical eschar removal, exposes viable wound bed |
| Silver sulfadiazine | `silver_sulfadiazine.toml` | Broad-spectrum topical antimicrobial (mildly cytotoxic to keratinocytes) |
| Skin substitute | `skin_substitute.toml` | Bioengineered collagen-GAG scaffold (Integra/Biobrane), reduces TEWL |
| Pressure garment | `pressure_garment.toml` | Compression therapy (15 to 25 mmHg), prevents hypertrophic scar |

## Pressure ulcer treatments

Five treatments in `studies/pressure-ulcer/treatments/` targeting ischemia-reperfusion injury:

| Treatment | File | Mechanism |
|-----------|------|-----------|
| Pressure redistribution | `pressure_redistribution.toml` | Low-air-loss mattress with 2h repositioning protocol |
| Wound VAC | `wound_vac.toml` | Negative pressure wound therapy for Stage III/IV |
| Nutrition | `nutrition.toml` | Protein, zinc, vitamin C supplementation for tissue repair |
| Silver dressing | `silver_dressing.toml` | Antimicrobial silver with moisture balance |
| Offloading | `offloading_protocol.toml` | Complete pressure elimination (gold standard prevention) |

## Surgical treatments

Five treatments in `studies/surgical/treatments/` targeting SSI prevention:

| Treatment | File | Mechanism |
|-----------|------|-----------|
| Prophylactic antibiotics | `prophylactic_antibiotics.toml` | Perioperative antimicrobial prophylaxis |
| Chlorhexidine | `chlorhexidine.toml` | Antiseptic skin preparation |
| Negative pressure | `negative_pressure.toml` | Incisional NPWT over closed surgical wounds |
| Enhanced recovery | `enhanced_recovery.toml` | ERAS protocol: nutrition, perfusion, reduced inflammation |
| Antimicrobial suture | `antimicrobial_suture.toml` | Triclosan-coated suture material |

## Shared treatments

Cross-study treatments in `studies/shared/treatments/`, searchable from any study:

| Treatment | File | Mechanism |
|-----------|------|-----------|
| Triple antibiotic | `triple_antibiotic.toml` | Bacitracin/neomycin/polymyxin B in petrolatum base; reduces infection, maintains moist wound environment |
