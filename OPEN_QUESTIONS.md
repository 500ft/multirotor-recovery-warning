# Open questions

The [roadmap](ROADMAP.md) is the only execution plan. The
[dependency decision](docs/decisions/dependency-roadmap.md) adopts the qualification
and mandatory physics-baseline sequence; physical choices remain open.

## Active evidence questions

| ID | Question | Status and closure evidence |
| --- | --- | --- |
| MR-D1 | Can the selected public file support a continuous response summary with known units, controller and permission? | CLOSED for the selected QDrone2 development recording; [executed report](docs/qdrone-response.md) |
| MR-D2 | Are independent pack/run identities and maneuver completion outcomes available? | OPEN; selected QDrone2 recording has repeated commands and no recovery labels; closure needs independent labeled outcomes |
| MR-D3 | Does the warning improve on delay-aware physics feasibility, voltage, sag-history and load baselines under withheld conditions? | UNTESTED; requires qualified outcomes, frozen whole-pack splits, false-alarm burden and useful lead-time criterion |
| MR-D4 | Can NeuroBEM be reused, and what does its timing support? | OPEN; processed motor speed is not maximum authority; no derived analysis before permission/timing qualification |
| MR-D5 | Are the selected propulsion configuration, installed force/current/voltage/RPM/temperature channels and containment qualified? | OPEN; roadmap A requires calibration, capacity/resolution, tare, timing and approval; torque needs a separate qualified method if used |
| MR-D6 | Is a delay-aware thrust-to-weight/height-to-arrest comparator supported by measured configuration inputs? | OPEN; roadmap B and C must complete before warning comparison |

## Pending owner decisions

