# Reference dataset provenance

Audit of the 32 reference CSVs in `modules/*/data/` that drive the validation
pipeline. For each dataset: observable, condition, primary citations, cohort
size when reported, extraction method, aggregation rule, normalization. Updated
Catalog originally recorded 2026-04-26. Coverage and reference limits reviewed 2026-10-07.

The companion file `modules/<m>/SOURCES.yaml` carries fuller per-paper notes;
this table records the existing reference curves. Labels such as "consensus",
"multi-paper mean" and "tabular" below are inherited descriptions, not verified
patient-level extractions. Where source tables, extraction records, cohorts or
aggregation weights are absent, these are qualitative modeling targets.
Citations do not establish their numerical values or uncertainty. Passing an
RMSE screen against such a curve is not empirical validation.

Measured data added on 2026-10-07: [GSE209609 human wound RNA](../modules/wound/data/published/GSE209609/README.md),
with 96 biopsies, 18 subjects, 17 genes, deposited processed values, sample IDs,
group SDs, source hashes and a reproducible extractor. This supports RNA timing,
not calibration of the current protein, cell-count, collagen or membrane fields.

Other primary evidence added at the same time:
[individual keratinocyte division records](../modules/tissue/data/README.md)
and [basement-membrane component observations](../modules/basement_membrane/README.md).
Cycle durations constrain observed division distributions, not the coefficient
of variation of persistent simulated traits. Component staining in a graft
does not identify a dimensionless membrane damage or repair rate.

## Core wound healing (normal)

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `wound/data/closure_kinetics_punch_biopsy.csv` | re-epithelialization | Eaglstein 1978 J Invest Dermatol; Cukjati 2000 Med Biol Eng Comput; Pastar 2014 Adv Wound Care | not stated | consensus | multi-paper mean | absolute (0-100%) |
| `inflammation/data/inflammation_timecourse.csv` | inflammatory mediator burden | Eming 2007 J Invest Dermatol; Hubner 1996 Cytokine; Koh 2011 Expert Rev Mol Med; Canedo 2019 Int J Inflam | not stated | consensus | multi-paper mean | peak-normalized |
| `immune/data/immune_cell_kinetics.csv` | neutrophil + macrophage density | Kim 2008 J Invest Dermatol; Wilgus 2013 Adv Wound Care; Rodero 2010 Int J Clin Exp Pathol; Krzyszczyk 2018 Front Physiol; Lucas 2010 J Immunol | not stated | consensus | multi-paper mean | peak-normalized per cell type |
| `fibroblast/data/fibroblast_kinetics.csv` | fibroblast infiltration | Singer 1999 N Engl J Med; Werner 2007 J Invest Dermatol; Clark 1996 (textbook) | not stated | tabular | single-source | peak-normalized |
| `fibroblast/data/myofibroblast_kinetics.csv` | myofibroblast density | Desmouliere 1995 Am J Pathol; Darby 2014 Clin Cosmet Investig Dermatol; Tomasek 2002 Nat Rev; Hinz 2007 J Invest Dermatol | not stated | consensus | multi-paper mean | peak-normalized |
| `fibroblast/data/collagen_deposition.csv` | total collagen | Gonzalez 2016 An Bras Dermatol; Zhou 2013 PLoS One; Mathew 2021 Bioengineering; Caetano 2016 Pharm Biol | not stated | consensus | multi-paper mean | end-normalized |
| `fibroblast/data/tgfb_kinetics.csv` | TGF-beta | Frank 1996 J Biol Chem; Shah 1995 J Cell Sci; Werner 2003 Physiol Rev; Barrientos 2008 Wound Repair Regen | not stated | consensus | multi-paper mean | peak-normalized |
| `fibronectin/data/fibronectin_kinetics.csv` | fibronectin | Grinnell 1981 J Invest Dermatol; Clark 1982 J Invest Dermatol; Welch 1990 J Cell Biol | not stated | consensus | multi-paper mean | peak-normalized |
| `mmp/data/mmp_kinetics.csv` | MMP activity | Nwomeh 1998 Wound Repair Regen; Gill 2008 Int J Biochem Cell Biol; Caley 2015 Adv Wound Care | not stated | consensus | multi-paper mean | peak-normalized |
| `angiogenesis/data/vegf_kinetics.csv` | VEGF | Nissen 1998 Am J Pathol; Brown 1992 J Exp Med; Johnson 2014 Adv Wound Care | not stated | consensus | multi-paper mean | peak-normalized |
| `ph/data/ph_kinetics.csv` | wound surface pH (alkalinity proxy) | Schneider 2007 Arch Dermatol Res; Gethin 2007 Wounds UK | not stated | consensus | multi-paper mean | scaled (1.0=pH 7.4, 0.0=pH 5.5) |

