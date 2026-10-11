# 07: Loss-of-control prediction and the recovery-warning question

The full-text review corrects the earlier abstract-only positioning. A general
onboard loss-of-control warning is already demonstrated. The current recovery
comparison remains untested; neither its novelty nor a likely null result is
established by this paper alone.

## Source and reading scope

Altena, van Beers and de Visser, *Loss-of-Control Prediction of a Quadcopter
Using Recurrent Neural Networks*, JAIS (2023),
[DOI](https://doi.org/10.2514/1.I011231),
[primary repository](https://repository.tudelft.nl/record/uuid%3A3051e4a5-5684-4d69-a3a5-bf1109298635),
[final published PDF](https://repository.tudelft.nl/file/File_45d6fb48-867f-43ce-ba4f-c43cf0d51789).
The complete article, including references, was read. The primary download
matches the supplied local reading copy, SHA-256
`ee6a20e23ed80856fe5c77e827d5f87d5324ff09506ab709be69f49067e078ae`.
The PDF and extraction are excluded from git; their availability does not grant
permission to redistribute them or reuse flight logs. No raw-data reproduction
or forward-citation review was performed.

## Verified paper findings

This table is the repository's numerical source for this comparison.

| Topic | Full-text finding | Location (journal page) |
| --- | --- | --- |
| Task | Predict time to forced yaw LOC; command ±2000 deg/s, label first roll/pitch magnitude exceeding 90° and continuing to grow. | III.A, 649–650 |
| Hardware | Tiny Whoop, UZ85, CineGO; Betaflight 4.2. Tiny Whoop motor-output limit 50%; onboard commands, rotor outputs and IMU logs. | III.A, Tables 1/3 |
| Conditions | Mass, propellers, wind and vehicle transfer; alternate pitch maneuver. | III.A, IV.C |
| Comparison | LSTM, BILSTM, CNN-LSTM, GRU and input ablations; time-to-LOC RMSE. No standalone saturation-threshold or height-to-arrest comparator. | III.B–IV |
| Evaluation | Random 80/20 split, overlapping windows; scaling uses all nominal runs; model comparison uses one separate validation flight. | III.A–C, IV |
| Limits | Pitch endpoint was onset of roll-axis flipping; detection failed on both selected longest runs. Wind produced false positives. Detection-time/false-positive/false-negative tradeoff remains untested. | IV.C.3–4, V.C |
| Timing/transfer | Approximately 2 s predictions track training duration; propeller/vehicle changes introduce timing bias and input-selection changes. | IV.C.2/5, V.C |
| Source conflicts | Tiny Whoop mass: abstract 53 g versus Table 1's 56 g. Three-blade diameter: IV.C.2 30 mm versus Table 1/III.A/V.C 35 mm. | 648, 650, 655, 658 |

## What changes in our interpretation

Command saturation is a controller-output observation. Available force depends
on the installed motor, propeller, supply, airflow and allocation. Even an
unsaturated command cannot guarantee adequate height to complete a recovery.
For example, identical commands at different descent speeds or heights can
produce different completion outcomes. Equating saturation with calibrated
thrust margin discards those variables. Keep a simple saturation warning as a
separate comparator alongside Roadmap C's delay-aware physics calculation.

The paper's task-specific label cannot serve as our independent maneuver
completion criterion. Its evaluation does not report a held-out battery-pack
comparison. Our contrast is whether an advance warning improves on
physics, saturation, voltage, sag-history and load comparators at equal
false-alarm burden for an approved fixed controller and recovery maneuver,
with whole packs and payload/guard conditions withheld. A new name for the
warning or a different airframe would not establish added value.

The table's split description does not establish whole-flight separation within
the random partition. Overlapping windows and scaling provenance matter when
assessing independence, but the text alone is insufficient to reproduce the
split or allege a measured leakage effect. Our evaluation must keep complete
groups separate and fit preprocessing only on development data. Likewise,
time-prediction RMSE alone cannot establish useful warning lead time at a fixed
false-alarm burden. Neither lower average error nor an early alert by itself
proves a warning is actionable.

Remove the earlier claim that a null result is likely: no matched comparator
result supports that probability judgment. A null result remains possible and
reportable. Evidence that would change the present assessment is either a
prior matched comparison on the same recovery endpoint, or our own qualified,
reserved comparison showing whether warning information adds value. This
single-paper review establishes a narrower contrast, not field-wide novelty.
The source conflicts above remain unresolved and must not populate a hardware
register. Retired vehicle and CAD history remain unchanged.

## M2 access choices, still pending

These are alternatives for the owner, not approvals or a new execution plan.
[Roadmap A](../../ROADMAP.md#a-qualify-component-instrumentation-and-propulsion)
retains the qualification requirements and G5 purchase gate.

| Route | What it could enable | Evidence needed before commitment | Supported endpoint |
| --- | --- | --- | --- |
| Borrow or lab access | Existing aircraft, measurement equipment, space and supervision could reduce what must be acquired. | Confirm the actual aircraft/controller, permitted logging and maneuvers, availability, independent outcome measurement, costs and safety responsibility. Access is currently unverified. | Component qualification first; warning evaluation only after the later roadmap gates. |
| Buy Crazyflie 2.1+ later | A dedicated candidate platform could avoid dependence on a borrowed aircraft. | Owner selects the configuration and approves a complete incremental budget: aircraft/radio, packs, fixtures, references, sensing, spares and facility needs. Purchase alone provides no calibration or outcome labels. CAD then uses current drawings and delivered interfaces. | Same qualification and outcome requirements; purchase does not establish transfer from the paper's vehicles. |
| Scoped qualification-only result | Report installed measurement capability, uncertainty and failed qualifications if qualified bench access becomes possible but flight outcomes do not. | Owner agrees the reduced scope; actual qualification records are still required. With current desk evidence alone, only this source review is complete. | Measurement capability within the tested configuration; recovery-warning performance remains unanswered. |

Recommendation: establish whether suitable lab access exists before choosing a
purchase. This is conditional on real availability, not an approved route.
Declining purchase does not close the project or select qualification-only work.
The next owner input is the M2 access/funding route and actual available hardware
and space, with M4 safety responsibility before physical execution.
