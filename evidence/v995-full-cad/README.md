# V995 full CAD and propulsion envelope

Owner instruction 2026-10-11 (chat): model the V995 fully in CAD, hand-calculate
the propulsion benchmarks from manufacturing details to get a range of values the
motors can produce with the propellers, and take on the hardest Ansys work that
can be learned from it. Decision record:
[docs/decisions/v995-cad-and-envelope-2026-10-11.md](../../docs/decisions/v995-cad-and-envelope-2026-10-11.md).

This does not select the aircraft for the study (M2 stays pending) and approves
no powered run or purchase.

## What exists now

- [Envelope inputs](../../Data/v995-envelope/inputs.json) and
  [executed result](../../Data/v995-envelope/results.json), from
  `python -m Analysis.propulsion_envelope`. Every input carries an evidence
  state; none is a measurement of the aircraft.
- [This worksheet](measurement-worksheet.csv), 22 rows, one unpowered session
  with calipers, a 0.01 g scale and a phone camera. The rules of the
  [fixture worksheet](../v995-fixture-measurements/README.md#rules-that-make-the-readings-usable)
  apply: three repositioned readings where the row says 3, record the datum,
  leave a row blank rather than estimate it.

The envelope result at the three corners (total thrust, four rotors): low
5 g, nominal 34 g, high 83 g. At the listed 22.3 g the nominal thrust-to-weight
is 1.5; at the owner's 50 g estimate it is 0.7, which would not hover. The
implied blade-pass frequency at the nominal corner is about 1.5 kHz. The
single highest-leverage number is still AC-06, the flight-ready mass on a
scale.

## CAD: what to model and what each part needs

Build the assembly in SOLIDWORKS from the worksheet, one part per physical
part, with the scale mass assigned to each part so the assembly mass
properties can be checked against DR-01, DR-02 and AC-06.

| Part | Rows | What it is for |
| --- | --- | --- |
| Shell (top, bottom) and arms | DR-06 to DR-09, DR-18, DR-19 | modal and harmonic models; mass distribution |
| Motor pod and motor mockup (cylinder) | DR-14, DR-15 | motor class for the envelope; pod mass at the arm tip sets the arm mode |
| Propeller (one blade, circular pattern; CW and CCW) | DR-10 to DR-13 | rotor CFD geometry; CT; blade-pass frequency |
| Guard ring and struts | DR-16, DR-17 | impact model; clearance |
| Battery, PCB block, camera, feet | DR-20, DR-21 | mass distribution only; no detail inside |

Model one propeller blade from the 75 percent station chord and pitch and the
tip and root; do not invent an aerofoil section. A photographed silhouette with
a scale bar is a measurement, a guessed NACA section is not.

## Ansys: the ladder, with the measurement that validates each rung

Each rung names the measurement that would show the model is right. A rung
without its measurement is practice, which is fine, but it is not evidence and
does not enter the roadmap.

| Rung | Model | Inputs | Validating measurement | Difficulty |
| --- | --- | --- | --- | --- |
| 0 | Assembly mass properties | per-part masses from the scale | AC-06, DR-01, DR-02 within scale resolution | easy |
| 1 | Modal analysis of the frame (free-free, then supported at the feet) | geometry; E and density as a datasheet range for the marked material family (DR-19) | tap test with the owned LIS3DH at 1344 Hz data rate (modes below about 600 Hz) or a phone accelerometer; fit E from the first mode, check the second within 20 percent | moderate |
| 2 | Harmonic response at rotor 1P and 3P across the envelope rpm range (1P 330 to 780 Hz, 3P 1.0 to 2.4 kHz) | rung 1 model; unbalance as a declared force | phone microphone spectrogram during a hover: frame peaks stay put while rotor peaks move with throttle | moderate |
| 3 | Rotor CFD in Fluent: one propeller, moving reference frame, laminar or transition SST at Re near 10^4, prism layers on the blade | measured blade geometry (DR-10 to DR-13); rpm from the envelope | first the published case, then the V995: see below | hard; the most useful thing on this list |
| 4 | Guard impact, explicit dynamics | guard geometry; material from DR-19 range | none available without a drop test and high-speed video; practice only | hardest |

Rung 3 has a complete published validation case before any V995 data exists.
Bitcraze publishes the Crazyflie 2 propeller mesh
(`propellers/BCP47-17_1000_vertices.stl` in the bitcraze-mechanics repository;
a decimated 1000-vertex STL, so expect to rebuild a clean surface from it),
Deters et al. 2018 Table 3 gives 10 g at 20,000 rpm for that 47 mm propeller
at Re 20,500, and the Bitcraze 2015 whole-vehicle table gives 57.9 g total at
23,882 rpm (14.5 g per rotor if the four are equal). Success criterion: CT
within 15 percent of both points. Only then run the V995 blade and compare
with the hover check below.

## The first powered check, and what it needs

A hover on a scale, the Bitcraze way (hold the aircraft down, read the lost
weight), with a phone spectrogram recording the blade-pass tone, gives thrust
and rpm at once. With DR-10 that is a direct CT for the real propeller and
replaces two declared ranges in the envelope. It spins propellers, so it falls
under the roadmap's powered-bench rule (A.3 review and owner approval), even
for a guarded 22 g toy.

## What this work does not claim

The CAD is a record of measured geometry and a learning platform. The envelope
bounds a force range from declared inputs. Neither is the physics baseline of
roadmap step C, which needs measured thrust, mass and delays on the aircraft
the study actually selects.
