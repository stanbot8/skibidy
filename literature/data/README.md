# Validation Reference Data

Digitized literature reference values for cutaneous wound healing and skin tumor growth kinetics.

## Structure

```
data/
  SOURCES.yaml       Full bibliography + dataset metadata
  README.md          This file
  consensus/         Synthesized midpoints (what comparison scripts use)
  raw/
    closure/         Re-epithelialization (3 papers)
    inflammation/    Cytokine timecourse (3 papers)
    neutrophils/     Neutrophil infiltration (2 papers)
    macrophages/     Macrophage dynamics (3 papers)
    myofibroblasts/  Alpha-SMA+ cell kinetics (4 papers)
    collagen/        Collagen accumulation (4 papers)
    tumor_growth/    BCC linear growth rate (3 papers)
    tumor_doubling/  Volume doubling time (2 papers)
    tumor_proliferation/ Ki-67 proliferation index (3 papers)
```

**[`raw/`](raw/)** contains per-paper digitized data organized by observable. Each CSV has a metadata header (source, DOI, figure, wound type, notes) followed by the data. These are the primary evidence.

**[`consensus/`](consensus/)** contains the averaged/interpolated curves derived from the raw sources. These are what the validation scripts compare against simulation output.

## Datasets

| Observable | Consensus file | Raw folder | Papers | Normalization |
|-----------|---------------|-----------|--------|---------------|
| Wound closure | [`closure_kinetics_punch_biopsy.csv`](consensus/closure_kinetics_punch_biopsy.csv) | [`raw/closure/`](raw/closure/) | 3 | Absolute (0-100%) |
| Inflammation | [`inflammation_timecourse.csv`](consensus/inflammation_timecourse.csv) | [`raw/inflammation/`](raw/inflammation/) | 3 | Peak = 1.0 (day 2) |
| Immune cells | [`immune_cell_kinetics.csv`](consensus/immune_cell_kinetics.csv) | [`raw/neutrophils/`](raw/neutrophils/) + [`raw/macrophages/`](raw/macrophages/) | 5 | Peak = 1.0 per cell type |
| Myofibroblasts | [`myofibroblast_kinetics.csv`](consensus/myofibroblast_kinetics.csv) | [`raw/myofibroblasts/`](raw/myofibroblasts/) | 4 | Peak = 1.0 (day 12) |
| Collagen | [`collagen_deposition.csv`](consensus/collagen_deposition.csv) | [`raw/collagen/`](raw/collagen/) | 4 | End = 1.0 (day 28) |

### Tumor

| Observable | Consensus file | Raw folder | Papers | Normalization |
|-----------|---------------|-----------|--------|---------------|
| Growth rate | [`tumor_growth_rate.csv`](consensus/tumor_growth_rate.csv) | [`raw/tumor_growth/`](raw/tumor_growth/) | 3 | Absolute (mm) |
| Doubling time | [`tumor_doubling_time.csv`](consensus/tumor_doubling_time.csv) | [`raw/tumor_doubling/`](raw/tumor_doubling/) | 2 | Absolute (days) |
| Proliferation index | [`tumor_proliferation_index.csv`](consensus/tumor_proliferation_index.csv) | [`raw/tumor_proliferation/`](raw/tumor_proliferation/) | 3 | Absolute (% Ki-67+) |

## Raw files by category

