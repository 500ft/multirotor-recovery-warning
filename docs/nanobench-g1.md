# NanoBench timing qualification

G1 remains incomplete. The pinned public snapshot does not supply the raw
motor/gyro block times, applied alignment offsets or deployed build configuration
needed to qualify a causal dynamic fit. The exposed development excerpt
reproduces the previous arithmetic and recorded-rate mismatch exactly, excluding
runtime. The [executed probe](../Data/nanobench-g1/qualification.json) records the
source inventory, metadata counts, adapter comparison and alternative-data
schema. No fit or final-test prediction was executed.

The [registration](../Data/nanobench-g1/registration.json) preceded this probe.
It fixes the previously exposed flight and excerpt, preserves the original
split, model and processing hashes, and requires stopping if collection timing
and configuration cannot be recovered. The conditional matrix and lag/delay
comparisons therefore did not start. G2 remains incomplete.

## What was recovered

[Sources and hashes](../Data/nanobench-g1/sources.json) pin the reviewed files.
[Public-source observations](../Data/nanobench-g1/public-source-survey.json)
record branches, release assets and the license field at retrieval. The search
covered the complete pinned NanoBench tree, its public branches/releases, the
README, the referenced paper's acquisition/synchronization sections and the
dataset loaders. Upstream result tables, model checkpoints and final-flight
observations were not opened.

| Evidence | Finding and consequence |
| --- | --- |
| Collection firmware | The exposed flight metadata supplies a version label. Its source revision and the logging/mixer/sensor trace are in the [existing audit](../Data/nanobench-baseline/audit-sources.json). Deployed flags, patches, parameter dump and binary identity remain unavailable. |
| Commands and conventions | The source path logs motor ratios after the compensation/capping path and motor overrides. The [existing audit](nanobench-baseline.md#audit-of-the-exposed-development-excerpt) checks motor IDs, moment signs, body axes, gyro units and quaternion conventions. The replay applies no second compensation. Euler columns remain unused because their published unit label disagrees with the excerpt. |
| Effective sampling | Metadata provides block counts and coarse recording endpoints. The probe reports average deliveries over that duration. Counts do not locate samples, recover interpolation weights or establish independent bandwidth. |
| Alignment | The [NanoBench paper, section III-C](https://arxiv.org/html/2603.09908v1#S3.SS3), describes full-flight gyro/Vicon cross-correlation followed by shifting and linear interpolation. The paired metadata contains neither offsets nor raw block timestamps. No collection/alignment implementation or build configuration was found in the reviewed tree. The paper's precision claim cannot supply the missing per-flight evidence. |
| Loader alternatives | `benchmarks/utils/data_loader.py` and the task-2 loader consume aligned CSVs; they do not reconstruct raw collection timing. `datasets/dataset/build_dataset.py` windows already prepared state/motor-speed columns, which differ from the released NanoBench PWM schema. It is not the missing collection pipeline. |
| Aircraft prior | Dataset mass remains fixed to CF-011 in the [register](../Engineering%20Data/platform_crazyflie.csv). Stock-model inertia and candidate firmware curves remain priors; the installed propeller and instrumented inertia are unresolved. |

The previous baseline and its residuals are unchanged. These source findings
do not show that the authors' unpublished files are unavailable to them; they
describe the public artifacts actually checked. Recovering collection code,
raw motor/gyro timestamps, applied offsets and deployed settings could change
this qualification. An empirical fit to the current grid could absorb its
processing into apparent actuator dynamics, so it would not resolve this gate.

## IDSIA alternative checked

The actual source is
[idsia-robotics/nanodrone-sysid-benchmark](https://github.com/idsia-robotics/nanodrone-sysid-benchmark),
linked by the [Nonlinear Benchmark entry](https://www.nonlinearbenchmark.org/benchmarks/nano-drone).
It describes a Crazyflie Brushless configuration. This task inspected its main
and documented dev source branches and release schema; it made no platform or
dataset switch.

The probe verifies that the named training member in the release matches the
pinned main branch's Git LFS object, then reads its header. It contains
`m1_rads` through `m4_rads`, body rates, state and body-acceleration columns.
No numerical flight rows or notebook outputs were parsed. Source inspection
supports a processed telemetry interpretation:

- `utils/topic_utils.py` extracts electrical RPM from the motor topic and
  applies scaling. The notebook converts it to rad/s. The
  [paper's acquisition description](https://arxiv.org/html/2512.14450v1)
  attributes motor-speed telemetry to a bidirectional DShot firmware extension.
  This traces the fields beyond a suggestive column name; it does not verify
  the deployed driver, pole-pair conversion or each released sample.
- `processing/csv_to_processed.ipynb` contains full-flight thrust/acceleration
  alignment, backward filling and zero-phase filtering. These operations use
  future observations. Processed motor-speed columns alone cannot establish
  causal actuator delay. Notebook code-cell locations are in the probe record;
  the notebook was never executed.
- `utils/topic_utils.py` defines `extract_motors` twice. The later definition
  omits the STM32 timestamp selected by the earlier one. The probe locates the
  effective definition using Python's source structure. This raises a timing
  traceability question, without establishing what code produced the release.
- The dev tree contains raw-recording paths. Their existence does not establish
  fields, rights or usable timing; their data were not opened in this task.

No explicit reuse license was located in the checked main/dev trees, README,
release archive, benchmark page or its [disclaimer](https://www.nonlinearbenchmark.org/disclaimer).
The GitHub license field was empty. Publication access and a citation request
do not settle dataset or code reuse terms. The
[unsent request](idsia-data-request.txt) asks for those terms and the processing
trace. Third-party code and the dataset archive remain outside git.

## Reproduce

Use the repository's existing Python requirements. This fetches the pinned
source files and the release archive into an external cache, checks their
hashes, inspects metadata/source structure and replays only the existing
development excerpt:

```sh
python -m Analysis.qualify_nanobench_sources \
  --cache ../nanobench-g1-cache --fetch \
  --output ../nanobench-g1-qualification.json
```

For an existing cache, omit `--fetch`. Missing or changed pinned files fail the
command. Moving-endpoint observations are retained separately with retrieval
times; the command does not pretend to reconstruct their historical state.
The scientific source review above supplies the gate interpretation. The
script checks the concrete inspected artifacts, rather than deciding whether
unknown public files exist. Runtime is recorded in the result JSON.

## Owner exercise and next action

Use `first_row` in the [excerpt audit](../Data/nanobench-baseline/excerpt-audit.json)
to reproduce one causal increment. Starting from its measured initial body
rate, form each motor's $\mathbf{r} \times \mathbf{F}$ and signed reaction torque, sum the moments,
then calculate $\dot{\boldsymbol{\omega}} = J^{-1}\left(\boldsymbol{\tau} - \boldsymbol{\omega} \times J\boldsymbol{\omega}\right)$. Multiply by the
first timestamp interval for the forward-Euler diagnostic and compare with the
recorded next-row increment; the audit also supplies the integrated prediction.
Only the start state and available command history belong in the prediction.
Explain why scaling torque and inertia together can preserve angular response,
and why unknown input/gyro alignment can resemble motor lag. Arithmetic
agreement does not select among those explanations.

Owner action: review the unsent IDSIA license/data request for possible outreach.
