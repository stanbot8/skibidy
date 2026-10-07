# Model and workflow completion

Started 2026-10-07 from `ad973e68e487f34fa318b17adff4eddd82fd114c`,
using BioDynaMo `v1.05.169-060d86f1`.

The purpose is to make the simulation's biological claims and experiment
workflows reproducible and honestly validated. Existing parameter means stay
fixed while defects are repaired. The user's question about distributions adds
an investigation of persistent cell and patient variation. Distributions and
their widths must have explicit evidence or be labelled sensitivity assumptions.
Roman Bauer has already been contacted by the user. No further email is needed.

## Work and acceptance criteria

- [x] Freeze and run normal, diabetic and full-model baselines with seeds
  42, 43 and 44. Save complete configurations, runtime identity, metrics,
  individual validation results and aggregate variability.
- [x] Replace fractional day-zero treatment approximations with actual start
  events. Untreated and delayed-treatment runs must agree before the start.
  Treatment must act at the requested time, including combination schedules.
- [x] Replace field-only checkpoints with verified compatible replay and state
  witnesses. Compare
  uninterrupted and resumed runs through agents, fields and metrics, including
  randomness and pending treatment events. Reject incompatible or corrupt saves.
- [x] Audit disabled mechanisms and validation coverage against primary
  sources. Preserve visible failures and distinguish unsupported observables
  from passing validation. Repair established implementation defects without
  tuning parameters to a desired curve.
- [x] Support reproducible, explicitly scoped parameter distributions where
  justified. Keep the fixed baseline reproducible. Sample persistent traits at
  their biological owner rather than adding arbitrary noise at every step.
- [x] Add CI and proportionate regression checks for the maintained workflows,
  including seeds, treatment starts, checkpoint equivalence and validation.
- [x] Exercise studies, aggregation, figures and the dashboard through their
  consumers. Repair failures and update documentation from current evidence.
- [x] Implement and verify the research extensions identified in the project
  assessment, with source provenance and stated validation limits.
- [x] Run the complete checks, review the final diff and deliver the resulting
  code and scientific evidence. Do not equate a successful build with completion.

## Evidence and decisions

The nine frozen baseline runs completed with finite output. Normal and full-model
configs run 30 days, sampled through hour 710. Diabetic configs run 35 days,
sampled through hour 820. All nine fail at least one existing curve screen:
normal/full have 12 tested observables each, diabetic has 6. The remaining
observables are explicitly untested. The reference audit shows that inherited
"consensus" curves do not have established patient-level extraction provenance.
Even a passing 15% normalized RMSE is only an engineering shape screen.
`scripts/validate_replicates.py` saves individual coverage, mean trajectories
and sample SD across seeds, plus figures. Seed variation is not patient uncertainty.
The [published baseline receipt](../literature/baseline-20261007/receipt.json)
and byte-verified archive preserve all nine configurations, metrics, logs and
validation reports. The historical loaded-library identity was not recorded.
The receipt distinguishes the known frozen library file from process evidence.

Checkpoint runtime regression passed 15 checks, including step 53 between PDE
updates, stochastic cell traits, membrane dynamics, historical treatment events,
future forks, corrupt saves and incompatible identities. ROOT stores agents and
RNG. Explicit arrays avoid its incomplete diffusion container serialization.
Scheduler/caches are reconstructed by deterministic replay and checked at the
boundary. There is no verified fast restore or speedup. See [limits](checkpoints.md).

Treatment runtime regression passed 15 run checks. Delayed runs match untreated
metrics and boundary state before the event, diverge afterwards, and day-zero
treatment matches a constant overlay. Equal-time events preserve declared order.
The [30-run pro-resolution cohort](../studies/diabetic-wound/data/proresolution_20261007/)
uses six arms and five paired seeds over 42 configured days, sampled through
hour 1000. Its exploratory recovery coefficients remain assumptions. It does
not establish an optimal treatment or clinical efficacy.

The C++ suite passed 168 tests across 57 suites. Dashboard/batch tests included
a real HTTP create-study, two production runs, aggregation and the results consumer.
The final discovery run passed 40 Python tests. One optional alternate-loader
test was skipped there and passed in its separate two-simulation proof.
The Python suite also passed with the generated root config absent. Dashboard
cohorts preserved an existing config byte-for-byte, and both failed batch starts
and the alternate-loader proof preserved initial config absence. A fresh build
generated study hooks before ROOT dictionary compilation and passed all 168 C++
tests. Deleting that header regenerated identical bytes, and adding/removing a
study declaration triggered reconfiguration. With BioDynaMo's GoogleTest files
temporarily unavailable, the maintained build found system GoogleTest and passed
the same 168 tests. The bundled dependency was restored after this check.
The literature library and data checker each passed 22 tests. The full data
checker validated 37 reference and evidence CSVs with no errors or warnings,
including censored cell records, measured RNA and treatment constraints.
The dashboard Study Builder also created the user's `wound-evidence`
normal-profile study in the browser,
and the shared study resolver read the saved identity.
The [GitHub CI run](https://github.com/stanbot8/skibidy/actions/runs/37683060530)
passed on Ubuntu 24.04 at code snapshot
`b86053a1b9b6f648384c4a5ada7d8af50f3c037b`. It installed the pinned BioDynaMo,
built from a fresh checkout, passed 168 C++ tests, executed 40 Python tests
(one optional alternate-loader test skipped), passed both 22-test literature
suites, checked 37 CSVs without errors or warnings, and passed the checkpoint
and scheduled-treatment runtime regressions. The real dashboard cohort ran in
that Python suite. The final documentation commit changes no software or data.

[Primary evidence](../literature/provenance.md) now includes 1,632 wound RNA
measurements from 96 biopsies, auditable individual division records with
descriptive normal/gamma/lognormal fits, and qualitative membrane component
milestones. RNA does not measure protein, cell count or collagen mass. Observed
cycle CV does not identify persistent trait CV. Component staining does not
calibrate membrane repair. These limits are retained with the data.

Mechanism audit: collagen-dependent TGF-beta sequestration and tissue-density
clearance are active coarse-grained sinks. Decorin/receptor trafficking are
implicit. Default gradient recruitment, efferocytosis-driven polarization,
constitutive-plus-responsive collagen and hypoxia-driven VEGF switches remain
as configured. Full-model enables the latter three. Explicit IDO1/tryptophan/
kynurenine/AhR and fibromodulin/IL-1β pathways are not represented by those
switches. The source mechanisms do not identify the model coefficients, so the
audit does not activate mechanisms or tune rates just to improve curve scores.

The optional membrane extension and persistent cell distributions are verified
through their consumers and remain disabled/fixed by default. Source metadata
repairs changed no parsed config values. Two inherited profile citations remain
explicitly unresolved (keloid Liu 2018 and psoriasis Griffiths 2017). Unrelated
DOIs were not accepted as support.