### [closure/](raw/closure/)
| File | Source | Observable |
|------|--------|-----------|
| [`eaglstein1978_closure.csv`](raw/closure/eaglstein1978_closure.csv) | [Eaglstein & Mertz 1978](https://doi.org/10.1111/1523-1747.ep12556814) | Re-epithelialization (porcine, moist) |
| [`cukjati2000_closure.csv`](raw/closure/cukjati2000_closure.csv) | [Cukjati et al. 2000](https://doi.org/10.1007/BF02347056) | Sigmoid model from clinical data |
| [`pastar2014_closure.csv`](raw/closure/pastar2014_closure.csv) | [Pastar et al. 2014](https://doi.org/10.1089/wound.2013.0473) | Review composite |

### [inflammation/](raw/inflammation/)
| File | Source | Observable |
|------|--------|-----------|
| [`eming2007_inflammation.csv`](raw/inflammation/eming2007_inflammation.csv) | [Eming et al. 2007](https://doi.org/10.1038/sj.jid.5700701) | Cytokine temporal profile |
| [`kondo1996_inflammation.csv`](raw/inflammation/kondo1996_inflammation.csv) | [Kondo & Ohshima 1996](https://doi.org/10.1007/BF01369816) | TNF-a + IL-1b + IL-6 (murine) |
| [`hubner1996_inflammation.csv`](raw/inflammation/hubner1996_inflammation.csv) | [Hubner et al. 1996](https://doi.org/10.1006/cyto.1996.0074) | Pro-inflammatory mRNA (murine) |

### [neutrophils/](raw/neutrophils/)
| File | Source | Observable |
|------|--------|-----------|
| [`kim2008_neutrophils.csv`](raw/neutrophils/kim2008_neutrophils.csv) | [Kim et al. 2008](https://doi.org/10.1038/sj.jid.5701223) | Ly6G+ flow cytometry (murine) |
| [`wilgus2013_neutrophils.csv`](raw/neutrophils/wilgus2013_neutrophils.csv) | [Wilgus et al. 2013](https://doi.org/10.1089/wound.2012.0383) | MPO activity (review) |

### [macrophages/](raw/macrophages/)
| File | Source | Observable |
|------|--------|-----------|
| [`krzyszczyk2018_macrophages.csv`](raw/macrophages/krzyszczyk2018_macrophages.csv) | [Krzyszczyk et al. 2018](https://doi.org/10.3389/fphys.2018.00419) | Macrophage dynamics (review) |
| [`rodero2010_macrophages.csv`](raw/macrophages/rodero2010_macrophages.csv) | [Rodero & Khosrotehrani 2010](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2933384/) | F4/80+ cells (murine) |
| [`lucas2010_macrophages.csv`](raw/macrophages/lucas2010_macrophages.csv) | [Lucas et al. 2010](https://doi.org/10.4049/jimmunol.0903356) | Macrophage depletion phases (murine) |

### [myofibroblasts/](raw/myofibroblasts/)
| File | Source | Observable |
|------|--------|-----------|
| [`desmouliere1995_myofibroblasts.csv`](raw/myofibroblasts/desmouliere1995_myofibroblasts.csv) | [Desmouliere et al. 1995](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1870783/) | Alpha-SMA+ density + apoptosis (rat) |
| [`darby2014_myofibroblasts.csv`](raw/myofibroblasts/darby2014_myofibroblasts.csv) | [Darby et al. 2014](https://doi.org/10.2147/CCID.S50046) | Myofibroblast timeline (review) |
| [`tomasek2002_myofibroblasts.csv`](raw/myofibroblasts/tomasek2002_myofibroblasts.csv) | [Tomasek et al. 2002](https://doi.org/10.1038/nrm809) | Differentiation timeline (review) |
| [`hinz2007_myofibroblasts.csv`](raw/myofibroblasts/hinz2007_myofibroblasts.csv) | [Hinz 2007](https://doi.org/10.1038/sj.jid.5700613) | Myofibroblast life cycle (review) |

### [collagen/](raw/collagen/)
| File | Source | Observable |
|------|--------|-----------|
| [`gonzalez2016_collagen.csv`](raw/collagen/gonzalez2016_collagen.csv) | [Gonzalez et al. 2016](https://doi.org/10.1590/abd1806-4841.20164741) | Tensile strength proxy (review) |
| [`zhou2013_collagen.csv`](raw/collagen/zhou2013_collagen.csv) | [Zhou et al. 2013](https://doi.org/10.1371/journal.pone.0058324) | Synthesis rate (rat) |
| [`mathew2021_collagen.csv`](raw/collagen/mathew2021_collagen.csv) | [Mathew-Steiner et al. 2021](https://doi.org/10.3390/bioengineering8050063) | Type III/I transition (review) |
| [`caetano2016_collagen.csv`](raw/collagen/caetano2016_collagen.csv) | [Caetano et al. 2016](https://doi.org/10.3109/13880209.2016.1170861) | Hydroxyproline content (rat) |

### [tumor_growth/](raw/tumor_growth/)
| File | Source | Observable |
|------|--------|-----------|
| [`fijalkowska2023_bcc_growth_meta.csv`](raw/tumor_growth/fijalkowska2023_bcc_growth_meta.csv) | [Fijalkowska et al. 2023](https://doi.org/10.5114/ada.2023.124795) | BCC linear growth rate meta-analysis (0.71 mm/month) |
| [`sykes2020_superficial_bcc.csv`](raw/tumor_growth/sykes2020_superficial_bcc.csv) | [Sykes et al. 2020](https://doi.org/10.1111/ajd.13352) | Superficial BCC dermoscopic growth |
| [`kricker2014_community_bcc.csv`](raw/tumor_growth/kricker2014_community_bcc.csv) | [Kricker et al. 2014](https://doi.org/10.1016/j.jaad.2013.11.009) | BCC size ratios over time (community) |

### [tumor_doubling/](raw/tumor_doubling/)
| File | Source | Observable |
|------|--------|-----------|
| [`al_qahtani2020_bcc_doubling.csv`](raw/tumor_doubling/al_qahtani2020_bcc_doubling.csv) | [Khoo et al. 2019](https://doi.org/10.2340/00015555-3325) | BCC volume doubling time (~148 days) |
| [`tejera2023_skin_cancer_tdt.csv`](raw/tumor_doubling/tejera2023_skin_cancer_tdt.csv) | [Tejera-Vaquerizo et al. 2023](https://doi.org/10.1016/j.ad.2022.10.034) | BCC/SCC doubling times from clinical cases |

### [tumor_proliferation/](raw/tumor_proliferation/)
| File | Source | Observable |
|------|--------|-----------|
| [`toth2012_bcc_ki67.csv`](raw/tumor_proliferation/toth2012_bcc_ki67.csv) | [Toth et al. 2012](https://doi.org/10.2478/s11756-012-0035-8) | Ki-67 index by BCC subtype (mean 27.4%) |
| [`alferraly2019_scc_ki67.csv`](raw/tumor_proliferation/alferraly2019_scc_ki67.csv) | [Alferraly et al. 2019](https://doi.org/10.3889/oamjms.2019.428) | Ki-67 index by SCC grade |
| [`alsader1996_bcc_scc_indices.csv`](raw/tumor_proliferation/alsader1996_bcc_scc_indices.csv) | [al-Sader et al. 1996](https://doi.org/10.1136/jcp.49.7.549) | Ki-67 and PCNA: BCC vs SCC comparison |

## Parameter-only datasets

These SOURCES.yaml entries validate specific parameter choices. No digitized curves; the evidence is in the cited papers.

### Diabetic wound healing (`diabetic_wound_healing`)

| Parameter | Source |
|-----------|--------|
| `m1_duration_factor=3.0` | [Mirza & Koh 2011](https://doi.org/10.1016/j.cyto.2011.06.016) |
| `resolution_factor=0.3` | [Louiselle et al. 2021](https://doi.org/10.1016/j.trsl.2021.05.006) |
| `neutrophil_factor=1.8` | [Wong et al. 2015](https://doi.org/10.1038/nm.3887) |
| `neutrophil_lifespan_factor=1.5` | [Brem & Tomic-Canic 2007](https://doi.org/10.1172/JCI32169) |
| `efferocytosis_factor=0.5` | [Khanna et al. 2010](https://doi.org/10.1371/journal.pone.0009539) |
| `prolif_factor=0.5`, `migration_factor=0.6` | [Wang & Graves 2020](https://doi.org/10.1155/2020/3714704) |
| `fibroblast_activation_factor=2.0` | [Lerman et al. 2003](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1851127/) |
| `collagen_factor=0.4` | [Goldberg et al. 2007](https://doi.org/10.1038/sj.jid.5700890), [Spanheimer 1988](https://doi.org/10.1016/0026-0495(88)90050-9) |
| `perfusion_basal=0.7` | [Dinh & Veves 2005](https://doi.org/10.1177/1534734605280130) |
| `water_recovery_rate=0.02` | [Sakai et al. 2005](https://doi.org/10.1111/j.1365-2133.2005.06756.x), [Li et al. 2017](https://doi.org/10.1097/MD.0000000000008611) |
| `baseline_inflammation=0.0005` | [Dinh et al. 2012](https://doi.org/10.2337/db12-0227) |

### Scar formation (`scar_formation_parameters`)

| Parameter | Source |
|-----------|--------|
| `fibroblast_lifespan`, `_min_lifespan` | [Desmouliere et al. 1995](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1870783/) |
| `activation_threshold`, `myofibroblast_threshold` | [Tomasek et al. 2002](https://doi.org/10.1038/nrm809) |
| `myofibroblast_delay=480` | [Van De Water et al. 2013](https://doi.org/10.1089/wound.2012.0393) |
| `apoptosis_threshold=0.05` | [Hinz 2007](https://doi.org/10.1038/sj.jid.5700613) |
| `tgfb_diffusion`, `tgfb_decay`, `collagen_deposition_rate` | [Murphy et al. 2012](https://doi.org/10.1007/s11538-011-9712-y) |
| `fibroblast_migration_speed` | [Dallon et al. 2001](https://doi.org/10.1046/j.1524-475X.2001.00278.x) |
| `m2_tgfb_rate=0.003` | [Koh & DiPietro 2011](https://doi.org/10.1017/S1462399411001943) |
| `scar_proportional_enabled` | [Ogawa 2017](https://doi.org/10.3390/ijms18030606), [Gauglitz et al. 2011](https://doi.org/10.2119/molmed.2009.00153) |

## DOI verification status

All 116 unique DOIs verified against CrossRef (resolution + title cross-check). Last checked 2026-02-25.

| Status | Count |
|--------|-------|
| :white_check_mark: Verified | 116 |
| :x: Broken | 0 |

<details>
<summary>Full verification table (116 DOIs)</summary>

| Source | DOI | Status |
|--------|-----|--------|
| Adams MP 2015 | [`10.1371/journal.pone.0116751`](https://doi.org/10.1371/journal.pone.0116751) | :white_check_mark: |
| Adra S 2010 | [`10.1371/journal.pone.0008511`](https://doi.org/10.1371/journal.pone.0008511) | :white_check_mark: |
| al-Sader MH 1996 | [`10.1136/jcp.49.7.549`](https://doi.org/10.1136/jcp.49.7.549) | :white_check_mark: |
| Alferraly IT 2019 | [`10.3889/oamjms.2019.428`](https://doi.org/10.3889/oamjms.2019.428) | :white_check_mark: |
| Armstrong DG 2005 | [`10.1016/S0140-6736(05)67695-7`](https://doi.org/10.1016/S0140-6736(05)67695-7) | :white_check_mark: |
| Ashcroft GS 2012 | [`10.1111/j.1524-475X.2011.00748.x`](https://doi.org/10.1111/j.1524-475X.2011.00748.x) | :white_check_mark: |
| Barrandon Y 1985 | [`10.1073/pnas.82.16.5390`](https://doi.org/10.1073/pnas.82.16.5390) | :white_check_mark: |
| Bemelmans MH 1996 | [`10.1615/CritRevImmunol.v16.i1.10`](https://doi.org/10.1615/CritRevImmunol.v16.i1.10) | :white_check_mark: |
| Bierhaus A 2005 | [`10.1007/s00109-005-0688-7`](https://doi.org/10.1007/s00109-005-0688-7) | :white_check_mark: |
| Bikle DD 2012 | [`10.1586/eem.12.34`](https://doi.org/10.1586/eem.12.34) | :white_check_mark: |
| Bjarnsholt T 2008 | [`10.1111/j.1524-475X.2007.00283.x`](https://doi.org/10.1111/j.1524-475X.2007.00283.x) | :white_check_mark: |
| Brem H 2006 | [`10.1097/01.prs.0000225459.93750.29`](https://doi.org/10.1097/01.prs.0000225459.93750.29) | :white_check_mark: |
| Brem H 2007 | [`10.1172/JCI32169`](https://doi.org/10.1172/JCI32169) | :white_check_mark: |
| Brownlee 2005 | [`10.2337/diabetes.54.6.1615`](https://doi.org/10.2337/diabetes.54.6.1615) | :white_check_mark: |
| Caetano GF 2016 | [`10.3109/13880209.2016.1170861`](https://doi.org/10.3109/13880209.2016.1170861) | :white_check_mark: |
| Canedo-Dorantes L 2019 | [`10.1155/2019/3706315`](https://doi.org/10.1155/2019/3706315) | :white_check_mark: |
| Cao Y 2017 | [`10.1155/2017/9328347`](https://doi.org/10.1155/2017/9328347) | :white_check_mark: |
| Catrina SB 2004 | [`10.2337/diabetes.53.12.3226`](https://doi.org/10.2337/diabetes.53.12.3226) | :white_check_mark: |
| Clark 1990 | [`10.1111/1523-1747.ep12876104`](https://doi.org/10.1111/1523-1747.ep12876104) | :white_check_mark: |
| Clayton E 2007 | [`10.1038/nature05574`](https://doi.org/10.1038/nature05574) | :white_check_mark: |
| Clayton SM 2024 | [`10.1089/wound.2023.0149`](https://doi.org/10.1089/wound.2023.0149) | :white_check_mark: |
| Cukjati D 2000 | [`10.1007/BF02347056`](https://doi.org/10.1007/BF02347056) | :white_check_mark: |
| Dallon JC 2001 | [`10.1046/j.1524-475X.2001.00278.x`](https://doi.org/10.1046/j.1524-475X.2001.00278.x) | :white_check_mark: |
| Darby IA 2014 | [`10.2147/CCID.S50046`](https://doi.org/10.2147/CCID.S50046) | :white_check_mark: |
| Davis SC 2008 | [`10.1111/j.1524-475X.2007.00303.x`](https://doi.org/10.1111/j.1524-475X.2007.00303.x) | :white_check_mark: |
| Dinh T 2005 | [`10.1177/1534734605280130`](https://doi.org/10.1177/1534734605280130) | :white_check_mark: |
| Dinh T 2012 | [`10.2337/db12-0227`](https://doi.org/10.2337/db12-0227) | :white_check_mark: |
| Dover R 1988 | [`10.1242/jcs.89.3.359`](https://doi.org/10.1242/jcs.89.3.359) | :white_check_mark: |
| Eaglstein WH 1978 | [`10.1111/1523-1747.ep12556814`](https://doi.org/10.1111/1523-1747.ep12556814) | :white_check_mark: |
| Eming SA 2007 | [`10.1038/sj.jid.5700701`](https://doi.org/10.1038/sj.jid.5700701) | :white_check_mark: |
| Eming SA 2014 | [`10.1126/scitranslmed.3009337`](https://doi.org/10.1126/scitranslmed.3009337) | :white_check_mark: |
| Falanga 2005 | [`10.1016/S0140-6736(05)67700-8`](https://doi.org/10.1016/S0140-6736(05)67700-8) | :white_check_mark: |
| Farage MA 2013 | [`10.1089/wound.2011.0356`](https://doi.org/10.1089/wound.2011.0356) | :white_check_mark: |
| Fedorko L 2016 | [`10.2337/dc15-2001`](https://doi.org/10.2337/dc15-2001) | :white_check_mark: |
| Fijalkowska M 2023 | [`10.5114/ada.2023.124795`](https://doi.org/10.5114/ada.2023.124795) | :white_check_mark: |
| Finch PW 2004 | [`10.1016/S0065-230X(04)91003-2`](https://doi.org/10.1016/S0065-230X(04)91003-2) | :white_check_mark: |
| Flegg JA 2012 | [`10.1016/j.jtbi.2012.01.043`](https://doi.org/10.1016/j.jtbi.2012.01.043) | :white_check_mark: |
| Galiano RD 2004 | [`10.1111/j.1067-1927.2004.12404.x`](https://doi.org/10.1111/j.1067-1927.2004.12404.x) | :white_check_mark: |
| Gauglitz GG 2011 | [`10.2119/molmed.2009.00153`](https://doi.org/10.2119/molmed.2009.00153) | :white_check_mark: |
| Gibson B 2018 | [`10.1098/rspb.2018.0789`](https://doi.org/10.1098/rspb.2018.0789) | :white_check_mark: |
| Gilchrest 1983 | [`10.1111/1523-1747.ep12541084`](https://doi.org/10.1111/1523-1747.ep12541084) | :white_check_mark: |
| Goldberg MT 2007 | [`10.1038/sj.jid.5700890`](https://doi.org/10.1038/sj.jid.5700890) | :white_check_mark: |
| Gonzalez ACDO 2016 | [`10.1590/abd1806-4841.20164741`](https://doi.org/10.1590/abd1806-4841.20164741) | :white_check_mark: |
| Goren I 2007 | [`10.1038/sj.jid.5700842`](https://doi.org/10.1038/sj.jid.5700842) | :white_check_mark: |
| Grabe N 2005 | [`10.1093/bioinformatics/bti585`](https://doi.org/10.1093/bioinformatics/bti585) | :white_check_mark: |
| Grinnell 1984 | [`10.1002/jcb.240260206`](https://doi.org/10.1002/jcb.240260206) | :white_check_mark: |
| Hinz 2007 | [`10.1038/sj.jid.5700613`](https://doi.org/10.1038/sj.jid.5700613) | :white_check_mark: |
| Hubner G 1996 | [`10.1006/cyto.1996.0074`](https://doi.org/10.1006/cyto.1996.0074) | :white_check_mark: |
| Hynes 1990 | [`10.1007/978-1-4612-3264-3`](https://doi.org/10.1007/978-1-4612-3264-3) | :white_check_mark: |
| Iizuka 1994 | [`10.1016/0923-1811(94)90057-4`](https://doi.org/10.1016/0923-1811(94)90057-4) | :white_check_mark: |
| James GA 2008 | [`10.1111/j.1524-475X.2007.00321.x`](https://doi.org/10.1111/j.1524-475X.2007.00321.x) | :white_check_mark: |
| Jesaitis AJ 2003 | [`10.4049/jimmunol.171.8.4329`](https://doi.org/10.4049/jimmunol.171.8.4329) | :white_check_mark: |
| Jetten N 2014 | [`10.1007/s10456-013-9381-6`](https://doi.org/10.1007/s10456-013-9381-6) | :white_check_mark: |
| Johnson KE 2014 | [`10.1089/wound.2013.0517`](https://doi.org/10.1089/wound.2013.0517) | :white_check_mark: |
| Jones PH 1993 | [`10.1016/0092-8674(93)90251-K`](https://doi.org/10.1016/0092-8674(93)90251-K) | :white_check_mark: |
| Junker JPE 2013 | [`10.1089/wound.2012.0412`](https://doi.org/10.1089/wound.2012.0412) | :white_check_mark: |
| Khanna S 2010 | [`10.1371/journal.pone.0009539`](https://doi.org/10.1371/journal.pone.0009539) | :white_check_mark: |
| Khoo ABS 2019 | [`10.2340/00015555-3325`](https://doi.org/10.2340/00015555-3325) | :white_check_mark: |
| Kim MH 2008 | [`10.1038/sj.jid.5701223`](https://doi.org/10.1038/sj.jid.5701223) | :white_check_mark: |
| Koh TJ 2011 | [`10.1017/S1462399411001943`](https://doi.org/10.1017/S1462399411001943) | :white_check_mark: |
| Kondo T 1996 | [`10.1007/BF01369816`](https://doi.org/10.1007/BF01369816) | :white_check_mark: |
| Kricker A 2014 | [`10.1016/j.jaad.2013.11.009`](https://doi.org/10.1016/j.jaad.2013.11.009) | :white_check_mark: |
| Krzyszczyk P 2018 | [`10.3389/fphys.2018.00419`](https://doi.org/10.3389/fphys.2018.00419) | :white_check_mark: |
| Ladwig GP 2002 | [`10.1046/j.1524-475x.2002.10903.x`](https://doi.org/10.1046/j.1524-475x.2002.10903.x) | :white_check_mark: |
| Lammermann T 2008 | [`10.1038/nature06887`](https://doi.org/10.1038/nature06887) | :white_check_mark: |
| Li A 1998 | [`10.1073/pnas.95.7.3902`](https://doi.org/10.1073/pnas.95.7.3902) | :white_check_mark: |
| Li X 2017 | [`10.1097/MD.0000000000008611`](https://doi.org/10.1097/MD.0000000000008611) | :white_check_mark: |
| Lobmann R 2002 | [`10.1007/s00125-002-0868-8`](https://doi.org/10.1007/s00125-002-0868-8) | :white_check_mark: |
| Londahl M 2010 | [`10.2337/dc09-1754`](https://doi.org/10.2337/dc09-1754) | :white_check_mark: |
| Louiselle AE 2021 | [`10.1016/j.trsl.2021.05.006`](https://doi.org/10.1016/j.trsl.2021.05.006) | :white_check_mark: |
| Lucas T 2010 | [`10.4049/jimmunol.0903356`](https://doi.org/10.4049/jimmunol.0903356) | :white_check_mark: |
| Lulevich V 2010 | [`10.1016/j.ultramic.2010.07.009`](https://doi.org/10.1016/j.ultramic.2010.07.009) | :white_check_mark: |
| Mathew-Steiner SS 2021 | [`10.3390/bioengineering8050063`](https://doi.org/10.3390/bioengineering8050063) | :white_check_mark: |
| McDougall S 2006 | [`10.1098/rsta.2006.1773`](https://doi.org/10.1098/rsta.2006.1773) | :white_check_mark: |
| Menon GK 1985 | [`10.1111/1523-1747.ep12273485`](https://doi.org/10.1111/1523-1747.ep12273485) | :white_check_mark: |
| Michaels JT 2007 | [`10.1111/j.1524-475X.2007.00273.x`](https://doi.org/10.1111/j.1524-475X.2007.00273.x) | :white_check_mark: |
| Mirza R 2011 | [`10.1016/j.cyto.2011.06.016`](https://doi.org/10.1016/j.cyto.2011.06.016) | :white_check_mark: |
| Morykwas MJ 1997 | [`10.1097/00000637-199706000-00001`](https://doi.org/10.1097/00000637-199706000-00001) | :white_check_mark: |
| Mosser DM 2008 | [`10.1111/j.1600-065X.2008.00706.x`](https://doi.org/10.1111/j.1600-065X.2008.00706.x) | :white_check_mark: |
| Murphy KE 2012 | [`10.1007/s11538-011-9712-y`](https://doi.org/10.1007/s11538-011-9712-y) | :white_check_mark: |
| Nagase H 1999 | [`10.1074/jbc.274.31.21491`](https://doi.org/10.1074/jbc.274.31.21491) | :white_check_mark: |
| Ogawa 2017 | [`10.3390/ijms18030606`](https://doi.org/10.3390/ijms18030606) | :white_check_mark: |
| Oyler-Yaniv A 2017 | [`10.1016/j.immuni.2017.03.011`](https://doi.org/10.1016/j.immuni.2017.03.011) | :white_check_mark: |
| Pastar I 2014 | [`10.1089/wound.2013.0473`](https://doi.org/10.1089/wound.2013.0473) | :white_check_mark: |
| Pinnagoda J 1990 | [`10.1111/j.1600-0536.1990.tb01553.x`](https://doi.org/10.1111/j.1600-0536.1990.tb01553.x) | :white_check_mark: |
| Potten CS 1988 | [`10.1242/jcs.1988.supplement_10.4`](https://doi.org/10.1242/jcs.1988.supplement_10.4) | :white_check_mark: |
| Rasik AM 2000 | [`10.1046/j.1365-2613.2000.00158.x`](https://doi.org/10.1046/j.1365-2613.2000.00158.x) | :white_check_mark: |
| Ravichandran 2010 | [`10.1084/jem.20101157`](https://doi.org/10.1084/jem.20101157) | :white_check_mark: |
| Rubin JS 1989 | [`10.1073/pnas.86.3.802`](https://doi.org/10.1073/pnas.86.3.802) | :white_check_mark: |
| Safferling K 2013 | [`10.1083/jcb.201212020`](https://doi.org/10.1083/jcb.201212020) | :white_check_mark: |
| Sakai S 2005 | [`10.1111/j.1365-2133.2005.06756.x`](https://doi.org/10.1111/j.1365-2133.2005.06756.x) | :white_check_mark: |
| Savill JS 1989 | [`10.1172/JCI113970`](https://doi.org/10.1172/JCI113970) | :white_check_mark: |
| Schugart RC 2008 | [`10.1073/pnas.0711642105`](https://doi.org/10.1073/pnas.0711642105) | :white_check_mark: |
| Schwindt DA 1998 | [`10.1046/j.1523-1747.1998.00321.x`](https://doi.org/10.1046/j.1523-1747.1998.00321.x) | :white_check_mark: |
| Sgonc R 2013 | [`10.1159/000342344`](https://doi.org/10.1159/000342344) | :white_check_mark: |
| Singer AJ 1999 | [`10.1056/NEJM199909023411006`](https://doi.org/10.1056/NEJM199909023411006) | :white_check_mark: |
| Siqueira MF 2010 | [`10.1007/s00125-009-1529-y`](https://doi.org/10.1007/s00125-009-1529-y) | :white_check_mark: |
| Smiell JM 1998 | [`10.1046/j.1524-475X.1999.00335.x`](https://doi.org/10.1046/j.1524-475X.1999.00335.x) | :white_check_mark: |
| Smith GN Jr 1999 | [`10.1002/1529-0131(199906)42:6<1140::AID-ANR10>3.0.CO;2-7`](https://doi.org/10.1002/1529-0131(199906)42:6<1140::AID-ANR10>3.0.CO;2-7) | :white_check_mark: |
| Spanheimer 1988 | [`10.1016/0026-0495(88)90050-9`](https://doi.org/10.1016/0026-0495(88)90050-9) | :white_check_mark: |
| Steed 2006 | [`10.1097/01.prs.0000222526.21512.4c`](https://doi.org/10.1097/01.prs.0000222526.21512.4c) | :white_check_mark: |
| Stucker M 2002 | [`10.1113/jphysiol.2001.013067`](https://doi.org/10.1113/jphysiol.2001.013067) | :white_check_mark: |
| Sun T 2007 | [`10.1098/rsif.2007.0227`](https://doi.org/10.1098/rsif.2007.0227) | :white_check_mark: |
| Sykes AJ 2020 | [`10.1111/ajd.13352`](https://doi.org/10.1111/ajd.13352) | :white_check_mark: |
| Tejera-Vaquerizo A 2023 | [`10.1016/j.ad.2022.10.034`](https://doi.org/10.1016/j.ad.2022.10.034) | :white_check_mark: |
| Thangarajah H 2009 | [`10.1073/pnas.0906670106`](https://doi.org/10.1073/pnas.0906670106) | :white_check_mark: |
| Tomasek JJ 2002 | [`10.1038/nrm809`](https://doi.org/10.1038/nrm809) | :white_check_mark: |
| Toth DP 2012 | [`10.2478/s11756-012-0035-8`](https://doi.org/10.2478/s11756-012-0035-8) | :white_check_mark: |
| Van De Water L 2013 | [`10.1089/wound.2012.0393`](https://doi.org/10.1089/wound.2012.0393) | :white_check_mark: |
| Wang Y 2020 | [`10.1155/2020/3714704`](https://doi.org/10.1155/2020/3714704) | :white_check_mark: |
| Werner S 1992 | [`10.1073/pnas.89.15.6896`](https://doi.org/10.1073/pnas.89.15.6896) | :white_check_mark: |
| Wetzler C 2000 | [`10.1046/j.1523-1747.2000.00029.x`](https://doi.org/10.1046/j.1523-1747.2000.00029.x) | :white_check_mark: |
| Wilgus TA 2013 | [`10.1089/wound.2012.0383`](https://doi.org/10.1089/wound.2012.0383) | :white_check_mark: |
| Winter 1962 | [`10.1038/193293a0`](https://doi.org/10.1038/193293a0) | :white_check_mark: |
| Wong SL 2015 | [`10.1038/nm.3887`](https://doi.org/10.1038/nm.3887) | :white_check_mark: |
| Zhou S 2013 | [`10.1371/journal.pone.0058324`](https://doi.org/10.1371/journal.pone.0058324) | :white_check_mark: |

</details>

## Sources

Full citations with DOI/PMC links in [`SOURCES.yaml`](SOURCES.yaml).

## Format

**Consensus files**: Plain CSV. Column headers in row 1, numeric data from row 2. No comments.

**Raw files**: CSV with metadata header rows (key,value pairs) before the data columns. Each file identifies its source paper, DOI, figure number, wound type, and notes.
