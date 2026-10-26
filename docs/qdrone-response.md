# QDrone2 development response

The [executed result](../Data/qdrone-response/results.json) summarizes continuous
altitude tracking during the source authors' original-MPC discharge recording.
Each detected command has a response status, precommand battery voltage and,
when its window is complete, signed bias, MAE and RMSE. The ending command stays
in the output as incomplete. The [figure](../Figures/qdrone-development-response.png)
shows aligned tracking and battery voltage, with response errors against time
and precommand voltage. [Vector PDF](../Figures/qdrone-development-response.pdf),
[accessible response table](qdrone-response-table.md) and
[CSV at stored precision](qdrone-response.csv) accompany it.

![QDrone2 original-MPC development recording: altitude and reference above aligned battery voltage, then the same complete-window RMSE values against time and voltage](../Figures/qdrone-development-response.png)

Panels c and d show the same events on one RMSE axis. The axis starts at the
data floor with labelled ticks, so the gap between directions is visible. Upward
and downward commands use both distinct markers and colors. The dotted time marker
locates the incomplete response; it has no invented error value. No bands or
error bars are drawn because none were estimated. The existing narrow variation
can be read precisely in the response table. [Visual inventory and provenance](qdrone-visuals.md)
record the reference and retained historical visuals.

## Source and permission

Observations were collected by Patricio Borbolla-Burillo, David Sotelo, Antonio
Favela-Contreras, Francisco Beltran-Carbajal, Hugo Yañez Badillo and Carlos
Sotelo. Their [Experimental Setup and Experimental Results](https://doi.org/10.5281/zenodo.19464105)
archive grants [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The [source record](../Data/qdrone-response/sources.json) stores citation,
retrieval metadata, archive inventory, download URLs and file hashes.
The archive README identifies Fig13a as repeated altitude commands under the
original MPC on QDrone2, with a voltage-based stopping rule. Its source command
and threshold constants live in `source_endpoint` in that record.

This repository reads the workbook unchanged and derives metrics and a plot.
The derived outputs carry the source attribution and CC BY 4.0 terms; the
analysis code retains the repository's MIT license. Raw workbooks remain outside
git. The linked paper's publisher returned an access error during qualification;
no paper-only shutdown claim or result is used.

## Development designation and method

The earlier project audit had already inspected Fig13a. Commit
[de72981](https://github.com/500ft/multirotor-recovery-dynamics/commit/de72981)
assigned it to development before response metrics were calculated. The same
commit fixed the [protocol](../Data/qdrone-response/protocol.json), source
identity, metric window and command-detection rule. The code was committed
before the full run. Other QDrone2 response workbooks and all NanoBench
final-test files remain unopened. This result has no new confirmation set or
fitted predictor.

[Analysis/qdrone_response.py](../Analysis/qdrone_response.py) verifies the pinned
source hashes and literal workbook header. `Time`, `zd`, `zw` and battery
voltage provide seconds, reference altitude, observed altitude and volts.
Only these channels enter the calculation. Motor columns labeled in volts do
not by themselves establish applied motor voltage or available thrust.
No mass, inertia or motor constants are transferred from the Crazyflie register.

The algorithm detects reference changes with the registered threshold, takes
the last voltage sample strictly before each command, and integrates sampled
errors over the fixed response horizon using actual timestamps. Error is
observed altitude minus the new reference. Bias is the time integral of error
divided by duration; MAE uses absolute error; RMSE is the square root of the
corresponding mean squared error. Trapezoidal quadrature uses the observed
samples and a linearly interpolated endpoint when required. There is no grid
resampling, derivative filtering, parameter fit or state prediction.

Windows ending beyond the recording, crossing the next command or containing
nonfinite required response values remain incomplete with a reason. The
initial steady fragment has no detected command and is unscored. The result
records timing intervals and sample counts for checking coverage, without
interpreting the stored grid as independent observations or native bandwidth.
The plot separates reference directions and shows the same errors against
command time and voltage to keep their confounding visible.

## Limits and next evidence

The selected file describes one discharge. Archive figure panels include
multiple views of experiments and do not identify independent run or battery
counts. Treating command windows as independent packs would overstate the
available evidence. No cross-pack interval or causal voltage slope is estimated.
Direction, demand, controller and elapsed discharge time can affect response.

The source stopping rule and the final recorded voltage are stored separately;
the last sample does not establish that the stated stop threshold was crossed.
An incomplete response is censoring, with no recovery-failure label. The error
window includes the commanded transition and is not a settling-time or physical
damage criterion. No acceptance threshold has been invented.

This result cannot test warning lead time, false alarms, available maximum
thrust, cold operation, payload transfer or upset recovery. Such a comparison
requires independent maneuver outcomes and pack identities, adequate synchronized
state and command telemetry, and approved physical scope. The [roadmap](../ROADMAP.md)
records those prerequisites.

[NeuroBEM's source description](https://rpg.ifi.uzh.ch/neuro_bem/Readme.html)
provides processed motor speed and voltage channels. Its processed time grid
cannot establish each sensor's native bandwidth; observed motor speed cannot
supply a maximum-authority label. Reuse permission remains unqualified, so no
derived NeuroBEM analysis is published here. Its vehicle remains separate from
QDrone2 and NanoBench.

## Reproduce

Install [requirements.txt](../requirements.txt) in a virtual environment. From
the repository root:

```sh
python -m Analysis.qdrone_response --fetch \
  --cache /tmp/multirotor-qdrone-source \
  --output /tmp/multirotor-qdrone-results.json \
  --figure /tmp/multirotor-qdrone-response.png
python -m unittest Analysis.tests.test_qdrone_response -v
```

`--fetch` downloads only the registered source README and development workbook
when absent, then verifies SHA-256 against the committed source record. It
rejects a changed or partial input. The JSON records the original calculation's
code/protocol hashes and runtime. That record stays unchanged during visual
redesign. The compatibility `--figure` option now delegates to the renderer.

To regenerate only the tracked figure and table views from the stored result:

```sh
python -m Analysis.plot_qdrone_response \
  --cache /tmp/multirotor-qdrone-source \
  --figure Figures/qdrone-development-response.png \
  --tables docs
```

This reads the same pinned development workbook for the time-series traces and
`results.json` for event metrics. It writes PNG/PDF plus generated Markdown/CSV,
without recomputing or rewriting the result. Tables show chronological rows,
units in headings and explicit missing values. Display precision is formatting;
the CSV retains the stored floats. Regenerate these views instead of editing
numbers in the table. The original calculation's `code_sha256` identifies its
producing source, which predates the renderer-only change.

Existing repository checks:

```sh
python -m unittest discover -s Analysis/tests -v
python -m unittest discover -s Instrumentation/tests -v
python -m Analysis.run_survivable_set --smoke --workers 2
python tools/check_presentation.py . 'Multirotor Recovery Dynamics' multirotor-recovery-dynamics
python tools/test_presentation.py
```

The new tests cover nonuniform timestamp integration, precommand selection,
endpoint interpolation, incomplete windows and invalid clocks. A separate raw
XLSX XML read and scalar quadrature reproduced the first complete window's RMSE;
this checks the ingestion and arithmetic independently of openpyxl/NumPy.
Historical smoke checks write no results and make no new recovery claim.
