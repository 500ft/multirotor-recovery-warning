# Current results

The [dependency roadmap](../ROADMAP.md) requires qualified propulsion measurements
and a delay-aware physics comparator before warning evaluation. No new physical
or warning result is supplied by the roadmap cleanup.

## QDrone2 public component response

The [development summary](../docs/qdrone-response.md) reports continuous altitude
tracking under the source authors' original MPC. The
[result file](../Data/qdrone-response/results.json) holds each response's bias,
MAE, RMSE, voltage and completeness; the
[figure](../Figures/qdrone-development-response.png) shows direction and time.
The [response table](../docs/qdrone-response-table.md) keeps all events in command
order, with [downloadable values](../docs/qdrone-response.csv).
Source, license and pre-calculation protocol are linked in the report.
Independent pack outcomes and recovery-failure labels remain unavailable.

## Prior Crazyflie development study

This section preserves the earlier study. It does not validate the current
warning question or authorize reopening its final-test split.

The [NanoBench baseline replay](../docs/nanobench-baseline.md) is executed on
development flights. Documented motor models accumulate substantial angular-rate
error relative to persistence. [Per-flight error tables](../Data/nanobench-baseline/development-errors.csv)
and the [run record](../Data/nanobench-baseline/development-run.json) contain the
scores, exclusions and runtime; the [figure](../Figures/nanobench-baseline.png)
summarizes horizon-dependent error. Source, configuration and timing limits are
listed with the replay. Final-test predictions remain unexamined, and no
parameters were fitted. [Preserved G1 gate](../ROADMAP.md#preserved-scientific-gates) remains
incomplete for dynamic identification.
The [selected-excerpt audit](../docs/nanobench-baseline.md#audit-of-the-exposed-development-excerpt)
reproduces the mismatch without establishing a replay implementation defect.
The original result remains unchanged.
The [public-source timing qualification](../docs/nanobench-g1.md) reproduces that
audit and records the missing collection timing/configuration. Conditional
identification stopped before fitting. The alternative-data inspection and
unsent request are recorded with that result.

## Historical designed aircraft

All results below use the earlier estimated aircraft. Their old bench gates
are retained for reproduction and do not govern Crazyflie work.

Generated from the locked Stage 1 catalog selection on June 21, 2026. These are
not validated design results.

## Mass Budget

| Quantity | Mass (g) |
| :--- | ---: |
| Best case | 123.86 |
| Nominal | 135.66 |
| Worst case | 156.00 |
| Unmodeled-hardware allowance | 5.00 |
| Proposed frozen maximum | 165.00 |
| Nominal margin to proposed maximum | 29.34 |

The proposed maximum is below the 225 g abort threshold (PASS).

The `165 g` value is a proposal only. It cannot become the fixed maximum until
delivered components are weighed and the complete CAD mass model exists.

## Pre-Registered Component Gates

| Gate | Threshold | Unit | Status |
| :--- | ---: | :--- | :--- |
| Full-reserve thrust at 7.0 V | 112.5 | gf per motor | Bench test required (BENCH_REQUIRED) |
| ESC unconditional current | ≤ 10.4 | A per motor | Bench test required (BENCH_REQUIRED) |
| Battery unconditional current | ≤ 44 | A per pack | Bench test required (BENCH_REQUIRED) |
| Stage 1 Nicla p95 latency | ≤ 100 | ms | Bench test required (BENCH_REQUIRED) |
| Future recovery Nicla p95 latency | ≤ 50 | ms | Deferred (DEFERRED) |
| Duplicate hardware resources | 0 | count | Pass on catalog map (PASS) |

## Preliminary Recovery Envelope

| Case | Minimum height (m) | Available height (m) | Testable now |
| :--- | ---: | ---: | :--- |
| Best placeholder case | 0.88 | 3.00 | Yes |
| Nominal placeholder case | 8.64 | 3.00 | No |
| Worst placeholder case | 58.42 | 3.00 | No |
| Nominal no-drag bound | 11.16 | 3.00 | No |

The model is first-order and uses estimated inertia, torque, thrust, latency, and drag. These results demonstrate why recovery cannot be assumed to work at low height. They do not predict the final vehicle.

## Guard Functional Check

All current placeholder guard cases fail the required clearance-to-deflection safety factor of `>=2`.

| Case | Predicted deflection (mm) | Clearance safety factor | Elastic stress safety factor | Functional result |
| :--- | ---: | ---: | ---: | :--- |
| Best placeholder case | 5.35 | 0.56 | 17.82 | Fail |
| Nominal placeholder case | 10.54 | 0.24 | 7.50 | Fail |
| Worst placeholder case | 20.00 | 0.10 | 4.00 | Fail |

This does not prove a real guard will fail. It proves that the assumed stiffness and energy values do not close and must be replaced by analysis and test data.

## Classifier Confidence Bounds

| Observation | Exact 95% upper bound (%) |
| :--- | ---: |
| 0 false positives in 300 trials | 0.994 |
| 0 false positives in 1,000 trials | 0.299 |

An observation of zero is not reported as a true false-positive rate of zero.

## Closed-Loop Recovery Envelope (6-DoF, corrected 2026-07-02)

From `Analysis/run_release_recovery.py` (`Data/release_recovery_results.json`). The
envelope scan is capped at the gyro measurement range (2000 °/s): a release faster than
the gyro can report cannot be claimed recoverable regardless of the dynamics. Each edge
is labeled by what it actually is.

Highest recovered tumble rate before the first failure, at 60° tilt and a 3 m
height budget:

| Tier | Rate (rad/s) | Rate (°/s) | Envelope edge |
| :--- | ---: | ---: | :--- |
| Best | 34.5 | 1977 | Gyro limit: no failure up to the sensor range |
| Nominal | 3.5 | 201 | Dynamic failure |
| Worst | 1.0 | 57 | Dynamic failure |

The previously reported "best ≥ 40 rad/s" was the scan cap of the search loop — an
artifact, not a physical boundary — and exceeded the gyro range. Corrected.

## Monte Carlo Dispersion Sweep — GATE RESULT: FAIL at placeholder authority

From `Analysis/monte_carlo_recovery.py` (`Data/monte_carlo_results.json`). The validation
gates require recovery to hold "across a Monte Carlo sweep, not only a single
cherry-picked run." Dispersions per trial: mass ×[0.95, 1.10], inertia ×[0.85, 1.25],
torque ×[0.85, 1.10], thrust ×[0.85, 1.05], latencies ×[0.8, 1.5], battery sag ×[0.90, 1.00],
motor-mismatch torque bias ≤ 10% of budget, gyro noise 0.02 rad/s, attitude-estimate noise
2°, thrust-line (CG) offset uniform over a disk. Release: 60° tilt, nominal BOM tier.

Recovered releases out of trials (success rate), by initial tumble rate:

| Scenario | 1.0 rad/s | 2.0 rad/s | 3.0 rad/s |
| :--- | ---: | ---: | ---: |
| As-toleranced (CG offset ≤ 5 mm) | 3/75 (4.0%) | 6/150 (4.0%) | 1/75 (1.3%) |
| Balance-controlled (CG offset ≤ 1 mm) | 45/75 (60.0%) | 115/150 (76.7%) | 32/75 (42.7%) |

Success rates carry exact Clopper–Pearson 95% lower bounds in the JSON (same
zero-inflation-proof convention as the classifier stats above).

**Root cause.** The thrust-line-offset disturbance torque is `cg × thrust`. Against the
placeholder 0.004 N·m per-axis budget (EST-REC-007 — explicitly a placeholder,
"replace with measured thrust and arm length"):

| Thrust condition | CG offset using 100% of budget (mm) | CG offset at 50% margin (mm) |
| :--- | ---: | ---: |
| Hover (1.27 N) | 3.15 | 1.57 |
| Recovery peak (4.2 N) | 0.95 | 0.48 |

A thrust cap during righting does not rescue it: protecting torque margin trades directly
against the 3 m altitude budget and the vehicle hits the ground instead.

**What this means (requirement, not despair).** A real 4-motor mixer at this scale can
plausibly produce ~10× the placeholder differential torque, so the FAIL is most likely an
artifact of the conservative placeholder — but that is exactly the point: the claim is
unverifiable until measured. Derived actions:

1. **EST-REC-007 is the highest-value bench measurement in the project.** Measure
   per-motor thrust + arm length; the recovery-robustness story lives or dies on it.
2. **New build requirement:** thrust-line offset ≤ 0.5 mm (50%-margin at recovery thrust
   under the placeholder budget), to be verified from the Lane A+ CAD mass model and at
   assembly. Relax only after (1) demonstrates margin.
3. Until one of those lands, the single-point Lane A demo may be cited only alongside
   this gate result.

## Scenario C — Mixer-Authority Prediction (added 2026-07-02, later same day)

The follow-up the FAIL demanded: replace the placeholder torque clip with the
**physically-derived 4-motor mixer authority** (`with_mixer`,
`Analysis/sim_release_recovery.py`) — per-motor thrust in [0, T_max/4],
differential headroom `d_max = min(T/4, T_max/4 − T/4)`, giving
`τ_rp(T) = 2√2·arm·d_max` (zero at zero AND full collective — the coupling the
placeholder ignored). Arm = **60 mm, ASSUMED** until CAD/bench. Making the
authority real exposed three controller gaps, each fixed with the standard
technique and stated in-code:

1. **Integral trim** (clamped, upright-only): a PD loop trims a constant CG
   disturbance with a steady tilt of `τ/KP ≈ 30°` at 2 mm offset — the classic
   reason attitude stacks carry an I-term.
2. **Attitude-priority desaturation ("airmode")**: collective capped at 75% so
   differential headroom can never vanish at full thrust.
3. **Control-authority floor while inverted**: quarter-collective while the
   >78° thrust cut is active — motors keep spinning for torque, the physical
   reason a real quad can right itself from inverted.
4. **Gain rescale** (P and D together, 3×): the base gains were sized for the
   0.004 N·m clip and are too soft to out-torque a CG disturbance at 60° tilt
   once real authority exists.

Result (scenario C in `Data/monte_carlo_results.json`), same as-toleranced
dispersions as scenario A (cg ≤ 5 mm; the torque multiplier now scales the arm):

Recovered releases out of trials (success rate; exact 95% lower bound for C):

| Scenario | 1.0 rad/s | 2.0 rad/s | 3.0 rad/s |
| :--- | ---: | ---: | ---: |
| A: placeholder authority | 3/75 (4.0%) | 6/150 (4.0%) | 1/75 (1.3%) |
| C: mixer authority (ASSUMED 60 mm arm) | 75/75 (100.0%; ≥ 96.1%) | 150/150 (100.0%; ≥ 98.0%) | 75/75 (100.0%; ≥ 96.1%) |

Worst altitude loss in scenario C: 1.01 m of the 3.0 m budget (3 rad/s case).

**Status of this result: a PREDICTION, not a validation.** The A→C contrast changes
both the authority model and controller behavior; it does not isolate a causal
effect of torque, nor demonstrate measured recovery. Everything above is
conditional on the ASSUMED 60 mm arm and datasheet per-motor thrust. The
scenario exists to make the EST-REC-007 bench measurement decisive: measure
per-motor thrust and arm, plug them in, and the recovery-robustness claim is
evaluated under those measured inputs; static thrust/arm data alone cannot
validate dynamic recovery or motor response. Until then the summary is: *fails at placeholder
authority, predicted to pass at mixer authority, measurement pending.*

## Frozen measured-authority verdict (registered 2026-07-17)

The next result is no longer governed by “comfortably above” or “sufficient
trials.” At 7.0 V, the empirical fifth-percentile `tau_rp(T)` must be at least
**0.020 N·m at every registered point from 25–75% collective**. If that passes,
the measured-distribution simulation runs 1,000 primary trials at 2 rad/s,
60° tilt, and CG ≤5 mm. PASS requires at least **962/1,000** recoveries, exact
one-sided 95% Clopper–Pearson lower bound ≥0.95, and maximum descent ≤3.0 m.
The 250-trial 1 and 3 rad/s cases are descriptive only.

The automated gate is committed in `Analysis/measured_authority_gate.py` and
`Analysis/monte_carlo_recovery.py`; the physical result remains **measurement
pending**. See `docs/specs/measured-authority-gate/`.

The evidence-admission correction dated 2026-09-05 requires a source manifest,
six sampled-motor identities, calibrated uncertainty, and unique raw references.
It validates supplied file consistency, not source authenticity or calibration
quality. The empirical fifth percentile (the minimum with six observations)
is not a confidence-qualified population bound. Synthetic bundles cannot issue
a physical PASS. The fixed thresholds above are unchanged.

## Survivable-Set Study A/A2/B (registered 2026-09-16)

Full definitions and audit trail: `docs/specs/survivable-set/design.md` (Study
A/B preregistration), `design-a2.md` (spin-aware variant + machinery revision),
`drop-test-prediction.md` (registered Study C prediction). Generated data:
`Data/survivable_set_results{,_a2}.json`, figures
`Figures/survivable_set_{psafe,policy}{,_a2}.png` with captions in the matching
`.caption.md` files. Everything below is
**simulation on EST action inputs (OQ-010)** — no survivable-set claim is
released until the bench and drop gates run.

Question: after a partial propulsion loss at state (height, vertical speed,
tumble rate, detection delay), which action — thrust reallocation, the
guard-enabled mechanism behavior, or a parachute-like device — maximises the
probability of a survivable landing, judged by a preregistered impact criterion
with exact Clopper–Pearson bounds?

Results, both controller variants (baseline PD and spin-aware A2):

- **Mechanism kill criterion fired in both variants**: in no primary
  (class × cell) does the mechanism's exact lower bound clear reallocation's
  exact upper bound. Every primary comparison is flagged `both_actions_fail` —
  under the registered interpretation clause this is a *controller* finding,
  not evidence the actions are interchangeable, and it blocks mechanism
  redesign rather than motivating it.
- **SCENARIO CAVEAT (2026-09-24, critique C04):** the simulator cuts **all four
  motors** for detection + spool latency before the controller engages. That is a
  **release/startup transient**, not an in-flight failure in which the healthy
  motors keep running until the fault is detected. Every rotor-out number below is
  conditional on that reading. The generated JSON now carries
  `scenario: "release_startup"`. Implementing `in_flight_loss` requires its own
  registration — see `docs/specs/survivable-set/critique-2026-09-24-status.md`.
- **SCOPE CORRECTION (2026-09-24, `design.md` §6b): this is a comparison of
  design packages, not a runtime policy.** `realloc_only` removes the guard's
  mass and inertia; `mechanism` keeps it. An airborne vehicle cannot choose to
  have launched without its guard, so the `policy` output is a **ranking of
  aircraft configurations**, not an executable in-flight selector. The parachute
  action is **UNAVAILABLE** in every configuration we own. Read every statement
  below as "which package performs better", never "which action to take".
- **Paired analysis (added 2026-09-23, `design.md` §7a) — the mechanism package
  does not merely fail to help; within this model it performs worse.** With both arms now drawing
  identical vehicles, noise and initial states, the comparison is exact
  conditional on discordant pairs rather than a clash of marginal intervals:
  - All four **primary** cells return `no_discordant_pairs` — mechanism and
    reallocation produced **identical outcomes on all 300 paired trials**. That
    is a far stronger statement of indistinguishability than the overlapping
    intervals previously reported, and it is what actually backs the kill verdict.
  - Across the 96 exploratory comparisons, 72 have no discordant pair at all.
    Of the 76 discordant pairs that exist, **69 favour reallocation and 7 favour
    the mechanism** (pooled π = 0.092, exact 95 % CI [0.038, 0.181]; pooled sign
    test mid-p ≈ 3.5 × 10⁻¹⁴). Two individual cells reach `b_superior`.
  - The direction matters more than the significance: the mechanism is judged
    against the **more lenient** guarded criterion (2.5 m/s, 60°) and still loses
    the overwhelming majority of discordant pairs. It is carrying mass and rim
    inertia that the paired trials say it does not earn back.
  - Pooling across heterogeneous cells is descriptive only; the per-cell verdicts
    in `Data/survivable_set_results.json` are primary.
- **H-A2.1 is contradicted, not merely unsupported.** Across 192 paired
  variant comparisons, the spin-aware variant won **zero** discordant pairs; the
  baseline won all 15 that exist (π = 1.000, exact 95 % CI [0.782, 1.000]).
  184 comparisons are outcome-identical. The gyroscopic feedforward never
  produced a survivable landing the baseline did not, and in 15 paired trials the
  baseline survived where it did not.
- **A2 hypothesis outcome**: H-A2.1 (gyroscopic feedforward + bounded terminal
  spin helps in tall cells) was NOT supported — all A-vs-A2 differences sit
  inside Monte Carlo uncertainty; H-A2.2 (parity at low height) held. The next
  controls step is a spin-locked rotor-out controller, not more feedforward.
- **Class structure**: 60% partial authority is benign nearly everywhere
  (lower bound 0.90 in the registered cage cell); one rotor out is marginal at
  2 rad/s and unrecoverable at 6 rad/s tumble; **two adjacent out has no
  surviving action of any kind in any cell.**
- **Parachute action, corrected 2026-09-22**: the original model treated
  deployment as a delay followed by an instantly effective drag device and made
  the action the unambiguously best choice in 22 class×cell combinations. Adding
  the inflation transient — calibrated to reproduce both published data points of
  the only measured system available — makes it **0/2000 in every cell**. The
  nominal ballistic distance before useful drag is 9.6 m and the break-even
  height is 10.5 m, against a tallest preregistered cell of 6.0 m. The 10.5 m
  figure is derived independently yet falls inside the 10–15 m floor measured for
  0.9–2 kg airframes. See `docs/specs/survivable-set/design.md` §4.
- **Boundary finding**: a 6 rad/s tumble at failure is outside the arrest
  envelope of this control family for the rotor-out classes at every tested
  height.
- **Integrator defense**: halving dt moves primary-cell impact speeds by at
  most 0.0044 m/s with full landed/not-landed agreement
  (`Data/survivable_set_convergence.json`).

## Scenario correction diagnostic — DR-SS-SCENARIO-01 (2026-09-25)

Registration: [`docs/specs/survivable-set/scenario-contract.md`](../docs/specs/survivable-set/scenario-contract.md),
frozen before execution. Data: `Data/scenario-diagnostic/scenario_diagnostic.json`.
Generator: `python -m Analysis.run_scenario_diagnostic`. **Exploratory, 288
trajectories on a limited slice — not a full-grid verdict.**

Three arms on identical physical draws: **L** legacy `release_startup` (all rotors
off until detection + spool), **H** `in_flight_hold_matched` (healthy rotors hold
pre-fault trim, same switch time), **I** `in_flight_hold_immediate` (held outputs,
recovery at detection). Fault abstraction is idealized complete rotor
effectiveness loss (R01) — **not** a validated motor-stop or propeller-loss
transient.

- **The binary proxy cannot resolve the scenario effect at the primary cells.**
  All 288 trajectories reached contact and **every one failed the criterion in
  every arm** — the two primary cells are precisely where everything already
  fails. So H−L, I−H and I−L are all 0/24 discordant, and the paired verdicts are
  `no_discordant_pairs` by saturation, not by agreement. **A full-grid rerun
  judged only on the binary proxy would have reported "no change" and been
  uninformative.** That is a finding about the study design.
- **The effect is real in the continuous quantities, and its sign depends on the
  cell.** Retaining healthy thrust delays contact everywhere
  (+0.03 to +0.07 s). Mean paired impact-speed change, I−L: **−0.38 m/s** at
  `h3_vz0_w6_d0.11` (one_out) and **−0.18 m/s** (two_adjacent), but **+0.21 m/s**
  at `h1.5_vz-1.5_w2_d0.3` (one_out) and **+0.09 m/s** (two_adjacent). Per-trial
  spread is wide (down to −3.4 m/s, up to +1.2 m/s).
- **This is exactly the registered warning.** Retained thrust slows the descent
  while the retained *unbalanced moments* worsen attitude; neither contrast was
  registered as expected to improve anything, and neither did uniformly.
- **I−H is small** (|mean| ≤ 0.16 m/s), so most of the change comes from
  retaining thrust rather than from removing the startup dead time.

The diagnostic uses the historical estimated aircraft. Its all-fail outcomes
motivated the new case selection below.

## Scenario comparison with selected cases

The new cases distinguish the release/startup and corrected in-flight scenarios
in every primary comparison. The in-flight case reduces landing pass rates for
one-rotor loss and increases them for opposite-rotor loss and reduced authority.
The exact counts, rate changes and intervals are in
[`Data/scenario-02/results.json`](../Data/scenario-02/results.json).

The [registration](../docs/specs/survivable-set/scenario-02.md) was committed
before execution. Its [settings](../docs/specs/survivable-set/scenario-02.json)
record the cases, sample count and new seed. Every draw is run in all three
scenarios and both aircraft packages. The original landing thresholds and A2
controller stay fixed. I-L is the primary comparison, with a Bonferroni
adjustment across the case-package comparisons. H-L and I-H show how the
retained-thrust history and transition timing contribute.

For each paired comparison, b counts passes only in the first scenario and c
counts passes only in the second. The pass-rate change is `(b-c)/N`. The exact
interval describes `b/(b+c)`, the share of disagreements favouring the first
scenario. These are different quantities, and the output reports both. Raw
per-trial outcomes are in [`trials.jsonl`](../Data/scenario-02/trials.jsonl).

The cases were selected using earlier simulation results and then evaluated
with fresh draws. The conclusions apply to the historical model and its assumed
landing limits. The [roadmap](../ROADMAP.md#current-step) is paused before
component instrumentation while the M2 access choice is open. The original
`two_adjacent` impact-speed results remain in the earlier diagnostic; no
additional study of that class is scheduled.

## Recovery replay with motor allocation

The [recovery replay](../docs/recovery-video.md) runs the historical nominal
and pessimistic aircraft with four feasible motor forces and first-order
rotor-speed response; the displayed pessimistic case adds filtered angular-rate
feedback and slower motors. Generator: `python -m Analysis.recovery_video`.
The [result file](../Data/recovery-video/results.json) holds altitude loss,
settling and held-recovery times, horizontal motion, the motor-response
sensitivity runs and the half-step convergence deltas. The
[settings](../Data/recovery-video/settings.json) pin the source revision and
assumptions; the [search record](../Data/recovery-video/scenario-search.json)
keeps every candidate behind the outcome-selected pessimistic case.

A rerun of the generator on a second machine reproduced every scalar field
and every logged array exactly, under the pinned NumPy
([record](../Data/recovery-video/reproduction-numpy-2.4.6.json)) and under
an older NumPy ([record](../Data/recovery-video/reproduction-numpy-2.1.1.json)).
Each record lists host, versions, command and the per-field comparison;
[`compare_reproduction.py`](../tools/recovery_video/compare_reproduction.py)
writes it from a rerun in a separate checkout. The replay is a deterministic
simulation on estimated parameters. It estimates no recovery probability and
leaves the envelope and Monte Carlo results above unchanged.
