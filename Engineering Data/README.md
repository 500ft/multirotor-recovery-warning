# Engineering data

Current QDrone2 component inputs and their archive source are in
[sources.json](../Data/qdrone-response/sources.json); analysis settings are in
[protocol.json](../Data/qdrone-response/protocol.json). No dynamics parameter fit
or aircraft selection is implied by this descriptive response result.

[platform_crazyflie.csv](platform_crazyflie.csv) retains the prior NanoBench and
Crazyflie configuration register unchanged. The firmware notes below apply to
that earlier study. Other tables describe the historical designed aircraft
unless explicitly labeled otherwise. Keep these vehicles separate; the
[roadmap](../ROADMAP.md) defines current work.

## Parameter evidence

Each row identifies its configuration, unit, source and locator. A manufacturer's
specification, a published measurement, a literature model and a firmware default
are distinct evidence types. None means this project measured a delivered part.

Add identified parameters as separate rows with the training configuration,
result-file location, fit bounds and uncertainty. Keep the published rows so a
reader can compare the initial model with the fit. A later physical measurement
also gets its own configuration and evidence reference. Mass, inertia and
propulsion from different airframes must not be combined silently.

## Firmware thrust curves

The pinned Bitcraze defaults define a per-motor cubic:

```math
v_{\text{motor}} = v_{\text{battery}} \cdot \frac{\mathrm{PWM}}{65535}
```

```math
T = c_0 + c_1 v_{\text{motor}} + c_2 v_{\text{motor}}^2 + c_3 v_{\text{motor}}^3
```

The coefficient rows and their source revision are in the CSV. These curves
are candidates for replay after checking the dataset's motor-command semantics,
propellers and voltage range. A better residual alone cannot identify which
propeller was installed. Negative intercepts and nonzero zero-voltage values
also show why a cubic must not be extrapolated to a stopped motor. Document the
valid operating range and the zero-command/dead-zone treatment.

`THRUST_MIN` bounds the firmware's inversion and `THRUST_MAX` scales commands.
The source explicitly describes the maximum as a trade-off for consistency over
battery levels. It is not an experimentally demonstrated physical maximum.
Use the selected firmware/configuration's command path when modeling saturation.
The torque ratio is another firmware default; its applicability needs checking.

In the pinned [motor driver](https://github.com/bitcraze/crazyflie-firmware/blob/f6e0f0a3b526861328caf3296a7ecf00bb915d39/src/drivers/src/motors.c),
`motorsCompensateBatteryVoltage` maps thrust requests to PWM, and
`motorsSetRatio` stores the resulting motor ratio. The
[collection-source audit](../docs/nanobench-baseline.md#signal-interpretation)
traces the logged ratio through compensation, capping and overrides at the
separate collection revision. Replaying it must not apply compensation twice.
The [timing qualification](../docs/nanobench-g1.md) leaves deployed build settings,
raw block timing and installed propulsion unresolved. Source tracing alone does
not establish the configured aircraft's response.

## Source baseline

- [NanoBench dataset and documentation](https://github.com/syediu/nanobench-iros2026/tree/934a1ab92c458cad99c9278a5cb63bf68af6e56c):
  instrumented vehicle, signal units, alignment and per-block sample counts.
  The [executed replay](../docs/nanobench-baseline.md) records acquisition hashes,
  data-license evidence and development results.
- [Bitcraze platform constants](https://github.com/bitcraze/crazyflie-firmware/blob/f6e0f0a3b526861328caf3296a7ecf00bb915d39/src/platform/interface/platform_defaults_cf2.h):
  firmware model inputs, conditional on build options.
- [CrazySim source](https://github.com/gtfactslab/CrazySim/tree/3ec8b55da4bff887da542a9f314da825460e65be):
  candidate SITL integration; pin its submodules and build options when used.

The upstream firmware and dataset preserve their own licenses. A source link
here does not relicense their code or data under this repository's MIT license.