## Diabetic

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `diabetic/data/diabetic_closure_kinetics.csv` | wound closure | Galiano 2004 Wound Repair Regen; Michaels 2007 Wound Repair Regen; Falanga 2005 Lancet | not stated | tabular (db/db murine) | weighted | absolute (0-100%) |
| `diabetic/data/diabetic_inflammation_timecourse.csv` | inflammatory mediator burden | Mirza 2011 Cytokine; Louiselle 2021 Transl Res; Eming 2014 Sci Transl Med; Clayton 2024 Adv Wound Care | not stated | tabular (db/db murine) | weighted | peak-normalized |
| `diabetic/data/diabetic_immune_cell_kinetics.csv` | neutrophil + macrophage density | Mirza 2011 Cytokine; Wetzler 2000 J Invest Dermatol; Khanna 2010 PLoS One; Clayton 2024 Adv Wound Care | not stated | tabular (db/db murine) | weighted | peak-normalized per cell type |
| `diabetic/data/diabetic_mmp_kinetics.csv` | MMP activity | Lobmann 2002 Diabetologia (MMP-1 65x, MMP-9 14x elevated in DFU vs traumatic) | n=12 (Lobmann) | parameter-derived from fold-change ratio | single-source | peak-normalized |
| `diabetic/data/diabetic_tgfb_kinetics.csv` | TGF-beta | Diabetic fibroblast and macrophage background. No extracted quantitative timecourse or established 50% TGF-beta reduction | not stated | constructed | unverified aggregation | peak-normalized |

## Burn

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `burn/data/burn_closure_kinetics.csv` | wound closure (deep partial thickness) | Jackson 1953 Br J Surg (zone classification); Declercq 2012 | not stated | consensus | multi-paper | absolute (0-100%) |
| `burn/data/burn_inflammation_timecourse.csv` | inflammatory mediator burden | Declercq 2012; Evers 2010 | not stated | consensus | multi-paper | peak-normalized |
| `burn/data/burn_immune_cell_kinetics.csv` | neutrophil + macrophage density | Declercq 2012; Evers 2010 | not stated | consensus | multi-paper | peak-normalized per cell type |

## Pressure ulcer

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `pressure/data/pressure_closure_kinetics.csv` | closure (Stage II/III) | NPUAP/EPUAP/PPPIA 2019 guideline; Thomas 1997 | guideline aggregate | guideline + single primary | weighted | absolute (0-100%) |
| `pressure/data/pressure_inflammation_timecourse.csv` | inflammatory mediator burden | NPUAP 2019; Mustoe 2006 | guideline aggregate | guideline + single primary | weighted | peak-normalized |
| `pressure/data/pressure_immune_cell_kinetics.csv` | neutrophil + macrophage density | Mustoe 2006; Gefen 2022 | not stated | consensus | multi-paper | peak-normalized per cell type |

## Surgical

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `wound/data/surgical_closure_kinetics.csv` | re-epithelialization (primary intention) | Gottrup 2004; Singer 1999 N Engl J Med | not stated | consensus | multi-paper | absolute (0-100%) |
| `wound/data/surgical_inflammation_timecourse.csv` | inflammatory mediator burden | Gottrup 2004; Singer 1999 N Engl J Med | not stated | consensus | multi-paper | peak-normalized |
| `wound/data/surgical_immune_cell_kinetics.csv` | neutrophil + macrophage density | Gottrup 2004; Singer 1999 N Engl J Med | not stated | consensus | multi-paper | peak-normalized per cell type |

