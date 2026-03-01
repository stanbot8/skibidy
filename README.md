# Skibidy

**Skin BioDynaMo (SkiBiDy)** is a hybrid agent-continuum simulation of skin tissue biology built on [BioDynaMo](https://biodynamo.org). Models wound healing, immune response, fibroblast/collagen dynamics, scar formation, vascular perfusion, hemostasis, tumor growth, and diabetic impairment.

![Wound healing simulation](docs/skibidy.gif?v=2)

## Overview

Healthy skin runs as a composite field coupling 23 PDEs with no agents. When an event occurs (wound, infection, tumor), cells spawn from local field state, interact with the fields, and dissolve back once stable. This is called **UWYN** (Use What You Need), meaning the simulation only creates agents where the biology demands resolution.

```
Corneum    [continuum]  barrier, desquamation
Granulosum [continuum]  keratohyalin, tight junctions
Spinosum   [continuum]  desmosomes; agents on event
Basale     [continuum]  stem/TA cells on event
---------- basement membrane ----------
Dermis     [continuum]  vasculature, O2/KGF, collagen; agents on event
```

The PDE channels (O2, water, calcium, KGF, stratum, vascular perfusion, inflammation [pro/anti split], immune pressure, TGF-beta, collagen, scar, MMP, fibronectin, elastin, hyaluronan, VEGF, dermis, pH, fibrin, biofilm, tumor) are cross-coupled so that behaviors like wound closure rate, scar formation, and angiogenesis emerge from local interactions rather than global parameters.

## Quick start

```bash
source <path_to_biodynamo>/bin/thisbdm.sh
./run.sh                                     # interactive menu
```

Pick a scenario:

```bash
./run.sh --preset=wound                # punch biopsy wound healing (~30 days)
./run.sh --preset=tumor                # basal cell carcinoma growth
./run.sh --preset=diabetic_wound       # chronic diabetic ulcer (~42 days)
./run.sh --skin=aged --preset=wound    # aged skin + wound
./run.sh --compare                     # normal vs diabetic side-by-side
```

Run the test suite:

```bash
./tests/test.sh                        # 118 unit tests
```

## Validation

Validated against published literature across 6 observables, backed by 134 DOI-linked source papers in [`SOURCES.yaml`](literature/data/SOURCES.yaml):

| Observable | Key references |
|-----------|---------------|
| Wound closure | Eaglstein 1978, Cukjati 2000, Pastar 2014 |
| Inflammation | Eming 2007, Koh & DiPietro 2011 |
| Neutrophil/macrophage kinetics | Kim 2008, Wilgus 2013, Krzyszczyk 2018 |
| Myofibroblasts + collagen | Desmouliere 1995, Darby 2014, Tomasek 2002 |
| Tumor growth + Ki-67 | Khoo 2019, Toth 2012 |

Run a 10-simulation consensus with literature comparison:

```bash
python3 batch/batch.py -n 10 --skin normal --preset wound --validate
```

Additional validation tools:

```bash
python3 literature/validate_all.py                      # RMSE dashboard
python3 literature/check_sources.py --verify-dois       # verify all DOI links
python3 batch/sweep.py batch/configs/cytokine_rate.toml  # parameter sweep
```

## Studies

Five packaged study scripts, each self-contained (builds, runs, collects, reports):

| Study | Script | Description |
|-------|--------|-------------|
| Diabetic treatments | [diabetic-study.sh](studies/diabetic-study.sh) | Baseline + 8 therapeutic interventions, Excel workbook |
| Adaptive combos | [adaptive-study.sh](studies/adaptive-study.sh) | Surrogate-guided combination search with synergy detection |
| Skin comparison | [skin-comparison-study.sh](studies/skin-comparison-study.sh) | Normal vs aged vs diabetic healing |
| Tumor growth | [tumor-study.sh](studies/tumor-study.sh) | BCC growth rate and proliferation kinetics |
| Scenario runner | [run-scenarios.sh](studies/run-scenarios.sh) | Run novel experiment scenarios (see below) |

```bash
bash studies/diabetic-study.sh           # ~3-4h, 8 treatments
bash studies/run-scenarios.sh            # all 7 scenarios
bash studies/run-scenarios.sh --quick    # quick pass (2 runs each)
```

Pre-generated results in [studies/diabetic-example/](studies/diabetic-example/) and [studies/adaptive-example/](studies/adaptive-example/).

## Experiment scenarios

Seven novel TOML-defined experiments in [`scenarios/`](scenarios/), driven by a generic [scenario runner](scripts/study/scenario_runner.py):

| Scenario | Configs | Question |
|----------|---------|----------|
| [Severity spectrum](scenarios/severity_spectrum.toml) | 5 severity levels (0.5x to 1.5x) | Is there a critical severity threshold for non-healing? |
| [Biofilm infection](scenarios/biofilm_infection.toml) | Early/late biofilm, +doxycycline | Does biofilm create a truly non-healing wound? |
| [Treatment timing](scenarios/treatment_timing.toml) | 3 treatments x 4 delay windows | Is early intervention critical, or can late treatment rescue? |
| [Wound size](scenarios/wound_size.toml) | 1.5mm to 8mm radius | Does healing scale linearly with wound area? |
| [Aged + diabetic](scenarios/aged_diabetic.toml) | 4 phenotypes (normal/aged/diabetic/both) | Are impairments additive or synergistic? |
| [Chronic wound](scenarios/chronic_wound.toml) | 90-day severe + biofilm + rescue | Can combination therapy rescue a chronic wound? |
| [Immune tuning](scenarios/immune_tuning.toml) | Restore one immune axis at a time | Which immune axis is the dominant barrier to healing? |

```bash
python3 scripts/study/scenario_runner.py scenarios/wound_size.toml --runs=5
bash studies/run-scenarios.sh scenarios/immune_tuning.toml
```

Output goes to `output/scenarios/<scenario_name>/` with per-config consensus CSVs and a comparison summary.

## Modules

Each module is self-contained in `modules/` with its own `config.toml` and source files:

| Module | Default | What it does |
|--------|---------|--------------|
| Tissue | on | Keratinocyte lifecycle, calcium gradient, O2/water/KGF fields |
| Wound | on | Punch biopsy, re-epithelialization, immune trigger |
| Immune | on | Neutrophil/macrophage waves, M1-to-M2 transition, efferocytosis |
| Inflammation | on | Cytokine diffusion (split pro/anti), immune pressure field |
| Fibroblast | on | TGF-beta cascade, myofibroblast differentiation, collagen deposition |
| Scar | on | Collagen-driven scar vs normal tissue at dissolution |
| MMP | on | Matrix metalloproteinase dynamics, collagen/fibronectin degradation |
| Fibronectin | on | Provisional wound matrix scaffold |
| Angiogenesis | on | VEGF-driven vessel sprouting under hypoxia |
| Perfusion | on | Vascular density field, wound disruption, recovery |
| Dermis | on | Dermal tissue integrity, sub-layer profile, collagen-driven recovery |
| Elastin | off | Elastic fiber network, wound disruption, slow recovery |
| Hyaluronan | off | Ground substance, water retention, wound matrix |
| pH | off | Wound bed alkalinity, acid mantle disruption, migration suppression |
| Hemostasis | off | Fibrin clot scaffold, platelet activation, TGF-beta coupling |
| Biofilm | off | Bacterial colonization, PAMP-driven inflammation |
| Diabetic | off | Impaired healing: prolonged M1, excess MMPs, reduced collagen |
| Tumor | off | Basal cell carcinoma with soft contact inhibition |

## Configuration

Config is layered TOML, merged at runtime:

```
bdm.core.toml                  core tissue params (committed)
  + modules/*/config.toml      18 module configs (auto-merged)
  + profiles/*.toml             skin phenotype overlay
  + presets/*.toml              scenario overlay
  = bdm.toml                    runtime config (gitignored)
```

| Skin profile | | Scenario preset |
|---|---|---|
| `normal` healthy adult (default) | | `wound` punch biopsy (~30d) |
| `aged` slower turnover, thinner corneum | | `tumor` BCC growth |
| `diabetic` prolonged M1, microangiopathy | | `diabetic_wound` chronic ulcer (~42d) |
| `aged_diabetic` composite comorbidity | | `tumor_wound` BCC with wound event |

## Project structure

```
src/
  core/         PDE framework, CompositeField, field names, forces, metrics, fused ops
  infra/        SimParam, VolumeManager, TimeModel, utilities
  skibidy.h/cc  Simulation orchestrator + TOML bindings
modules/        Self-contained modules (config.toml + source per module)
  tissue/       Keratinocyte, cell cycle, differentiation, migration, O2/Ca/KGF/water/stratum
  wound/        Punch biopsy event, wound resolution
  immune/       Neutrophils, macrophages, M1/M2, efferocytosis, chemotaxis
  inflammation/ Cytokine PDE (split pro/anti) + immune pressure field
  fibroblast/   TGF-beta, collagen, myofibroblast differentiation
  scar/         Emergent scar accumulation
  mmp/          Matrix metalloproteinase dynamics
  fibronectin/  Provisional wound matrix scaffold
  angiogenesis/ VEGF-driven vessel sprouting
  perfusion/    Vascular perfusion field
  dermis/       Dermal tissue integrity (sub-layer profile)
  elastin/      Elastic fiber network
  hyaluronan/   Hyaluronic acid ground substance
  ph/           Wound bed pH gradient
  hemostasis/   Fibrin clot scaffold, platelet activation
  biofilm/      Bacterial colonization
  diabetic/     Chronic wound modifiers
  tumor/        BCC neoplastic growth
profiles/       Skin phenotypes: normal, aged, diabetic, aged_diabetic
presets/        Scenarios: wound, tumor, diabetic_wound, tumor_wound, nothing
treatments/     8 therapeutic interventions for diabetic wound study
scenarios/      7 novel experiment definitions (TOML)
studies/        Packaged study scripts and example results
batch/          Multi-run consensus, parameter sweeps, analysis
scripts/        merge_config, apply_preset, plot_metrics, scenario_runner
literature/     Literature comparison scripts, consensus data, SOURCES.yaml
tests/          118 unit tests
docs/           Full documentation
```

## Docs

| Document | Description |
|----------|-------------|
| [Guide](docs/guide.md) | Configuration, running, visualization |
| [Architecture](docs/architecture.md) | UWYN design, CompositeField, adding modules |
| [Module Reference](modules/README.md) | Per-module biology, model, parameters, coupling, and validation |
| [Parameters](docs/parameters.md) | Parameter index with module links and config layering |
| [Wound Healing](docs/wound-healing.md) | Wound biology and model pipeline |
| [Diabetic](docs/diabetic.md) | Diabetic impairment model |
| [Treatments](docs/treatments.md) | Therapeutic interventions |
| [Tumor](docs/tumor.md) | BCC growth module |
| [Batch & Sweeps](batch/README.md) | Multi-run consensus, parameter sweeps |
| [Studies](studies/README.md) | Packaged experiments, scenarios, example outputs |
| [Validation](docs/validation.md) | Metrics columns, literature validation |

## Third-party

| Library | Version | License |
|---------|---------|---------|
| [toml++](https://github.com/marzer/tomlplusplus) | 3.4.0 | [MIT](third_party/tomlplusplus/LICENSE) |
| [BioDynaMo](https://biodynamo.org) | 1.04+ (master) | Apache 2.0 (linked, not bundled) |

## License

[Apache 2.0](LICENSE)
