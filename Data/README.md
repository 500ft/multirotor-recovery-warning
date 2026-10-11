# Data

[qdrone-response/](qdrone-response/) contains the current public component
source record, registered development protocol and executed continuous-response
result. Raw source workbooks remain outside git; [reproduction](../docs/qdrone-response.md#reproduce)
fetches the selected licensed file and verifies its hash.


[nanobench-baseline/](nanobench-baseline/) contains the Crazyflie development
replay, source records and frozen split. [nanobench-g1/](nanobench-g1/) contains
the source qualification; [data and figures](../docs/data-and-figures.md) maps
these outputs to their generators and limits. Full downloaded flights remain
outside git, apart from the attributed development test excerpt.

[v995-envelope/](v995-envelope/) contains the hand-calculated propulsion
envelope for the owned V995: declared and literature inputs with evidence
states, and the executed result from `Analysis/propulsion_envelope.py`. No
measurement of the aircraft is in it.

Other existing result files and the physical-test layout below belong to the
historical aircraft. The warning study follows the [roadmap](../ROADMAP.md);
the old tasks and thresholds do not transfer to it.

Do not commit fabricated or manually edited measurement results.

Use this structure:

```text
Data/
  Calibration/YYYY-MM-DD_instrument_calibration-name/
  Bench/YYYY-MM-DD_test-id/
  Unpowered-Release/YYYY-MM-DD_test-id/
  Powered-Recovery/YYYY-MM-DD_test-id/
```

Each test directory should contain:

- `metadata.json`
- raw instrument exports
- raw flight logs
- video or a link to externally stored video
- processed outputs
- test notes and observed failures

Powered-recovery data is not permitted until the documented safety gate is approved.
