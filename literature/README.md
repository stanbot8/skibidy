> [Home](../README.md) / Validation

# Validation

Compares simulation output against digitized literature data and checks source integrity.

## Running

```bash
# Full pipeline (source check + sim validation + plots)
python3 literature/validate_all.py output/skibidy/metrics.csv

# Source integrity only (no sim data needed)
python3 literature/check_sources.py
```

`validate_all.py` runs the source check first, then loads simulation metrics and validates whichever modules are present (wound, fibroblast, tumor).

## Scripts

| Script | Purpose |
|--------|---------|
| [`validate_all.py`](validate_all.py) | Single entry point: source check, compute, print, plot |
| [`check_sources.py`](check_sources.py) | SOURCES.yaml structural integrity + DOI cross-check |
| [`lib.py`](lib.py) | Shared utilities: CSV loading, interpolation, RMSE, plotting |
| [`compare_wound.py`](compare_wound.py) | Standalone wound healing comparison |
| [`compare_immune.py`](compare_immune.py) | Standalone immune cell kinetics comparison |
| [`compare_fibroblast.py`](compare_fibroblast.py) | Standalone fibroblast/collagen comparison |
| [`compare_tumor.py`](compare_tumor.py) | Standalone tumor growth comparison |

## Source integrity checks

`check_sources.py` parses [`data/SOURCES.yaml`](data/SOURCES.yaml) and validates:

| Check | Level | What |
|-------|-------|------|
| YAML parse | ERROR | File loads cleanly |
| `description` field | ERROR | Every dataset has a description |
| `sources` list | ERROR | Every dataset has at least one citation |
| Citation fields | ERROR | Each source has `id`, `authors`, `year`, `title` |
| File references | ERROR | `consensus` and `raw_files` paths resolve to existing files |
| DOI/PMC/URL | WARN | At least one locator per source |
| Parameter notes | WARN | Parameter-only datasets have `notes` annotations |
| Config DOI cross-check | WARN | Inline `doi:10.xxx` comments in `bdm.toml` and `profiles/*.toml` match SOURCES.yaml |

## Reference datasets

### Timeseries (digitized curves)

