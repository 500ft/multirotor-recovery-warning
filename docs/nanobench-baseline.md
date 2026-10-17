# NanoBench baseline replay

The documented motor models accumulate substantial angular-rate error on the
eligible development flights. Persistence has lower mean flight rollout error
in the [executed figure](../Figures/nanobench-baseline.png).
The per-flight, per-axis results are in
[development-errors.csv](../Data/nanobench-baseline/development-errors.csv);
[development-run.json](../Data/nanobench-baseline/development-run.json) records
exclusions, numerical failures through the metric table, input hashes and runtime.
No parameters were fitted and no final-test predictions were evaluated.

Figure caption ([caption file](../Figures/nanobench-baseline.caption.md)):
NanoBench development replay: open-loop rollout error of the documented motor models against the persistence comparator. Panels (a) to (c): mean world velocity error [m/s] for (a) 2.1+ curve, (b) Thrust-upgrade curve, (c) Legacy-propeller curve. Panels (d), (e), (f): mean body angular rate error [rad/s] for the same models in the same order. Each panel repeats persistence (hold state, diamonds, dashed line) so the panels share one scale per row. Horizons 0.1, 0.25, 0.5 s; same starts for all models; 12 development flights per point; mean of within-flight vector RMSE with equal flight weighting; no uncertainty interval. Persistence has the lowest error at every horizon for both quantities. The three motor-curve velocity errors meet by 0.5 s. The thrust-upgrade curve has the largest body rate error at every horizon. NanoBench observations collected by Ullah and Baca. Per-axis and per-flight values: Data/nanobench-baseline/development-errors.csv.

## Reproduce

Run from the repository root with Python and `curl`. Store the dataset outside
this checkout. The downloader fetches only the files listed in
[sources.json](../Data/nanobench-baseline/sources.json), at the pinned revisions,
and checks every SHA-256. It also checks existing cached files before reuse.

```sh
python -m pip install -r requirements.txt
python -m Analysis.nanobench_data acquire --cache ../nanobench-cache
python -m Analysis.nanobench_data inventory --cache ../nanobench-cache
python -m Analysis.nanobench_replay --cache ../nanobench-cache --split development --output ../nanobench-replay
python -m Analysis.plot_nanobench_baseline --results ../nanobench-replay/development-errors.csv --output ../nanobench-replay/development.png
python -m unittest Analysis.tests.test_nanobench_replay -v
```