## Venous ulcer

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `wound/data/venous_closure_kinetics.csv` | wound closure | Harrison 2011 BMC Nursing (Canadian Bandaging Trial) | n=215 (4LB arm) | tabular (Table 6) | single-arm | absolute (0-100%) |

## Skin senescence

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `senescence/data/p16_p21_age_cross_section.csv` | p16/p21+ cell percentage by age bin | Idda 2020 Aging | n=5/bin (Young/Middle/Old) | figure-extracted (Fig 2A-D) | single-source | absolute (% positive) |

## Scar maturation (clinical scar scoring)

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `scar/data/scar_posas_observer_normal.csv` | POSAS Observer mean at 3/6/12 mo (normal-healing burn-graft scar) | van der Wal 2024 Burns | n=127 | tabular | single-source | absolute (POSAS 1-10) |
| `scar/data/scleroderma_mrss_trajectory.csv` | mRSS Class 4 trajectory (canonical dcSSc) | Ledoult 2020 Arthritis Res Ther | n=13 (Class 4 of 198) | tabular (Table 2) | single-class | absolute (mRSS 0-51) |

## Tumor (BCC / SCC)

| File | Observable | Citation(s) | Cohort | Extraction | Aggregation | Normalization |
|------|------------|-------------|--------|------------|-------------|---------------|
| `tumor/data/tumor_doubling_time.csv` | volume doubling time | Khoo 2019 Acta Derm Venereol; Tejera 2023 Actas Dermosifiliogr | not stated | tabular | consensus | absolute (days) |
| `tumor/data/tumor_growth_rate.csv` | linear growth rate | Fijalkowska 2023 Postepy Dermatol Alergol; Sykes 2020 Australas J Dermatol; Kricker 2014 J Am Acad Dermatol | community-cohort | tabular | consensus | absolute (mm/month) |
| `tumor/data/tumor_proliferation_index.csv` | Ki-67 fraction | Toth 2012 Biologia; Alferraly 2019 Open Access Maced J Med Sci; al-Sader 1996 J Clin Pathol | not stated | tabular | consensus | absolute (% Ki-67+) |

## Reference limits and coverage gaps
Legacy timecourses lack a verified chain from measured values to the stored
target, including extraction records, source cohorts and aggregation weights.
Some normalized per-paper files exist under `raw/`. Their presence does not
establish that the values were digitized, that an asserted consensus is a mean,
or that the underlying assays measure the same quantity.
Normal closure combines a pig partial-thickness series, a human sigmoid fit and
a review composite. The day-7 raw-file mean is about 52.3%, while the target is
45%. No aggregation procedure explaining that difference is recorded. The
simulation uses wound-voxel occupancy, which is not automatically equivalent to
the source outcomes.
Collagen inputs mix tensile-strength proxies, estimated deposition from rat
synthesis rates, rat hydroxyproline and review schematics. The target is
end-normalized at day 28. Its normalized value is not a collagen mass,
concentration or breaking strength. The raw files are modeling inputs, and their
label does not make them interchangeable assays.
Diabetic MMP and TGF-beta targets are constructed day-by-day trajectories with
unverified numerical extraction. They are not simple amplitude-scaled normal
curves. Normal MMP peaks at day 5 and the diabetic target at day 21.
Lobmann's cross-condition MMP observations do not establish that 28-day shape.
The inherited TGF-beta table attribution of a 50% reduction to Lerman is
unestablished. Peak normalization does not test a diabetic fold change.
Burn, pressure and primary-intention surgical targets are condition sketches
without recorded cohorts or a reproducible numerical extraction. The pressure
target's guideline citation is not itself a measured closure timecourse.
The pH target is a schematic alkalinity index without extracted pH measurements.
The six rheumatoid curves are generated 30-day trajectories supported by review
background, not an observed joint-erosion cohort.
Measured-data exceptions include the GSE209609 extraction linked above and
the venous, scar and senescence CSV headers. Some headers contain cohort sizes,
source tables and approximate figure-extraction descriptions. These must be
assessed individually. They do not validate the legacy normalized targets.
Many mechanisms have no quantitative outcome screen, including bioelectricity,
biofilm, blood, body site, dermis, elastin, glucose, hemostasis, hyaluronan,
lactate, lymphatics, mechanotransduction, neuropathy, nitric oxide, perfusion,
photon input, ROS, scab, temperature and tissue. Scar and senescence have stored
CSV evidence, but the shared validator does not score it. A physical input may
need a different validation design from a wound timecourse.


