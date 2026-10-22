# Executable analysis

Current result reproduction is [QDrone2 response](../docs/qdrone-response.md#reproduce).
The [roadmap](../ROADMAP.md) defines prerequisites for future physics and warning
work. No new feasibility calculator or warning model is implemented yet.

Run the retained regression checks:

```sh
python -m unittest discover -s Analysis/tests -v
```

[NanoBench reproduction](../docs/nanobench-baseline.md) and
[G1 qualification](../docs/nanobench-g1.md) remain available with their original
split and blockers. Final-test files remain unopened.

Historical designed-aircraft models remain because committed results depend on
them: budget, recovery, guard, allocation, rigid-body, release, Monte Carlo and
survivable-set/scenario code. [Data and figures](../docs/data-and-figures.md)
maps their inputs and commands. Instrument calibration/gates and statistical
helpers retain their tests. These calculations do not accept the future aircraft.

The unused prototype state-diagram renderer and retired CAD task-ledger validator
were removed; see [cleanup and retention](../docs/history/README.md#cleanup-and-retention).

The owner-requested [large-tilt development comparison](../docs/large-tilt-recovery.md)
executes the historical release simulator with the original and optional
angle-error controller. Reproduction commands and model limits are in that report.
