# Exact checkpoint continuation

Checkpoints use verified deterministic replay. Saving runs exactly N steps and
stops before final cleanup. Resuming initializes the original experiment, reruns
those N steps through the normal scheduler, checks the saved boundary witness,
then continues. This reconstructs agents and behaviors, random streams, continuum
and derived fields, scheduler phases, wound events, recruitment counters, and
operation caches through their normal state owners. **Replay gives no speedup**
and repeats prefix output in the new run's metrics file.

BioDynaMo's native Simulation serialization excludes the scheduler, environment,
execution contexts and custom operation pointers. Saving concentrations alone
cannot restore this model's trajectory. The old field-only format is rejected.

Use the same Linux executable, installation paths and loaded runtime libraries,
with `OMP_NUM_THREADS=1`, `OMP_DYNAMIC=FALSE`, `skin.hot_reload=false`, and no
command-line configuration or native backup/restore. Multithreaded continuation
is unsupported. The file records the original TOML, the exact completed step,
runtime fingerprint, and a witness of ROOT-streamed agents/behaviors, random
streams, continuum concentrations and cached gradients, and every derived-field
value. The witness does not independently cover the inactive continuum buffer,
scheduler internals or operation caches. Normal replay reconstructs those owners.
BioDynaMo's ROOT grid streamer drops its vector data, so the witness reads grid
arrays directly through the grid API. A versioned, bounded, checksummed file is written through a temporary
file and renamed after a successful close. Existing checkpoints are immutable.
Checksums detect accidental corruption, not malicious tampering.

From the sourced BioDynaMo environment:

```sh
/usr/bin/python3 batch/checkpoint.py save --step 53 --dir checkpoints/step_53
/usr/bin/python3 batch/checkpoint.py fork --checkpoint checkpoints/step_53 \
  --treatments npwt --output output/fork_53_npwt
```

The save command selects a profile and study (`--profile diabetic`,
`--study diabetic-wound` by default). A fork inherits the configuration stored in
the checkpoint. Named treatment overlays are resolved in the selected study and
shared treatments, validated against the runtime parameter allowlist, and added
as schedule events at the actual saved boundary. It never applies treatment to
the initialization or prefix. Ordered existing schedule events before that
boundary must remain identical. Future events may change. Static configuration
changes are rejected except `simulation.output_dir`. Module switches, geometry,
seed, run length and scheduler changes require a new baseline run.

Each batch run has its own working directory, TOML and process logs. Nonzero exits,
invalid checkpoints and incomplete/nonfinite resumed metrics return failure.
Direct binary use sets `SKIBIDY_CKPT_SAVE_DIR` plus `SKIBIDY_CKPT_STEP`, or
`SKIBIDY_CKPT_LOAD_DIR`. Save and load are mutually exclusive. Step N means N
completed steps: a treatment scheduled at step N executes on the next step.
At the fixed 0.1-hour time step, step 700 is 70 hours (2.92 days). Day 7 is step 1680.

Use Python 3.11 or newer. Sourcing some BioDynaMo installations changes PATH to an
older bundled interpreter, so the commands above select Ubuntu's interpreter.

Run `/usr/bin/python3 scripts/validation/checkpoint_regression.py` after building to compare
uninterrupted and resumed production runs at an off-subcycle boundary with an
active wound and recruited immune cells. It checks exact metrics and final
state witnesses, a treatment fork against its scheduled uninterrupted trajectory,
and corruption/configuration/runtime/thread/boundary rejection. The optional
`SKIBIDY_STATE_SIGNATURE_FILE` environment variable writes a final witness for
these comparisons without changing biology.
