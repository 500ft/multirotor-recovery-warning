# Rotor-force recovery comparison: review packet

The saved computation contains 900 cases, paired across three estimated plants.
This directory delivers a draft source integration alongside base revision
`e7661b24a8d8b981c649b435ea5cd46dc9e33233`; default-branch integration remains pending.
The research remains open for owner and possible professor feedback.

## Question and result

How does release recovery change when the same controller and sampled conditions
are evaluated with the historical plant and two CAD/catalog plants, while every
command is realized by four feasible rotor forces?

The [saved summary](results/summary.json) owns the aggregate outcomes. Each plant
stabilized in its 300 declared cases. Maximum modeled descent was 1.093 m for
the historical plant, 0.747 m for Variant C and 1.145 m for H7. These are rounded
headlines from that file. [Historical](results/historical_actual_code.json),
[C](results/Variant_C.json) and [H7](results/Cheapest_H7.json) retain each case's
outcomes and allocator diagnostics. Episode recovery, terminal stabilization
and crashes remain separate fields.

## Read the evidence

| Purpose | File |
| --- | --- |
| Pre-outcome cohort and noise seeds | [Frozen cohort](frozen/frozen_cohort.json) |
| Original plant values, input hashes and accepted limits | [Original freeze](results/FROZEN_BEFORE_OUTCOMES.json) |
| C mass, tensor, CG and propulsion assumptions | [C physical model](inputs/aircraft_r1/Variant_C/physical_model.json) |
| H7 mass, tensor, CG and propulsion assumptions | [H7 physical model](inputs/aircraft_r1/Cheapest_H7/physical_model.json) |
| Sampler and full-tensor adapter | [Runner source](frozen/r1_recovery_runner.py), [tensor kernel](frozen/sim_release_recovery_tensor.py), [exact diff](evidence/tensor_adapter.diff) |
| Rotor map and direction-preserving moment scaling | [Allocator/runner source](frozen/r1_bounded_v2.py), [executed kernel](frozen/sim_release_recovery_bounded_v2.py), [exact diff](evidence/bounded_v2.diff) |
| Pre-outcome method and time-step screen | [Protocol](frozen/BOUNDED_V2_PROTOCOL.txt), [acceptance record](evidence/bounded_v2_acceptance_frozen.json), [pilot](frozen/bounded_v2_pilot.json) |
| Original analytical/allocator checks | [Checks](evidence/bounded_v2_checks.json), [Euler check](evidence/full_euler_nonlinear_check.json) |
| Output inspection already performed | [Original audit](results/INDEPENDENT_OUTPUT_AUDIT.json), [coordinator recount](evidence/COORDINATOR_DELIVERY_CHECK.json) |
| Result figure | [PNG](figures/bounded_recovery_comparison.png), [SVG](figures/bounded_recovery_comparison.svg), [caption](figures/bounded_recovery_comparison.caption.txt) |
| Exact copied bytes and original locations | [Source map](source-map.json) |
| Rerun obstacles and proposed adaptations | [Portability review](PORTABILITY_REVIEW.md) |

The copied protocol includes an earlier statement that no R1 campaign result
existed. Its later approval paragraph and the completion records preserve the
sequence. The completed `results/summary.json` supplies the current outcome
status; the frozen protocol was not edited retrospectively.

## Method and interpretation

The allocator converts collective and moments to individual rotor forces. It
scales requested moments together when a rotor limit is reached and returns the
achieved wrench. The dynamics use the complete inertia tensor. The controller,
cohort, outcome definitions and acceptance limits are retained in the copied
source and freeze records. Gains were not tuned against these outcomes.

The [sampler clarification](evidence/SAMPLER_AND_INTEGRAL_CLARIFICATION.txt)
explains the unused placeholder torque multiplier and retained integral logic.
The [stopped scalar attempt](evidence/CAMPAIGN_STOP_STATUS.txt) is diagnostic
history and does not contribute a qualified cohort to the current comparison.

Plant mass, inertia, propulsion, guards and yaw inputs contain estimates or
assumptions. Continuous motor lag, installed propulsion calibration and descent
inflow are absent. The per-case files preserve metrics and allocator diagnostics,
not complete state trajectories. The completed audits recount saved records and
frozen hashes; they are not an independent reduction of every full trajectory.
The allocator enforced moment closure during execution, but its maximum moment
error was not separately serialized. Simulation outcomes do not qualify a flight
envelope, recovery probability for real aircraft, or a warning system. Reserved
public-data outcome files were not opened by this study or this packaging task.

## Inspection and reproduction status

Inspect the copied code as text. Do not import the runner or invoke `--help`
from this directory: the original modules generate kernel/diff files at import
time and reference the original host checkout. The audit script also writes
plots and tables. They were preserved byte for byte and were not run here.

The new [case75 wrapper](portable_replay.py) separates immutable inputs from a
fresh output directory. It loads the saved pure kernels and selects the exact
parameter/allocator definitions without importing their source-generating
drivers. It reads the frozen cohort and remaps only model-file path metadata.
The [protocol](PORTABLE_CASE75_PROTOCOL.json) was recorded before first use.

The [first replay status](../../review_runs/portable_case75_01/STATUS.json) and
[per-field comparisons](../../review_runs/portable_case75_01/COMPARISONS.json)
record the selected case for each plant. All compared scientific scalar fields
matched the saved values exactly; wall-clock time was excluded prospectively.
The six scalar trajectories already exposed by the kernel were retained. These
checks qualify the path/loading change for the selected cases on this host;
they do not re-run or independently validate the full campaign.

For a later authorized replay from the repository root, choose a directory that
does not exist:

```sh
python -B studies/recovery-r1-900/portable_replay.py --output ../fresh-case75-replay
```

The wrapper refuses an existing output directory, changed registered inputs or
the first failed comparison. It has no campaign or case-selection option.
Original driver portability limits remain in
[PORTABILITY_REVIEW.md](PORTABILITY_REVIEW.md). Other hosts and dependency
environments have not been tested. No original scientific source was adapted.

## Notices and review state

Primary code and associated documentation retain the repository's
[MIT notice](notices/ORIGINAL_MIT_LICENSE.txt). No QDrone2, NanoBench or other
third-party source dataset was added. The copied figures were already generated
from the saved computation; no figure was redrawn for this packet.

The source map retains the original Windows locations as provenance metadata.
The generic Admin source-checkout locations were reviewed with the copied packet:
they contain no CUSP research, private contacts or credentials. They remain as
historical provenance and are not portable execution paths. The study-specific
attributes preserve copied source and output bytes across checkout line-ending
conversion.

- [ ] Owner reviews the source/input/output packet.
- [ ] Professor or independent technical review is recorded, if obtained.
- [x] Coordinator authorized the path/loading wrapper and its single case75 replay.
Publication of this non-enclosure review packet follows the owner's pivot and
publication instruction. Draft delivery does not record technical acceptance.

No approval, professor endorsement or project closure is inferred from these
unchecked review fields.

## Repository validation status

The local fail-fast suite stopped after 18 tests on Windows default text decoding.
One approved child-process UTF-8 pass then stopped after 77 tests at the registered
NanoBench fixture hash: checkout CRLF bytes differ from the registered HEAD LF
bytes. Both stopped logs are preserved locally. The exact-LF fixture restoration
and another local suite pass remain pending the existing owner decision; neither
was performed for this draft. No test, registered hash or acceptance limit changed.

Hosted CI is separate evidence using the repository's normal Linux checkout and
declared dependencies. Its result does not authorize the held local repair or
turn the selected-case replay into a full-campaign reproduction.