| ID | Owner choice | Status |
| --- | --- | --- |
| M1 / MR-1 | Adopt the maneuver-warning question and dependency roadmap? | ADOPTED for the question, completed public-data task and [dependency-plan cleanup](docs/decisions/dependency-roadmap.md); no physical execution approval |
| M2 | Choose concrete borrowed or self-funded hardware, configuration, site and budget; resolve any G5 purchase approval separately. | PENDING; [adopted access disposition](docs/decisions/dependency-roadmap.md#physical-access-disposition) pauses experimental qualification until physical access is selected. Closure is recommended while no route exists; neither closure nor purchase is approved. |
| M3 | Specify recovery maneuver, available height and independent completion criterion? | PENDING |
| M4 | Identify test facility and responsible safety owner? | PENDING |

## Superseded Crazyflie execution questions

These questions leave the active queue with the [successor decision](docs/decisions/maneuver-warning-v2.md).
Their scientific gaps remain unresolved; superseded does not mean answered.

| ID | Preserved question | Status |
| --- | --- | --- |
| OQ-018 | Which dynamics parameters can NanoBench identify? | SUPERSEDED as active work; G1 incomplete, no fitted model or final-test result |
| OQ-019 | Which command meaning, propellers and thrust mapping apply? | SUPERSEDED as active work; deployed settings/configuration unresolved in [source audit](docs/nanobench-baseline.md#audit-of-the-exposed-development-excerpt) |
| OQ-020 | What evidence tests recovery transfer to a purchased Crazyflie? | SUPERSEDED; actual warning-study aircraft is pending M2 |
| OQ-021 | How do the stock supervisor and estimator behave during release? | SUPERSEDED; compiled-firmware comparison remains unexecuted |
| OQ-022 | Can timing resolve lag and yaw torque separately? | SUPERSEDED as active work; [G1 timing/configuration gaps](docs/nanobench-g1.md) remain |
| OQ-023 | Which sensing/logging configuration supports physical recovery? | SUPERSEDED; must be reconsidered for M2–M4 |

## Historical and deferred questions

The rows below preserve earlier decisions and unresolved findings. Their old
OPEN labels do not schedule work on the retired designed aircraft or V995.
Facility, containment and load-cell questions require review for the eventual
physical configuration. No prior target transfers automatically.

| ID | Question | Decision Needed From | Required Evidence | Status |
|---|---|---|---|---|
| OQ-001 | Does the locked propulsion set (EX1103 11000KV / Gemfan 2023-3 / GNB 2S 550 mAh) meet thrust reserve on the bench? | Propulsion bench testing | Thrust/current/RPM curves at 8.4/7.6/7.0 V; >=112.5 gf/motor at 7.0 V for full 225 g reserve | OPEN (catalog selection LOCKED 2026-06-20; performance bench-gated) |
| OQ-002 | What is the frozen maximum flying mass? | CAD and BOM rollup | `roundup_to_5g(Sigma worst + 5 g)` and result `<=225 g` | OPEN (primary response to a propulsion miss is mass freeze, not a prop change) |
| OQ-003 | Can batteries eventually be integrated into hollow frame members? | Later packaging study | Crash protection, thermal, serviceability, and abuse testing | DEFERRED |
| OQ-004 | Which NYU facility can provide motion-capture or high-speed video access? | Faculty/lab outreach | Confirmed equipment access and supervision | OPEN |
| OQ-005 | What gyro range and estimator envelope are reliable on the Holybro Kakute H7 Mini (ArduPilot)? | Bench + flight test on locked FC | Kakute IMU datasheet, ArduPilot EKF3 config, and external-truth comparison | OPEN (FC locked: Kakute H7 Mini) |
| OQ-006 | What release heights are testable in the available enclosure? | Test-facility design | Cage dimensions and recovery simulation | OPEN |
| OQ-007 | Is the locked flight controller (Holybro Kakute H7 Mini **v1.5**) still procurable in the exact revision? | Procurement before any order | Live first-party or authorized-reseller stock of v1.5; if unavailable, an H7 20x20 successor with a re-verified UART/DShot resource map | CLOSED 2026-07-03: v1.5 in stock at Holybro direct at $58.99 (v1.3 sold out). The 2026-06-22 "effectively unavailable" finding was stale. FC stays locked. |
| OQ-008 | Are the EOL/legacy parts in the locked BOM (Matek 3901-L0X, HGLRC XJB BS13A) actually orderable now? | Procurement before any order | Confirmed in-stock standalone units, or pre-selected current substitutes | CLOSED 2026-07-03: both unavailable as standalone new stock. Substituted per gate policy (unavailability = blocker): ESC -> Flywoo GOKU G45M 45A 2-6S AM32 (6.4 g, current sensor); flow/lidar -> MicoAir MTF-01 (4.5 g, MAVLink, native ArduPilot). Budgets and interface map updated. |
| OQ-009 | Does the Flywoo GOKU G45M actually run 2S LiHV (7.0-8.4 V) under load, and does its current sensor integrate with ArduPilot battery monitoring on the Kakute? | ESC bench test before the propulsion gate | Spin-up and full-throttle at 7.0 V bench supply; BATT_AMP_PERVLT calibrated against a bench meter | OPEN (Flywoo specifies 2-6S; some retailer listings say 3-6S — treat 2S support as unverified until benched.) |
| OQ-010 | Study A/A2 action parameters awaiting owner replacement (literature review 2026-09-22 supplies anchors for several: see `literature/claim-ledger.md` B1/B2/C1): removable-guard mass share (EST 16 g of EST-MASS-012, fraction computed against the live rollup), guard inertia share (EST 0.30, needs CAD mass model), guarded impact tolerance (EST 2.5 m/s / 60 deg, needs drop data), parachute terminal speed and deployment delay (EST 1.8 m/s / 0.8 s — or a decision that no parachute variant exists), A2 yaw rotational-drag coefficient (EST 6e-6 N·m·s², needs spin bench/flight data) | Owner (CAD mass model + guard drop data + parachute decision + spin data) | CAD-split EST-MASS-012; drop-test impact tolerance; canopy datasheet or removal of the action; measured spin-down | OPEN (preregistered defaults frozen in `docs/specs/survivable-set/design.md` + `design-a2.md`; survivable-set claims blocked until replaced) |
| OQ-011 | Does the stock Veeniix V995 board expose any telemetry, command or programming interface (the `CLK` pad group, U46C-family receiver-board lead), and which MCU/IMU is on it? | Owner (B01 close-up photos, B03 continuity map) + Claude (B02 datasheet match, B04 decision) | Readable chip markings; power-off pad/net map; datasheet identity — a pad label is not a port | CLOSED 2026-10-04: V995 retired. Owner board photos show the 32-pin main chip and the second QFN both unmarked; the `CLK`/`DAT` pads were never probed. No programming route was established. |
| OQ-012 | **[Screened 2026-09-27 — 1 kg recommended, not accepted]** Which purchased load cell (1 kg PID 4540 or 5 kg PID 4541) carries the V995 whole-drone cradle, and does the NAU7802 chain resolve the ~0.49 N hover-equivalent force to the exploratory 5 % target? | Owner (installed load budget, reference masses) + Claude (calibration analysis) | Installed load budget incl. cradle/preload/off-axis; installed calibration with holdouts, hysteresis and drift (R3.5–R3.8); target stays undecided until F_ref_use and an uncertainty budget exist | DEFERRED 2026-10-04 (V995 retired; reopen for Crazyflie per-motor thrust work). Earlier screen: datasheet screen done (`cad/v995/README.md`): the 5 kg cell's published 0.03 %FS terms give U ≈ 0.02942 N, **2.4× over** the 0.01226 N target, so it is not demonstrated compliant; the 1 kg cell is the recommended candidate and must be better than **0.0625 %FS per term** to meet the target — but **no accuracy table was verified for the 4540**, so this is conditional. Neither cell is an accepted calibrated instrument; closure needs installed calibration, not a datasheet. |
| OQ-013 | What is the guard's causal mechanism for airborne recovery, and what evidence supports it — does it prevent rotor contact, preserve clearance under load, decouple contact torque, absorb deformation energy, or change drag? | Owner (mechanism statement) + drop/contact evidence | A written mechanism plus evidence for that specific construction; Briod et al. (2014) support a cage on a passive three-axis gimbal, which is NOT equivalent to rigid propeller rings | OPEN (until answered, the inverted-authority floor's coupling to guard presence is unjustified and guard causation cannot be claimed — `docs/specs/survivable-set/design.md` §6b) |
| OQ-014 | What does the 25 g buffer below the 250 g regulatory boundary (REQ-MASS-002) actually allocate to, and is 25 g the right size? | Owner (policy) or a mass-uncertainty allocation | Either an itemised allocation (weighing method and its uncertainty, battery variation, un-itemised hardware, post-freeze additions) summing to a justified buffer, or an explicit statement that it is a policy margin rather than a derived one | OPEN (not currently binding — headroom is 60 g; `Design Report/calculations.md` §Abort threshold, audit Tier B) |
| OQ-015 | What justifies `UNMODELED_HARDWARE_G` = 5 g, the guard safety factors (2.0 clearance / 3.0 stress) and the authority-gate sampling constants (n=6, 5th percentile, 25–75% band)? | Owner + itemised estimates / material data | Itemised un-modelled hardware estimate; quantified PETG property scatter tied to the stress SF; a stated basis for the sampling constants | OPEN (audit Tier C — bare constants that gate real decisions; `docs/ENGINEERING_AUDIT.md`) |
| OQ-016 | Which test cases and outcome should the new scenario comparison use? | Owner delegated the choice and execution | [Study registration](docs/specs/survivable-set/scenario-02.md) and [settings](docs/specs/survivable-set/scenario-02.json), committed before execution; [completed results](Data/scenario-02/results.json) | CLOSED: DR-SS-SCENARIO-02 adopts the proposed cases with fresh paired draws and retains the binary landing rule. Selection using earlier results is recorded. `two_adjacent` keeps its existing continuous diagnostic results; a separate follow-up is deferred while the V995 bench measurements are pending. |
| OQ-017 | Which mounting revision is the **delivered** Adafruit 4540? The 4540 PDF viewer was unreadable and the indexed 80 mm drawing sits under PID 5231; Adafruit also lists an older 80 mm 5 kg version, so product number and capacity do not fix the revision. | Owner (inspect the delivered part) | Delivered-part inspection: body length, section, hole count/coordinates/thread designations at both ends, load-end designation, usable thread depth — compared against whichever drawing the part actually matches | DEFERRED 2026-10-04 (V995 retired). Earlier status: OPEN (blocks the V995 fixture geometry from leaving `candidate_drawing`; `cad/v995/parameters.csv`) |