The output directory is separate so reproducing the run preserves the committed
results. Runtime and environment are in the run record. The acquisition requires
network access; replay and tests run offline after acquisition. No full flight
CSV is committed. The small development excerpt used by tests has its own
[source and row-range record](../Analysis/tests/fixtures/nanobench/source.json).
NanoBench observations were collected by Syed Izzat Ullah and Jose Baca.
Data reuse permission is explicit: the pinned README's
[License section](https://github.com/syediu/nanobench-iros2026/blob/934a1ab92c458cad99c9278a5cb63bf68af6e56c/README.md#license)
applies BSD-3-Clause to the dataset as well as the codebase.
[Audit sources](../Data/nanobench-baseline/audit-sources.json) record that statement,
retrieval dates and hashes separately from the software license designation.
The [license terms](../Data/nanobench-baseline/NANOBENCH_LICENSE.txt) and attribution
accompany the excerpt and metadata. Referenced Bitcraze firmware remains under
its upstream GPL license; the acquisition cache preserves the source headers.

## Inventory and split

[Inventory](../Data/nanobench-baseline/inventory.json) is the source for file
counts, duplicate identities, columns, metadata, raw block counts, grid gaps,
PWM range and voltage range. It covers every flight CSV in the pinned source
tree, including the auxiliary benchmark directories. The tree contains fewer
main recordings than the upstream README's advertised total. Auxiliary files
lack paired metadata and are excluded. Exact byte duplicates are counted once;
the manifest groups their trajectory families in the same split.

[Split assignments](../Data/nanobench-baseline/split.json) and the
[metric/processing protocol](../Data/nanobench-baseline/protocol.json) were
committed in `7e2be09` before the implementation or any model comparison.
The previously inspected `A1b_multisine_sysid_rep1.csv` was recovered byte for
byte from existing scratch work. Its hash is recorded in the split. The entire
excitation family belongs to development, together with oval and battery-drain
flights. Star, trefoil and lissajous families are reserved for final testing;
the remaining main families are training. Repeats, speed variants and controller
variants within each family stay together.

The intended generalization is across trajectory families on the same
instrumented vehicle. This split cannot establish transfer between aircraft or
independent collection campaigns. Inspecting all files for the fixed inventory
and data-quality checks exposed their schemas and ranges, but no final-test
model errors. Only development files entered the replay.

## Signal interpretation

The signal reference is the pinned
[NanoBench column reference](https://github.com/syediu/nanobench-iros2026/blob/934a1ab92c458cad99c9278a5cb63bf68af6e56c/README.md#csv-column-reference).
The metadata names collection firmware `2025.12.1`, resolved to
`252b41341a078c29662ff7bd580985befce42a6c`. The register's candidate curves use
the separately pinned revision in the
[register guide](../Engineering%20Data/README.md#firmware-thrust-curves).

| Signal or convention | Interpretation and check |
| --- | --- |
| `motor_motor_m1` through `m4` | The collection [stabilizer](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/modules/src/stabilizer.c#L208-L260) compensates battery voltage and caps commands before `motorsSetRatio`. The [driver](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/drivers/src/motors.c#L474-L511) stores the final ratio, including overrides; its [log variables](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/drivers/src/motors.c#L754-L770) reference that stored ratio. These are post-compensation PWM. Apply the voltage-to-thrust curve once. |
| Other commands | Position/yaw setpoints and legacy PID outputs are inventoried. The PID thrust request and legacy pitch/yaw signs are not substituted for motor PWM or physical torques. |
| Motor geometry | With body x forward, y left and z up, positions for M1 through M4 are `(d,-d)`, `(-d,-d)`, `(-d,d)`, `(d,d)`, where `d=arm/sqrt(2)`. The collection [SI mixer](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/modules/src/power_distribution_quadrotor.c#L94-L115) gives body yaw-reaction signs `-,+,-,+`. Thus M1/M3 rotor spin is positive about z and M2/M4 negative under the standard reaction-torque interpretation. Tests independently check roll/pitch with `r cross F` and invert the SI mixer. |
| `qx,qy,qz,qw` | Scalar-last Hamilton quaternion, interpreted as body to world. World z points up. Rotation and gravity tests include tilted thrust and free fall. The `frame_check` rows compare published Vicon world angular rate, rotated into body axes, with body gyro on development flights. They check consistency without estimating a correction. |
| `imu_acc_*` | Body specific force in g. Convert using the protocol gravity constant. The prediction is total thrust divided by mass along body z; gravity is added only after rotation for world acceleration. |
| `imu_gyro_*` | Body rate already in rad/s in the distributed CSV. Collection [firmware logs](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/modules/src/stabilizer.c#L632-L646) are deg/s; do not convert the CSV a second time. |
| `px,py,pz,vx,vy,vz` | Vicon world position and published differentiated velocity in SI units. Initial states and evaluation targets use these columns. |
| Voltage | Recorded battery voltage in volts. Use it as a known replay input; do not infer current, motor RPM or future battery behavior. The firmware's compensation filter is not applied again. |
| Onboard estimates | The onboard EKF was Vicon aided. Its states are inventoried but are not an independent reference or a substitute for onboard-only sensing. |

## Model and numerical protocol

The [register](../Engineering%20Data/platform_crazyflie.csv) supplies measured
instrumented mass (CF-011), the stock-model diagonal inertia prior
(CF-020 through CF-022), firmware arm (CF-048), and the candidate cubic/torque
parameters. The code reads these rows directly. It does not use the upstream
loader's stock-mass fallback. Instrumented mass with stock-model inertia is an
explicit hybrid assumption; the charging deck and markers have no sourced
inertia tensor in these inputs.

For each motor, `v_motor = v_battery * PWM / 65535`. Evaluate the candidate
cubic at that voltage, force exactly zero at stopped PWM, and clip negative
polynomial thrust to zero. A nonzero intercept never starts a stopped motor.
`THRUST_MIN` is an inversion bound; `THRUST_MAX` scales firmware commands.
Neither supplies an empirical validity interval or a measured physical maximum.
The run records positive-command values below the former and predictions above
the latter without silently saturating them.

The rigid-body equations are:

```text
f_body = [0, 0, sum(T_i)/mass]
a_world = R(q) f_body + [0, 0, -g]
tau = [d*(-T1-T2+T3+T4), d*(-T1+T2+T3-T4), k*(-T1+T2-T3+T4)]
omega_dot = J^-1 (tau - omega cross (J omega))
q_dot = 0.5 * q HamiltonProduct [omega_x, omega_y, omega_z, 0]
p_dot = v
```

There is no drag, actuator lag, CG offset, off-diagonal inertia or individual
motor calibration in this baseline. All documented candidates are reported.
A residual ranking does not establish which propellers NanoBench used.

[Protocol](../Data/nanobench-baseline/protocol.json) holds the numerical horizons,
stride, integration step, filters, quality limits and metric definitions. RK4
uses the actual timestamp intervals, with substeps no larger than the declared
step. PWM and voltage are held over each published interval. Nominal horizons
map to grid sample counts; the run record reports their actual elapsed ranges.
Measured position, velocity, orientation and body rate initialize each start
once. Future observations are used only as targets and for the fixed quality
mask. Recorded future commands and voltage make this an input-conditioned
open-loop replay. Persistence holds world velocity and body rate and integrates
orientation with that fixed rate.

Force diagnostics compare trailing means of predicted and observed body
specific force. Angular-acceleration diagnostics backward-difference the
trailing-mean gyro and compare it with equally averaged Euler predictions using
instantaneous measured rate. This diagnostic is separate from the propagated
rate score. Force persistence uses the previous aligned sample and angular-
acceleration persistence is zero. These short-lag diagnostics benefit from
serial correlation; the multi-step rollout is the stronger comparison.

Residuals are prediction minus observation, with bias and RMSE by axis and
flight. Attitude uses the shortest quaternion geodesic angle, so its `bias`
column is mean angular distance. Numerical failures remain counted even when
finite-only error summaries are available. Empty error cells with zero count
mean no eligible data. The figure takes the Euclidean norm of axis RMSEs within
each flight, then an unweighted mean across flights. It supplies no pooled
sample confidence interval.

## Exclusions, timing and limits

The run record lists overlapping row rejection reasons and unique rejected
rows/windows. Windows must satisfy the same rules for every model through the
longest horizon. The fully inactive oval recording has no rollout score.
The battery-drain recordings contain out-of-range PWM or frequent grid gaps;
only their eligible portions contribute. No command clipping or interpolation
repairs were introduced to retain those segments. Very sparse eligible flights
still appear individually, so their small denominators are visible.

Raw per-block counts in the inventory bound the number of distinct source
samples behind the aligned grid. They are not a statistical effective sample
size. The ratio to aligned duration is descriptive because the raw recording
and trimmed CSV intervals can differ. Exact interpolation fractions, dropout
bursts and independent bandwidth require raw block timestamps. Auxiliary files
have no such counts. The dataset authors aligned clocks offline by whole-flight
cross-correlation and resampled to a common grid. This preprocessing already
uses future observations. The baseline introduces no fitted shift or scaling,
and therefore evaluates the published aligned product rather than causal raw
telemetry. The voltage column is documented as forward-filled, but the excerpt
audit below finds adjacent-row changes in the distributed product; the processing
that produced those values remains uncertain.

The collection [sensor implementation](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/hal/src/sensors_bmi088_bmp3xx.c#L297-L349)
applies calibration, alignment and low-pass filtering before logging. Its
[filter defaults](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/hal/src/sensors_bmi088_bmp3xx.c#L139-L142)
and [initialization](https://github.com/bitcraze/crazyflie-firmware/blob/252b41341a078c29662ff7bd580985befce42a6c/src/hal/src/sensors_bmi088_bmp3xx.c#L544-L549)
limit the original signals; radio sampling and interpolation further reduce
usable bandwidth. Our trailing mean adds another frequency response and delay,
with its span fixed in the protocol. The exact Vicon differentiation filter,
per-flight clock offsets, deployed build flags and collection-script revision
are unavailable in the pinned metadata. The source trace assumes the named
unmodified firmware tag. The documented cubic calibration ranges and installed
propeller identity also remain unresolved. These gaps limit interpretation of
torque and rapid transients; this run does not attribute the exploratory
single-flight discrepancy to a cause.

## Audit of the exposed development excerpt

The [executed audit](../Data/nanobench-baseline/excerpt-audit.json) establishes
no replay implementation defect. Explicit polynomial arithmetic, per-motor
`r cross F` moments and componentwise Euler equations agree with the replay to
floating-point rounding. The selected measured rate increment still differs
substantially from the conditional prediction. The original error tables,
figure, source manifest, split and protocol are unchanged. No new regression
test was added because no implementation bug was reproduced.

The diagnostic uses the existing development fixture. It checks arithmetic on
the whole excerpt, then uses its first sample for the hand calculation, its
first interval and the shortest frozen horizon for rate increments. These
choices do not select favorable errors. The result records each motor's thrust
and moment, net moment, measured initial rate, predicted acceleration and both
observed and predicted increments. It also derives body rate from the first
quaternion pair as a convention check without optimizing an axis map or shift.

```sh
python -m Analysis.audit_nanobench_excerpt --output ../nanobench-excerpt-audit.json
```

| Finding | Effect on this replay | Remaining evidence |
| --- | --- | --- |
| Collection logging stores motor PWM after the compensation/capping path; motor IDs and the SI mixer preserve the declared order | No duplicated compensation or reordered-motor defect found | Deployed build flags and custom patches are unrecorded |
| Independent moment and angular-acceleration arithmetic agree with the implementation, while the short rate increment disagrees with observation | Preserve the conditional baseline; a residual alone cannot distinguish inertia, motor asymmetry, CG offset or timing | Installed geometry/inertia and actuator configuration, plus usable timing information |
| Published Euler columns agree with quaternion-derived radians despite the README degree labels | This is a source unit-description defect; Euler columns are unused by the replay | Consumers must verify their own chosen columns; no source data were rewritten |
| Aligned PWM values are fractional and voltage changes between adjacent grid rows | These values are processed inputs; the original integer PWM stream and voltage holds cannot be reconstructed from the grid alone | Raw block times, alignment offsets and collection/preprocessing code |

The [source audit](../Data/nanobench-baseline/audit-sources.json) rechecks the
collection driver, stabilizer, mixer, motor IDs, sensor processing and platform
constants at their pinned revisions. The register's mass describes the dataset
configuration; its inertia remains a stock-model prior. Source sensor filtering
and recorded block counts constrain what can be inferred about fast dynamics,
but neither identifies the effective post-interpolation bandwidth. No fitted
lag, battery correction, inertia or motor gain is justified by this excerpt.

Owner exercise: use the first fixture row and the registered `cf21plus_firmware` curve to
calculate M4's motor voltage and thrust. Form its moment from its body position
and reaction-torque sign, then sum all motor moments and apply Euler's equation.
Multiply the initial angular acceleration by the first timestamp interval and
compare it with the difference of the next two gyro rows. Check the independent
arithmetic against `first_row` and `intervals` in the audit JSON. Explain why a
correct calculation with the stated priors can still disagree with the measured
increment. This is an estimation diagnostic with no invented acceptance threshold.

## Next decision

The subsequent [public-source timing qualification](nanobench-g1.md) records the
unresolved collection evidence and the stop before fitting. The
[roadmap](../ROADMAP.md#current-step) holds the current action.

The same evaluator can later compare the reserved split with a frozen fitted
model. It requires `--split final_test`, `--frozen-model path.json` and
`--protocol-sha256` matching the committed protocol. That file must contain
`protocol_sha256`, `training_result`, `frozen_commit`, and `model` with the keys
returned by `documented_models()`. The measured mass remains fixed. Its hash is
recorded in the output. This interface supports the current physical model;
any different model class or preprocessing needs a development-only revision
before final evaluation. Supplying these fields records provenance; it cannot
prove a human has kept final outcomes uninspected. Final evaluation was not run
in this PR.