| Observable | Consensus CSV | Sources |
|-----------|--------------|---------|
| Wound closure | [`closure_kinetics_punch_biopsy.csv`](data/consensus/closure_kinetics_punch_biopsy.csv) | [Eaglstein 1978](https://doi.org/10.1111/1523-1747.ep12556814), [Cukjati 2000](https://doi.org/10.1007/BF02347056), [Pastar 2014](https://doi.org/10.1089/wound.2013.0473) |
| Inflammation | [`inflammation_timecourse.csv`](data/consensus/inflammation_timecourse.csv) | [Eming 2007](https://doi.org/10.1038/sj.jid.5700701), [Kondo 1996](https://doi.org/10.1007/BF01369816), [Hubner 1996](https://doi.org/10.1006/cyto.1996.0074), [Koh 2011](https://doi.org/10.1017/S1462399411001943) |
| Immune cells | [`immune_cell_kinetics.csv`](data/consensus/immune_cell_kinetics.csv) | [Kim 2008](https://doi.org/10.1038/sj.jid.5701223), [Wilgus 2013](https://doi.org/10.1089/wound.2012.0383), [Krzyszczyk 2018](https://doi.org/10.3389/fphys.2018.00419), [Rodero 2010](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2933384/), [Lucas 2010](https://doi.org/10.4049/jimmunol.0903356) |
| Myofibroblasts | [`myofibroblast_kinetics.csv`](data/consensus/myofibroblast_kinetics.csv) | [Desmouliere 1995](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1870783/), [Darby 2014](https://doi.org/10.2147/CCID.S50046), [Tomasek 2002](https://doi.org/10.1038/nrm809), [Hinz 2007](https://doi.org/10.1038/sj.jid.5700613) |
| Collagen | [`collagen_deposition.csv`](data/consensus/collagen_deposition.csv) | [Gonzalez 2016](https://doi.org/10.1590/abd1806-4841.20164741), [Zhou 2013](https://doi.org/10.1371/journal.pone.0058324), [Mathew-Steiner 2021](https://doi.org/10.3390/bioengineering8050063), [Caetano 2016](https://doi.org/10.3109/13880209.2016.1170861) |
| Tumor growth | [`tumor_growth_rate.csv`](data/consensus/tumor_growth_rate.csv) | [Fijalkowska 2023](https://doi.org/10.5114/ada.2023.124795), [Sykes 2020](https://doi.org/10.1111/ajd.13352), [Kricker 2014](https://doi.org/10.1016/j.jaad.2013.11.009) |
| Tumor doubling | [`tumor_doubling_time.csv`](data/consensus/tumor_doubling_time.csv) | [Khoo 2019](https://doi.org/10.2340/00015555-3325), [Tejera-Vaquerizo 2023](https://doi.org/10.1016/j.ad.2022.10.034) |
| Proliferation index | [`tumor_proliferation_index.csv`](data/consensus/tumor_proliferation_index.csv) | [Toth 2012](https://doi.org/10.2478/s11756-012-0035-8), [Alferraly 2019](https://doi.org/10.3889/oamjms.2019.428), [al-Sader 1996](https://doi.org/10.1136/jcp.49.7.549) |

See [`data/README.md`](data/README.md) for per-file details and raw data tables.

### Parameter-only (no digitized curves)

These datasets validate specific parameter choices via literature citations. No consensus CSVs; the evidence is in the cited papers.

#### Diabetic wound healing

| Parameter | Value | Source | Evidence |
|-----------|-------|--------|----------|
| `diabetic_m1_duration_factor` | 3.0 | [Mirza & Koh 2011](https://doi.org/10.1016/j.cyto.2011.06.016) | Persistent M1 markers (iNOS, TNF-alpha) in diabetic wounds |
| `diabetic_resolution_factor` | 0.3 | [Louiselle et al. 2021](https://doi.org/10.1016/j.trsl.2021.05.006) | Failed M1-to-M2 switch; sustained pro-inflammatory cytokines |
| `diabetic_neutrophil_factor` | 1.8 | [Wong et al. 2015](https://doi.org/10.1038/nm.3887) | Hyperglycemia-primed NETosis; ~2x neutrophil burden |
| `diabetic_neutrophil_lifespan_factor` | 1.5 | [Brem & Tomic-Canic 2007](https://doi.org/10.1172/JCI32169) | Delayed neutrophil apoptosis; prolonged protease release |
| `diabetic_efferocytosis_factor` | 0.5 | [Khanna et al. 2010](https://doi.org/10.1371/journal.pone.0009539) | ~50% reduction in phagocytic clearance |
| `diabetic_prolif_factor` | 0.5 | [Wang & Graves 2020](https://doi.org/10.1155/2020/3714704) | PI3K/FAK pathway inhibition by hyperglycemia |
| `diabetic_migration_factor` | 0.6 | [Wang & Graves 2020](https://doi.org/10.1155/2020/3714704) | ClC-2/Rac1 signaling deficits |
| `diabetic_fibroblast_activation_factor` | 2.0 | [Lerman et al. 2003](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1851127/) | Delayed activation, reduced VEGF, impaired hypoxia response |
| `diabetic_collagen_factor` | 0.4 | [Goldberg et al. 2007](https://doi.org/10.1038/sj.jid.5700890), [Spanheimer 1988](https://doi.org/10.1016/0026-0495(88)90050-9) | TNF-alpha suppresses alpha-SMA; collagen ~58% of control |
| `diabetic_fibroblast_lifespan_factor` | 0.6 | [Lerman et al. 2003](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1851127/) | Oxidative stress-driven senescence |
| `perfusion_basal` | 0.7 | [Dinh & Veves 2005](https://doi.org/10.1177/1534734605280130) | Capillary density -22%, lumen area -58% |
| `perfusion_angio_rate` | 0.002 | [Brem et al. 2006](https://doi.org/10.1097/01.prs.0000225459.93750.29) | Impaired VEGF/FGF signaling |
| `water_recovery_rate` | 0.02 | [Sakai et al. 2005](https://doi.org/10.1111/j.1365-2133.2005.06756.x), [Li et al. 2017](https://doi.org/10.1097/MD.0000000000008611) | Reduced SC hydration + impaired barrier |
| `diabetic_baseline_inflammation` | 0.001 | [Bierhaus et al. 2005](https://doi.org/10.1007/s00109-005-0688-7), [Dinh et al. 2012](https://doi.org/10.2337/db12-0227) | AGE/RAGE-driven sterile inflammation |

#### Scar formation parameters

| Parameter | Value | Source | Evidence |
|-----------|-------|--------|----------|
| `fibroblast_min_lifespan` | 1680 (7d) | [Desmouliere et al. 1995](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1870783/) | Myofibroblasts appear day 4-6, apoptosis begins ~day 12 |
| `fibroblast_lifespan` | 6720 (28d) | [Desmouliere et al. 1995](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1870783/) | Largely resolved by day 30 |
| `fibroblast_activation_threshold` | 0.005 | [Tomasek et al. 2002](https://doi.org/10.1038/nrm809) | Two-stage model: TGF-beta + mechanical tension gates (rescaled) |
| `fibroblast_myofibroblast_threshold` | 0.015 | [Tomasek et al. 2002](https://doi.org/10.1038/nrm809) | Sequential TGF-beta threshold for alpha-SMA acquisition (rescaled) |
| `fibroblast_myofibroblast_delay` | 1200 (5d) | [Van De Water et al. 2013](https://doi.org/10.1089/wound.2012.0393) | 3-5 days in vitro; shifts myofibroblast peak to day 10-12 |
| `fibroblast_apoptosis_threshold` | 0.003 | [Hinz 2007](https://doi.org/10.1038/sj.jid.5700613) | Apoptosis triggered by loss of mechanical load + low TGF-beta (rescaled) |
| `tgfb_diffusion` | 0.03 | [Murphy et al. 2012](https://doi.org/10.1007/s11538-011-9712-y) | Mechanochemical model parameter table |
| `tgfb_decay` | 0.005 | [Murphy et al. 2012](https://doi.org/10.1007/s11538-011-9712-y) | Growth factor kinetics calibration |
| `collagen_deposition_rate` | 0.002 | [Murphy et al. 2012](https://doi.org/10.1007/s11538-011-9712-y) | Collagen production rate calibration |
| `fibroblast_migration_speed` | 1.0 | [Dallon et al. 2001](https://doi.org/10.1046/j.1524-475X.2001.00278.x) | TGF-beta modulates fibroblast speed |
| `m2_tgfb_rate` | 0.003 | [Koh & DiPietro 2011](https://doi.org/10.1017/S1462399411001943) | M2 macrophages are primary TGF-beta source |
| `scar_proportional_enabled` | (flag) | [Ogawa 2017](https://doi.org/10.3390/ijms18030606), [Gauglitz et al. 2011](https://doi.org/10.2119/molmed.2009.00153) | Scar severity correlates with inflammation integral |

## Output

Plots are saved to `output/plots/`:

| File | Contents |
|------|----------|
| `validation_dashboard.png` | Combined multi-panel dashboard |
| `wound_validation.png` | Closure, inflammation, immune cells, stratification |
| `fibroblast_validation.png` | Myofibroblast count + collagen accumulation |
| `tumor_validation.png` | Growth rate + doubling time |