## Profiles without dedicated reference curves

The following profiles exist but have no condition-specific reference CSVs;
the validator leaves unsupported condition comparisons untested:

`keloid`, `hypertrophic`, `psoriasis`, `aged`, `aged_diabetic`, `tumor_wound`.

`venous` and `scleroderma` have stored datasets above but no shared-validator
observable mapping. Presence of a CSV is not tested coverage.
`rheumatoid` is study-scoped and has separate reference data under `studies/rheumatoid/`.

### Hypertrophic gap

A multi-timepoint hypertrophic-specific scoring trajectory was searched for
in open-access form (Bombaro 2003, Bock 2006, Niessen 1999, Bloemen 2009,
Nedelec 2014, van der Wal 2012/2017, Lee 2024). The strongest candidate
(Nedelec 2014, n=46, 3/6/12 mo ultrasound thickness) is paywalled and the
abstract reports only directional changes, not per-timepoint values. The
hypertrophic profile currently validates against the normal-scar POSAS
baseline; the deviation upward from that baseline is the proxy observable.

### Saved-cohort review, 2026-10-07

The nine saved runs in `baseline-20261007/replicate_evidence.zip` were
re-evaluated through the shared overlap-only validator without rerunning the
simulation or changing that archive. `scripts/compare_replicates.py` now reads
each run's saved configuration, rejects mixed settings within a cohort and
retains failures at individual seeds. `scripts/compare_cohorts.py` pairs seeds
and requires identical comparison sample dates. Sample SD describes simulation
seed variability, not patients or a significance test.

All three cohorts still fail the engineering screen. The diabetic cohort's
mean RMSE is 21.42% for neutrophils, 23.68% for macrophages, 22.90% for
TGF-beta and 23.34% for MMP. These four targets are constructed curves,
including scaled normal consensus and parameter-derived trajectories, as
recorded above and in `modules/diabetic/SOURCES.yaml`. Peak normalization
tests shape and discards absolute fold differences. The failure labels are
retained as model consistency results. They do not identify clinical error,
a missing mechanism or a replacement rate.

The saved diabetic seed 42 configuration uses wound radius 12 and immune
diameter 3. The current recruitment operation computes 25 perimeter slots
and suppresses recruitment when the total tissue macrophage count reaches
25. The saved output reaches that ceiling. Total tissue census is a modeling
proxy for margin adhesion occupancy, not measured venule occupancy.
This identifies a constraint on the simulated trajectory without estimating
a new capacity or attributing the entire curve mismatch to that constraint.

The saved diabetic configurations omit `macrophage_apoptosis_factor`.
The struct default in `modules/diabetic/params.h` is 0.5, whereas today's
`profiles/diabetic.toml` specifies 0.3 and the preset application appends that
key. A rerun using today's profile therefore changes an input relative to
the frozen cohort. Comparisons must report this configuration difference.
Neither value was changed in this review.

A separately verified Griffiths et al. 2017 epidemiology workshop report
([primary source](https://pmc.ncbi.nlm.nih.gov/articles/PMC5600082/),
DOI 10.1111/bjd.15610) is recorded in `modules/immune/SOURCES.yaml`.
It supports epidemiological background. It supplies no numerical calibration
for the psoriasis profile and does not resolve the inherited BMJ citation.

### Quality checks

`literature/check_data_quality.py` enforces well-formedness, monotonic time
axis, finite values, and column-range validity (peak-normalized in [0, 1.05],
percentage in [0, 100]) across all CSVs. `literature/test_lib.py` and
`literature/test_check_data_quality.py` exercise the loaders and the checker
itself. All three are wired into `tests/test.sh`.
