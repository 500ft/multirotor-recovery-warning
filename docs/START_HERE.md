# Start here: Multirotor Recovery Warning

The [README](../README.md) states the research question and current evidence.
The [roadmap](../ROADMAP.md) lists the remaining prerequisites. This guide points
to results and reproduction commands.

## Reading paths

| If you have | Read |
| --- | --- |
| Two minutes | [Current work](../README.md#current-work), then the [roadmap](../ROADMAP.md) |
| Half an hour | The [QDrone2 response report](qdrone-response.md), [open questions](../OPEN_QUESTIONS.md), then [data and figures](data-and-figures.md) |
| A current result to review | The [response result](../Data/qdrone-response/results.json) and [registered protocol](../Data/qdrone-response/protocol.json) |
| Prior development replay | The [NanoBench replay](nanobench-baseline.md), [source timing/configuration check G1](nanobench-g1.md) and [history index](history/README.md) |
| Historical recovery work | The [survivable-set design](specs/survivable-set/design.md) and historical [review index](REVIEW_READY.md) |
| Development dependencies | [Roadmap prerequisites and completion evidence](../ROADMAP.md#dependency-order); instrumentation and propulsion qualification precede the physics baseline |
| Physical platform choice | The hardware, site and budget choice (M2) remains [pending](../OPEN_QUESTIONS.md#pending-owner-decisions); public datasets describe separate vehicles |
| Bench hardware | The [bench wiring and bring-up](bench-acquisition.md); the retired [V995 fixture notes](../cad/v995/README.md) are history |

## Configurations

The simulation work used a designed 130–165 g vehicle (EX1103 motors, Kakute H7
flight controller, 2S battery). It was never built. Its numbers live in
`Engineering Data/`, `cad/bench/` and the analysis code, with its own gates
(7.0 V, six motors, 0.020 N·m).

The earlier simulation-first study selected the Bitcraze Crazyflie. Its sourced
values are in `Engineering Data/platform_crazyflie.csv`; the warning study has
not selected physical hardware under M2. No values carry over from the designed
vehicle. The stock V995 demonstrator is retired; its register in `cad/v995/`
remains as history.

In the linked reports, M2–M4 name pending physical access, maneuver and facility
choices; G5 is the separate purchase restriction. OQ IDs identify open or
historical research questions. DR IDs identify recorded study decisions and do
not authorize physical work.

## Software checks — Python 3.11

Set up as in the [README](../README.md#quick-start), then from the repository
root:

```sh
python cad/input_requests.py --check
python -m unittest discover -s Analysis/tests -v
python -m unittest discover -s Instrumentation/tests -v
```

[CI](../.github/workflows/ci.yml) runs analysis and instrumentation tests,
the historical simulation smoke and presentation checks. Crazyflie inputs belong
in its [platform register](../Engineering%20Data/platform_crazyflie.csv).
The designed-vehicle and V995 input checks remain historical regression checks.

## CAD — pinned environment

The pins in [cad/requirements.lock](../cad/requirements.lock) cover direct
packages only, not the whole dependency tree:

```sh
conda create -n recovery-cad -c conda-forge --strict-channel-priority --file cad/requirements.lock
conda activate recovery-cad
python -m pytest cad/tests -q
```

The [CAD workflow](../.github/workflows/cad-geometry.yml) regenerates the
historical motor-envelope geometry and uploads it for inspection. V995 CAD stays
available as a historical asset with its tests; automatic generation of its
unreleased fixture has been removed. Completing it is outside the roadmap.

## Regenerating the simulations

These overwrite the committed JSON and figures, so use a spare checkout at a
recorded revision:

```sh
python -m Analysis.run_release_recovery
python -m Analysis.monte_carlo_recovery
```

[Data and figures](data-and-figures.md) lists smaller single-study commands.
The 4% placeholder result and the 300 of 300 mixer prediction differ in
controller as well as torque, so they are not a controlled test of torque
alone.

## Before any powered work

Nothing in this guide authorizes powering anything. Before physical work, review
[Safety](../Safety/README.md) and the
[bench checklist](../Instrumentation/propulsion-bench-safety-checklist.md)
with the responsible person for the actual setup. The proposed
[bench bring-up](bench-acquisition.md) begins with a power-off continuity check;
powered operation still requires its own approval.

The September 11 [completion correction](COMPLETION_RECONCILIATION.md)
explains which early deliverables were preparation rather than finished work.
