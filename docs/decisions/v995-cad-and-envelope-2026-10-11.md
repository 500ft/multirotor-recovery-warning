# Decision: V995 full CAD, hand-calculated propulsion envelope and Ansys practice

## Status
Accepted 2026-10-11. Owner instruction 2026-10-11 (chat): "i want to cad the
drone fully, but the benchmarks should be hand calculated through the
manufacturing details on what is used to get a range of possible values that
the motors can produce in context with the propellers", and "do the hardest
thing possible to learn", for CAD and Ansys skill development across the
projects.

## What this authorizes
- A full CAD model of the owned Veeniix V995 built from measured dimensions
  and masses, per [evidence/v995-full-cad/measurement-worksheet.csv](../../evidence/v995-full-cad/measurement-worksheet.csv).
  Unmeasured dimensions stay blank; nothing is estimated into the model.
- The executed propulsion envelope,
  [Analysis/propulsion_envelope.py](../../Analysis/propulsion_envelope.py),
  with inputs and result in [Data/v995-envelope/](../../Data/v995-envelope/).
  It is the pre-measurement bound for roadmap step C and the expected force
  range for the bench. Every input carries an evidence state.
- Ansys studies on that model as listed in
  [evidence/v995-full-cad/README.md](../../evidence/v995-full-cad/README.md),
  each with the measurement that would validate it. Unpowered validation (tap
  test, scale) needs no further approval.

## What this does not decide
- The study aircraft. M2 in OPEN_QUESTIONS.md stays pending; the V995 was
  retired as the study platform on 2026-10-04 and this decision does not
  reinstate it.
- Any powered run, including a hover on a scale. Roadmap A.3 and the owner's
  approval still gate it.
- Any purchase (G5).

## Sources used for the envelope
Deters, Dantsker, Kleinke, Norman and Selig, AIAA 2018-4122, Table 3 (static
thrust at maximum rpm for 30 to 66 mm quadrotor propellers; read from the
author's PDF). Bitcraze Crazyflie 2 thrust table (2015, whole vehicle, power
box supply) and the 2022 thrust-upgrade post. Hobby listing for a 0716 coreless
motor (2 A maximum). Manufacturer FAQ for the 3.7 V 180 mAh pack as already
recorded in the hardware inventory. Listing weight 22.3 g (search 2026-10-11),
against the owner's 50 g estimate; AC-06 settles it.
