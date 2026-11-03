# Bench acquisition — wiring, settings and bring-up (R2, 2026-09-21)

Status: **proposed topology** for the retired V995 setup. Check it against delivered
board revisions before wiring. Vendor pinout pages S1–S11, cited in the hardware
plan, are the sources; this page records no measurements. The
[firmware](../Instrumentation/firmware/code.py) and
[host capture](../Instrumentation/bench_capture.py) implement the proposed wiring,
§3 settings and §4b incomplete-run handling. They have **not** run against real
hardware. The §4 checks start with power-off continuity; any powered step needs
a separately approved physical setup. Analysis of a completed run is later work.

The proposed chain originated with the retired V995 demonstrator and remains
available for a future configuration-specific acquisition design. The current
propulsion configuration, installed capacity, calibration, timing and containment
have not been established.
[Roadmap A](../ROADMAP.md#a-qualify-component-instrumentation-and-propulsion) sets
those prerequisites. Neither this force channel nor the INA260 measures torque;
RPM and measured component temperature need qualified channels.

Original platform note: bench chain for the Veeniix V995 demonstrator
([`evidence/week-2026-09-19/platform-capabilities.md`](../evidence/week-2026-09-19/platform-capabilities.md)).
Nothing here touches the drone's power or board (E6).

## 1. Buses and power (E1)

The QT Py RP2040 has **two** I²C buses: the STEMMA QT connector is `I2C1`
(`board.STEMMA_I2C()` in CircuitPython, `Wire1` in Arduino); the labelled `SDA`/`SCL`
pads are `I2C0` (`board.I2C()`). Do not bridge them. Bench power is USB; sensor
logic is the QT Py `3V` pad.

| Bus | Devices | Expected addresses | Physical link |
| --- | --- | --- | --- |
| `I2C1` (STEMMA connector) | NAU7802 | `0x2A` | the one purchased QT cable (PID 4210) |
| `I2C0` (`SDA`/`SCL` pads) | INA260, LIS3DH | `0x40` (default), `0x18` or `0x19` | header pins + jumpers (PID 1951/1957) |

An address ACK is not device identity: read the device ID / configuration registers
and check them against the datasheet before trusting a channel.

## 2. Connection table (E1–E4)

| From (board / pin) | To (board / pin) | Voltage | Direction | Bus / net | Wire | Source | Verified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QT Py STEMMA (V, GND, SDA, SCL) | NAU7802 STEMMA in | 3.3 V | bidir | `I2C1` | QT cable | S1, S5 | ☐ |
| QT Py `3V` | INA260 `Vcc` | 3.3 V | power | logic supply | jumper | S6 | ☐ |
| QT Py `GND` | INA260 `GND` | 0 V | — | logic GND | jumper | S6 | ☐ |
| QT Py `SDA` / `SCL` pads | INA260 `SDA` / `SCL` | 3.3 V | bidir | `I2C0` | jumpers | S5, S6 | ☐ |
| QT Py `3V` | LIS3DH `Vin` | 3.3 V | power | logic supply | jumper | S8 | ☐ |
| QT Py `GND` | LIS3DH `GND` | 0 V | — | logic GND | jumper | S8 | ☐ |
| QT Py `SDA` / `SCL` pads | LIS3DH `SDA` / `SCL` | 3.3 V | bidir | `I2C0` | jumpers | S8 | ☐ |
| Load cell E+ / E− | NAU7802 `E+` / `E−` | bridge excitation (proposed 2.4 V setting) | out | excitation | cell leads, verified by function **not colour** | S2, S3 | ☐ |
| Load cell A+ / A− | NAU7802 `A+` / `A−` | mV-level differential | in | bridge signal | cell leads | S2 | ☐ |
| Beam receiver `OUT` | QT Py `A0` (digital in; confirm GPIO number from S5) | open-collector, **pull-up to 3.3 V** | in | event | jumper | S9 | ☐ |
| Beam emitter / receiver `V`, `GND` | QT Py `3V` (or `5V` for optics only) / `GND` | 3.3–5 V | power | optics supply | jumpers | S9 | ☐ |
| INA260 `Vin+` / `Vin−` | *nothing this week* | — | — | shunt | — | S6, S7 | ☐ |

Rules that the table encodes:

- **E2** INA260 `Vin+`/`Vin−` are the two ends of the internal shunt, *not* battery
  + and −. The eventual high-side topology is `battery + → Vin+ → shunt → Vin− →
  load +`, `battery − → load −`, with one reviewed logic reference. The logged
  voltage is the VBus node (tied to `Vin+` on the Adafruit board) — name it that,
  not "motor terminal voltage". First electrical checks use a **current-limited
  dummy load**, never the drone.
- **E2** Motor/battery current never runs through breadboards, the QT cable or
  logic jumpers. The INA260 chip's 15 A figure does not rate the harness.
- **E3** Bridge current is `I_exc = V_exc / R_bridge`; the NAU7802 needs its supply
  ≥ 0.3 V above the regulated analog output, so 2.4 V is a starting proposal at a
  3.3 V supply, to check against the delivered bridge resistance and sensitivity.
  Verify load **sign** with a known mass. ADC internal calibration ≠ force
  calibration.
- **E4** Beam polarity (clear vs blocked) is established empirically and recorded.
  A beam crossing marks an event; it commands nothing.
- **E6** No connection to the V995 until connector polarity, an accessible rail,
  the current budget and the grounding scheme are known. The 5 V / 2 A charger
  input is not an accessory rail. The old 7.0 V propulsion setting does not apply.

## 3. Proposed acquisition settings (R2.4) — to verify by readback and sustained timing

| Sensor | Setting | Why | Verify |
| --- | --- | --- | --- |
| NAU7802 | one channel; 80 SPS; compare 10 SPS for static noise; gain and excitation recorded | force resolution vs bandwidth trade | data-ready status, not repeated polls; readback of gain/rate/excitation |
| LIS3DH | 100 Hz; ±2 g for static checks; documented wider range before any dynamic test | gravity checks need raw DC | per-axis saturation flag; range/mode logged on change |
| INA260 | conversion time / averaging chosen for ~100 fresh records/s **if** the configured window permits; report the real rate | fresh vs repeated samples | measurement window logged |
| Beam | edge capture with timestamp and recorded polarity | coarse event timing | 30 manual block/clear cycles vs independent count |

Clock semantics: one MCU monotonic clock for all records; `t_event`, `t_ready/read`
and host receipt are separate fields; a reset opens a new epoch. Raw streams stay
asynchronous (one CSV per sensor + one manifest); no synthetic synchronized rows.

## 4. Bring-up order (R2.1) — one thing at a time

1. QT Py alone on USB: firmware boots, monotonic clock ticks, a 10-minute idle
   record has no sequence gaps or resets.
2. Add NAU7802 on `I2C1`: ID/config readback; unloaded 60 s noise record.
3. Add LIS3DH on `I2C0`: six stationary orientations (±each axis, ~10 s).
4. Add INA260 on `I2C0`: zero, then two dummy-load points against a meter.
5. Add the beam: 30 manual cycles.
6. Combined 10-minute stationary record; deliberately unplug one sensor and reset
   the MCU during it — the capture must mark the run incomplete, not splice.

Before step 2 the owner does a power-off continuity/polarity check of every row in
§2 and ticks "Verified". Loose bench jumpers are a bench harness, not an airborne one.

## 4b. Observability contract (C06)

These tables describe the proposed acquisition chain, with the same pending
qualifications as the [source configuration](../evidence/week-2026-09-19/hardware-inventory.csv).
They do not qualify a new per-motor stand. **Missing is not zero**: unavailable
quantities cannot be plotted, fitted or labelled with a surrogate.

### Available channels after their stated checks

| Quantity [unit] | Source and frame/node | Required qualification | Permitted claim |
| :--- | :--- | :--- | :--- |
| Aggregate axial force [N] | Installed cell + NAU7802; fixture axis, cradle datum | R3 installed calibration | Whole-article axial force in the stated restraint |
| Bus voltage [V], current [mA] | INA260; declared node, VBus tied to `Vin+`; declared averaging | R2 dummy-load check | Aggregate electrical power at that node |
| Specific force [m/s²] | LIS3DH; sensor axes and mounting offset from CG | Six-orientation check | Specific force only; attitude and angular rate unavailable |
| Beam crossing [event] | IR break-beam; recorded geometry and polarity | 30-cycle check | One coarse crossing event |

### Timing, range and uncertainty still to qualify

| Quantity | Timestamp meaning | Rate/filter age and range | Uncertainty basis |
| :--- | :--- | :--- | :--- |
| Aggregate axial force | ADC data-ready | 80 samples/s nominal; conversion and filter age to be measured; cell-dependent range | Installed calibration, beyond a datasheet figure |
| Bus voltage/current | Conversion-window end | Configured window; report achieved rate; chip limits do not define harness rating | Reference-instrument comparison |
| Specific force | Sample-register read | 100 Hz proposed; ±2/4/8/16 g; per-axis saturation flag | Axis map, offsets and scale versus gravity |
| Beam crossing | Edge timestamp | <2 ms device response plus software timestamp; range unspecified | Spacing and ambient-light effects |

### Unavailable outputs

| Quantity | Availability | Missing evidence |
| :--- | :--- | :--- |
| Per-rotor force | Unavailable | No per-rotor measurement in this chain |
| Angular rate / full attitude | Unavailable | LIS3DH supplies specific force; no gyro purchased in the recorded inventory |
| Trajectory | Unavailable | External tracking |
| Fault identity | Unavailable | Qualified fault observation |
| Physical damage | Unavailable | Separate inspection record; kinematics do not supply it |

Source: original C06 channel contract and the [wiring/settings above](#1-buses-and-power-e1).
The [firmware fields](../Instrumentation/firmware/code.py) log current in mA and
specific force in m/s²; force in N requires calibration of raw ADC counts.
No calibration, rate or range has been newly verified by this table redesign.
Current stand prerequisites, including optional torque and missing RPM/temperature
qualification, remain in [roadmap A](../ROADMAP.md#a-qualify-component-instrumentation-and-propulsion).

**Offset-sensor caveat.** A sensor not at the CG also measures `α × r` and
`ω × (ω × r)`. At 20 rad/s with a 10 mm perpendicular offset the centripetal term
is ≈4 m/s² — comparable to a large tilt signal and **not** gravity. Mounting
dimensions are therefore estimation inputs and must be recorded.

### Static vs impact bandwidth (C08)

The purchased chain is a **static** force instrument and must not be promoted into
an impact instrument. At 80 SPS samples are **12.5 ms** apart; even 320 SPS gives
3.125 ms, before filter delay. A contact event is far shorter, so peak force needs
demonstrated bandwidth, a characterised mechanical response and enough samples
across the contact. Repeated drops on one damaged specimen are **not** independent
trials.

**Contact-state record**, when a contact study is eventually run — each field
stored explicitly, with damage kept separate from any kinematic proxy: vertical
velocity, lateral velocity, attitude, angular velocity, surface, contact location,
configuration, specimen history, and observed physical damage / post-event
function.

## 5. Not part of this document

Load-cell selection (1 kg vs 5 kg — needs the installed load budget, R3.2), the
cradle/fixture geometry (R3.1/R3.3, own evidence and the CAD briefing), calibration
procedure (R3.4–R3.8), and any onboard package (mass/CG first, R5.5).
