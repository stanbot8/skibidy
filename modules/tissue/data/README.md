# Primary cell-cycle data

The three original XLSX files were downloaded from public publisher supplement
links on 2026-10-07. They remain byte-for-byte unchanged. Xiao and Piedrafita's
originals are included here under the open terms described below. Roshan's full
publisher workbook is preserved locally in the Git directory's `research/tissue`
cache, outside the public checkout. `provenance.json` owns
the exact URLs, article identities, sizes, SHA-256 hashes, settings and extraction
rules, storage locations and attribution. Roshan's author manuscript permits
academic copying/downloading/data mining under Nature conditions and does not
claim CC BY; the public outputs contain numerical extraction and analysis.

[Xiao, Eze, Charruyer-Reinwald et al. (2024)](https://link.springer.com/article/10.1186/s13287-024-03670-y)
publish their article under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
and its data under [CC0](https://creativecommons.org/publicdomain/zero/1.0/) unless
otherwise credited. [Piedrafita, Kostiou, Wabik et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7080751/)
publish under CC BY 4.0, with third-party credit exceptions. No separate restrictive
credit was found in either numerical workbook. Both originals are unchanged;
the CSV and JSON are extractions and summaries made by this project's script.
[Roshan, Murai, Fowler et al. (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4872834/)
retain their publisher's credits and conditions; their workbook is not included.

Run `python modules/tissue/data/analyze_cycles.py` with openpyxl, NumPy and SciPy.
On a fresh checkout, use `python modules/tissue/data/analyze_cycles.py --download`
to fetch the missing Roshan original from its recorded ordinary public URL into
the local Git research cache. An explicit `--cache-dir PATH` also supports an
existing download or a checkout without Git metadata. Retrieval verifies size
and SHA-256 before saving, rejects changed responses, and never replaces an
existing file. Running without `--download` uses only local files. Copies of
tracked originals can also be recovered through their recorded URLs if missing.
The verified run used Python 3.14.3, openpyxl 3.1.5, NumPy 2.4.3 and SciPy 1.17.1.
The script verifies the original hashes, unique extracted source cells and the
Xiao classified counts before writing the derivatives. It opens source files
read-only and never saves them. Openpyxl's unsupported-extension warning refers
to its in-memory representation; the hash checks protect the original bytes.

`human_complete_cycle_records.csv` preserves study, sheet, clone, source generation,
duration cell, missing duration, recorded fate and fit-selection flags. A positive
interval is a confirmed completed division only with two P/D/U daughter labels;
single D/U and other labels remain auditable without an assumed division. It includes
founder and untracked records for audit as well as selected complete cycles.
For example, Xiao EXP!D4 is 18 hours and Roshan expanding Fig2a!G5 is 11.6667 hours.
Generation 1 duration is excluded because time since plating is not a whole cycle.
Roshan's local subclone generation resets require additional identity information;
the main neonatal expanding sheet is therefore retained without fitting it.
Identical timestamps are not deduplicated. Other experimental sheets are separate.

`cycle_summary.json` contains complete-cycle and classified-fate summaries,
sample SD/CV, source hashes and exploratory marginal fits. Normal has two fitted
parameters; gamma and lognormal fix location 0 and fit two parameters. AIC is
`4 - 2 logL`. This independence-based calculation is descriptive because cells
share lineages, cultures and observation windows. It neither corrects censoring
nor identifies Skibidy's latent phase-duration propensity distribution. The
Xiao subset reproduces group counts 1017/174, while its DIF median 30.5 differs
from the article's 30; retain the source precision rather than force agreement.

The mouse workbook contains H2B-GFP intensity observations. The JSON inventories
actual tissue sheets, header cells, chase-time labels, observation counts and
distinct recorded mouse IDs. Counts of nuclei are not independent animal counts.
No intensity-to-duration conversion is performed.

See [biological variation](../../../docs/heterogeneity.md) for the interpretation
and optional model settings. None of these outputs changes calibrated parameters.
