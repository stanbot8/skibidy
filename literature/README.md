# Validation

Compares simulation output against digitized literature data and checks source integrity. Reference data lives in each module under `modules/<module>/data/`, with citations in per-module `SOURCES.yaml` files.

## Running

```bash
# Full pipeline (source check + sim validation + plots)
python3 literature/validate_all.py output/skibidy/metrics.csv

# One module, using the same saved-run validation rules
python3 literature/validators/compare.py wound output/skibidy/metrics.csv

# Source integrity only (no sim data needed)
python3 literature/check_sources.py

# 10-run batch consensus with validation
python3 batch/batch.py -n 10 --study wound --validate
```

`validate_all.py` runs the source check first, then loads complete simulation metrics
and validates enabled modules, including enabled outputs that remain zero.
Both validation commands read `run-config.toml` or `bdm.toml` beside the metrics
or in its parent directory. Supply `--config PATH` when saved evidence lives
elsewhere. Explicit condition flags must agree with that saved configuration.
Wound curves use days since injury. RA and tumor use days since simulation start.
Failed or entirely untested screens return a failing exit status.
The module command supports `wound`, `immune`, `fibroblast`, `microenvironment`
(`microenv`), `tumor` and `ra`. Use `--quick` to skip plots and `--report PATH`
to select the JSON destination. Its default is `validation_MODULE.json` beside
the metrics. The full validator writes `validation.json` there.

## Scripts

| Script | Purpose |
|--------|---------|
| `validate_all.py` | Single entry point: source check, compute, print, plot |
| `check_sources.py` | SOURCES.yaml structural integrity + DOI cross-check |
| `lib.py` | Shared utilities: CSV loading, interpolation, RMSE, plotting |

## Source integrity checks

`check_sources.py` parses per-module `SOURCES.yaml` files and validates:

| Check | Level | What |
|-------|-------|------|
| YAML parse | ERROR | File loads cleanly |
| `description` field | ERROR | Every dataset has a description |
| `sources` list | ERROR | Every dataset has at least one citation |
| Citation fields | ERROR | Each source has `id`, `authors`, `year`, `title` |
| File references | ERROR | `consensus` and `raw_files` paths resolve to existing files |
| DOI/PMC/URL | WARN | At least one locator per source |
| Config DOI cross-check | WARN | Inline `doi:10.xxx` comments in configs match SOURCES.yaml |

## Output

Plots are saved in `plots/` beside the selected metrics CSV:

| File | Contents |
|------|----------|
| `validation_dashboard.png` | Combined multi-panel dashboard |
| `wound_validation.png` | Closure, inflammation, immune cells |
| `fibroblast_validation.png` | Fibroblast, myofibroblast, collagen |
| `microenvironment_validation.png` | TGF-b, VEGF, fibronectin, MMP, wound pH |
| `tumor_validation.png` | Growth rate + doubling time |

For detailed parameter sources and validation datasets, see each module's README under `modules/*/README.md`.

The [fibroblast producer experiment](fibroblast-producers-20261007/README.md)
records the primary evidence, matched-seed comparison, raw trajectories and
remaining biological failures for the activated-cell collagen repair.

The [lactate VEGF signal experiment](lactate-signal-20261007/README.md)
records the evidence and matched-seed effects of restoring lactate signaling
in oxygenated dermal and epidermal wound tissue.

The [NO collagen evidence and matrix-loss diagnosis](no-collagen-20261007/README.md)
records the removal of an unsupported inhibitory coupling, the remaining
biological failures and an isolated MMP collagen-breakdown experiment.
