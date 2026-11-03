# Traceability index

The [dependency decision](decisions/dependency-roadmap.md) adopts the warning
question's qualification sequence and mandatory delay-aware physics baseline. The [QDrone2 report](qdrone-response.md)
links the source/license, registered protocol, executed result and figure.
Physical [access and test choices](../OPEN_QUESTIONS.md#pending-owner-decisions) remain
unanswered. The [roadmap](../ROADMAP.md) is the active plan.

The [history index](history/README.md) preserves the NanoBench replay,
configuration register and unresolved timing qualification. The rows below
preserve the older designed-vehicle audit; its gates do not select or validate
the warning-study aircraft.

One row per consequential decision: what it is, what requires it, where its
reasoning lives, which canonical inputs it depends on, how it will be validated,
and its current status. **The mathematics is not repeated here** — follow the link.

**Status vocabulary.** `derived` (reasoning recorded) · `asserted` (purpose
stated, derivation absent) · `bare` (value only) · `preregistered` (frozen before
execution) · `blocked` (needs an input that does not exist) · `unresolved`.
No historical decision row below is `measured`. The Crazyflie replay uses
third-party ordinary-flight observations with their own source and license;
it supplies no physical validation of recovery or warnings.

## Historical vehicle and propulsion

| Decision | Requirement | Reasoning lives in | Canonical inputs | Validation | Status |
| --- | --- | --- | --- | --- | --- |
| Frozen maximum mass 165 g | REQ-MASS-001/002 | [`calculations.md` §Mass and Thrust](../Design%20Report/calculations.md) | `mass_budget.csv` (EST-MASS-001…012) | weigh the built vehicle | `derived` (rule), inputs catalog/estimate |
| Abort threshold 225 g | REQ-MASS-002 | [`calculations.md` §Abort threshold](../Design%20Report/calculations.md) | 250 g regulatory boundary | allocate the buffer, or restate as policy | **`unresolved` allocation** |
| Unmodelled hardware +5 g | — (no ID) | [`ENGINEERING_AUDIT.md`](ENGINEERING_AUDIT.md) Tier C | — | itemise or justify | **`bare`** |
| Thrust-to-weight ≥ 2.0 | REQ-PROP-001 | [`calculations.md` §T/W](../Design%20Report/calculations.md) | `T_max`, `arm_m` | static thrust at 7.0 V (OQ-001) | `derived` (retrospective) |
| Per-motor thrust 112.5 gf @ 225 g | REQ-PROP-001 | `Analysis/gates.py` | T/W, mass | propulsion bench | `derived`, **bench-gated** |
| Authority ≥ 0.020 N·m, 25–75 % | — (no ID; see audit) | [`measured-authority-gate/design.md`](specs/measured-authority-gate/design.md) | 4.41 N total, 5 mm offset | EST-REC-007 bench | `derived`, **measurement pending** |
| Arm 60 mm | — (no ID) | `with_mixer()` docstring | — | CAD | **`blocked`** on CAD |
| Acceptance voltage 7.0 V | REQ-PROP-002 | requirements.csv | 2S LiHV min | bench | `asserted` |

## Guard and structure

| Decision | Requirement | Reasoning lives in | Canonical inputs | Validation | Status |
| --- | --- | --- | --- | --- | --- |
| Prop clearance ≥ 2.0 mm | REQ-GUARD-001 | [`calculations.md` §Prop Guard Geometry](../Design%20Report/calculations.md) | guard geometry | CAD + inspection | `asserted` |
| Clearance SF ≥ 2.0 | REQ-GUARD-002 | `Analysis/guard.py` | impact energy, stiffness | drop/contact test | `asserted` |
| Stress SF ≥ 3.0 | REQ-GUARD-003 | `Analysis/guard.py` | PETG allowables | material test | `asserted`, PETG scatter unquantified |
| Guard causal mechanism | **OQ-013** | [`survivable-set/design.md` §6b](specs/survivable-set/design.md) | — | mechanism statement + evidence | **`unresolved`** |

## Recovery study

| Decision | Requirement | Reasoning lives in | Canonical inputs | Validation | Status |
| --- | --- | --- | --- | --- | --- |
| Landing criterion 2.0 m/s / 30° | — | [`survivable-set/design.md` §5](specs/survivable-set/design.md) | — | drop test of the actual vehicle | `preregistered`, **assumed** |
| Guarded criterion 2.5 m/s / 60° | OQ-010 | same | — | drop test | `preregistered`, **assumed (EST)** |
| Descent budget 3.0 m | **OQ-006** | `sim_release_recovery.py` | enclosure dimensions | facility survey | **`blocked`** |
| Mechanism kill criterion | — | [`design.md` §7](specs/survivable-set/design.md) | exact CP bounds | — | `preregistered` |
| Paired comparison (McNemar) | — | [`design.md` §7a](specs/survivable-set/design.md) | discordant counts | — | `derived` |
| Scenario arms L/H/I | — | [`scenario-contract.md`](specs/survivable-set/scenario-contract.md) | R01–R10 | — | `preregistered` |
| Fault abstraction | R01 | same | — | hardware failure characterisation | `preregistered`, **idealised** |
| Parachute inflation 0.6 s | OQ-010 | [`design.md` §4](specs/survivable-set/design.md) | published sim/HIL outputs | physical drop | **calibration, not validation** |
| Detection delay cells | — | [`design.md` §6c](specs/survivable-set/design.md) | published 20–130 ms envelope | — | `preregistered` scenario bracket |

## Statistics

| Decision | Reasoning lives in | Validation | Status |
| --- | --- | --- | --- |
| Clopper–Pearson exact bounds | [`literature/notes/05`](../literature/notes/05-statistics-reachability-preregistration.md) | — | `derived`, criticism recorded |
| 962/1000 at 0.95 lower bound | `monte_carlo_recovery.py` | — | `preregistered` |
| Empirical 5th percentile, n=6 | audit Tier C | — | **`bare`**; is a minimum, not a confidence bound |
| Bounds are conditional sampling bounds | [`design.md` §6c](specs/survivable-set/design.md) | — | `derived` |

## Bench (V995 demonstrator, retired 2026-10-04)

The earlier simulation-first study used Bitcraze Crazyflie data; physical
hardware for the warning study remains undecided under M2 ([roadmap](../ROADMAP.md)).
Rows below describe the retired V995 work.


| Decision | Reasoning lives in | Validation | Status |
| --- | --- | --- | --- |
| Observability contract | [`bench-acquisition.md` §4b](bench-acquisition.md) | — | `derived` |
| Load-cell selection 1 kg vs 5 kg | **OQ-012** | installed calibration | **`blocked`** |
| Static-only force chain | [`bench-acquisition.md` §4b](bench-acquisition.md) | — | `derived` (12.5 ms at 80 SPS) |
| V995 control access | **OQ-011** | board investigation B01–B04 | **`blocked`** |
| Platform = stock Veeniix V995 | [`cad/v995/README.md`](../cad/v995/README.md) | — | **owner decision 2026-09-27** |
| Cell selection (1 kg 4540) | [`cad/v995/README.md`](../cad/v995/README.md) screening table | installed calibration | `asserted` — datasheet screen, **conditional** on an unverified 4540 accuracy class |
| Cell-end adapter geometry | [`cad/v995/`](../cad/v995/README.md) + `contract.json` | delivered-part inspection (OQ-017) | `derived` from `candidate_drawing` inputs |
| V995 cradle / base plate | `generate_fixture.py` `NOT_GENERATED` | aircraft + bench inspection | **`blocked`**, reasons recorded |

## How to use this

- Adding a consequential number? Add a row, and put the reasoning **beside the
  decision**, not here.
- Moving a status to `measured` requires recorded physical evidence under
  `evidence/`, not a calculation and not a citation.
- `blocked` rows name the open question that blocks them. Resolve the question,
  not the row.
