# Preliminary Calculations

These calculations are the first sizing pass for the protected throwable micro-UAV. Replace assumptions with measured values as parts are selected.

## Mass and Thrust Requirements

The maximum mass is not frozen. Current planning rollup:

| Value | Result |
|---|---:|
| Sigma best | 123.86 g |
| Sigma nominal | 135.66 g |
| Sigma worst | 156.0 g |
| Proposed frozen maximum | 165.0 g |

Freeze rule:

```math
\begin{aligned}
\text{frozen maximum mass} &= \operatorname{roundup}_{5\,\text{g}}\left(\Sigma_{\text{worst}} + 5\ \text{g}\right)\\
\text{nominal margin} &= \text{frozen maximum mass} - \Sigma_{\text{nominal}}
\end{aligned}
```

### Decision: the 225 g abort threshold and its 25 g buffer (REQ-MASS-002)

**Status: retrospective assessment with an unresolved allocation, 2026-09-25.**

**Question.** The regulatory class boundary is 250 g. The abort threshold is set
at 225 g. What must the 25 g difference absorb, and is 25 g the right size?

**Known inputs**

| Symbol | Value | Units | Provenance |
| --- | --- | --- | --- |
| $m_{\text{reg}}$ | 250 | g | *requirement* — regulatory class boundary (FAA Part 107 Category 1 takeoff mass; see `literature/notes/03` §4) |
| $m_{\text{abort}}$ | 225 | g | *selected design value* — `ABORT_THRESHOLD_G`, `Analysis/budget.py:12` |
| $m_{\text{frozen}}$ | 165 | g | *calculated result* — $\operatorname{roundup}_{5\,\text{g}}(\Sigma_{\text{worst}} + 5\ \text{g})$ |
| $\Sigma_{\text{worst}}$ | 156.0 | g | *calculated result* from `mass_budget.csv` |

**Model.** The threshold is a buffer, not a computation:

```math
\begin{aligned}
\text{buffer} &= m_{\text{reg}} - m_{\text{abort}} = 250 - 225 = \text{25 g} \quad (10\,\%\ \text{of the regulatory limit})\\
\text{current headroom} &= m_{\text{abort}} - m_{\text{frozen}} = 225 - 165 = \text{60 g}
\end{aligned}
```

**Unit check.** All terms in grams. ✓

**What the buffer must absorb — and what is actually quantified**

| Contributor | Quantified? |
| --- | --- |
| Scale/measurement uncertainty at final weigh-in | **no** — no scale identified (see OQ-012 for the bench chain) |
| Battery unit-to-unit variation | partly — `mass_budget.csv` gives 28/29/31 g best/nominal/worst for EST-MASS-005 |
| Fasteners, adhesive, wire dressing, heat-shrink not itemised | **no** — `UNMODELED_HARDWARE_G` = 5 g exists but is itself an unjustified constant (audit Tier C) |
| Post-freeze additions (markers, tape, guards, instrumentation) | **no** |
| Paint/finish, moisture uptake in printed parts | **no** |

**Result.** The buffer is **25 g = 10 % of the regulatory limit**, and the current
design sits 60 g below the abort threshold — so the threshold is not currently
binding. **The 25 g is not allocated to any quantified contributor.** It is a
round 10 % of the limit, and this audit found no record of it being derived from
the list above.

**Sensitivity.** Because current headroom (60 g) exceeds the buffer (25 g), the
choice of buffer size has **no effect on any present decision**. It becomes
consequential only if the frozen maximum rises above 225 g, i.e. after ~36 % mass
growth. That is why this is P1 for *traceability* but not urgent for *design*.

**Decision.** Retain 225 g. Record explicitly that it is a **selected round
buffer, not an allocated one**, and that the repository does not currently
justify 25 g over, say, 20 g or 30 g.

**Validation / what would close this.** Either (a) allocate the 25 g against the
table above once a weighing method and its uncertainty exist, replacing the round
number with a sum; or (b) state it as a deliberate policy margin and stop
implying it is derived. **Do not** treat the present analysis as having closed it.
Status: **unresolved allocation.**

At the current proposed 165 g maximum:

```math
\begin{aligned}
T_{\text{required, total}} &= 2.0 \times \text{165 g} = \text{330 g}\\
T_{\text{required, motor}} &= \text{330 g} / 4 = \text{82.5 g}
\end{aligned}
```

This is only the static requirement. The recovery case may require greater thrust and torque.

### Decision: why thrust-to-weight ≥ 2.0 (REQ-PROP-001)

**Status: retrospective assessment, 2026-09-25.** The requirement predates this
analysis and its original rationale is not recorded; `requirements.csv` states
only "Minimum static control authority". What follows assesses whether 2.0 is
defensible, and does **not** claim to be the reason it was first chosen.

**Question.** What does the thrust-to-weight ratio have to be for hover to sit at
the collective that gives the most roll/pitch authority?

**Known inputs**

| Symbol | Value | Units | Provenance |
| --- | --- | --- | --- |
| $T_{\max}$ | 4× per-motor static thrust | N | *selected design value*, gated by the propulsion bench (OQ-001) |
| $\mathrm{arm}$ | 0.060 | m | *provisional estimate* — ASSUMED until CAD (audit Tier C) |
| $m g$ | hover thrust | N | *calculated result* from the mass rollup |

**Assumptions**

- Four-rotor X mixer, per-rotor thrust bounded to $[0,\ T_{\max}/4]$.
- Differential pairs: raise one pair by $d$, lower the other by $d$, holding
  collective. This is the model already used in `sim_release_recovery.py`.
- Static case; no aerodynamic or battery-sag terms.

**Model.** Roll/pitch differential torque available at collective $T$ is

```math
\tau_{\text{rp}}(T) = 2\sqrt{2}\,\mathrm{arm}\,d_{\max}, \qquad d_{\max} = \min\left(\frac{T}{4},\ \frac{T_{\max}}{4} - \frac{T}{4}\right)
```

$d_{\max}$ is the smaller of the headroom below the upper bound and the room above
zero, so it is maximised where the two are equal:

```math
\frac{T}{4} = \frac{T_{\max}}{4} - \frac{T}{4} \quad\Rightarrow\quad T = \frac{T_{\max}}{2}
```

**Substitution.** Hover requires $T_{\text{hover}} = m g$. Placing hover at the authority
optimum therefore requires

```math
m g = \frac{T_{\max}}{2} \quad\Rightarrow\quad \frac{T_{\max}}{m g} = 2.0
```

**Unit check.** $T_{\max}/(m g)$ is N/N — dimensionless, as a thrust-to-weight ratio
must be. $\tau_{\text{rp}}$ is (m)(N) = N·m. ✓

**Result.** **T/W = 2.0 places hover exactly at the collective of maximum
roll/pitch authority.** Verified numerically against `mixer_torque_limit()`:
the peak sits at 0.5000 of $T_{\max}$ (peak 0.0891 N·m at $T_{\max}$ = 4.2 N,
$\mathrm{arm}$ = 60 mm), i.e. T/W = 2.0000.

**Sensitivity.** Authority falls away on both sides of the optimum, and it
vanishes at both $T = 0$ and $T = T_{\max}$. A vehicle at T/W = 1.5 hovers at 67 %
collective and a vehicle at T/W = 4 hovers at 25 % — both on the falling flank.
Because $d_{\max}$ is piecewise linear, authority at hover is
$\tau_{\text{rp}} = 2\sqrt{2}\,\mathrm{arm}\,(T_{\max}/4)\,\min\left(\frac{1}{T/W},\ 1 - \frac{1}{T/W}\right)$, so it degrades roughly
linearly in the distance from T/W = 2.

**Decision.** Retain T/W ≥ 2.0. It is not an arbitrary round number: under the
mixer model this repository already uses, it is the value that maximises the
control authority available at hover, which is precisely the quantity the
recovery study is limited by.

**Caveats.** This justifies the ratio under the *mixer* authority model with an
*assumed* 60 mm arm. It says nothing about whether the locked propulsion set
achieves the required absolute thrust (OQ-001, bench-gated), and the $\geq$ form
means higher T/W is permitted even though it moves hover off the optimum — if
that matters, the requirement should become a band, which is a change this audit
does **not** make.

**Validation.** Measure static thrust per motor at 7.0 V (OQ-001) and the actual
arm from CAD; recompute. Status: **predicted, not measured.**

Hover thrust per motor:

```math
T_{\text{hover, motor}} = \frac{\text{mass}}{4}
```

| Mass | Hover Thrust Per Motor |
|---:|---:|
| 140 g | 35.0 g |
| 150 g | 37.5 g |
| 160 g | 40.0 g |
| 180 g | 45.0 g |
| 200 g | 50.0 g |

The selected motor/prop/battery combination should produce hover thrust well below maximum throttle.

## Locked Propulsion Gate

The catalog combination is EX1103 11000KV + Gemfan 2023-3 + GNB 2S 550 mAh.
Its performance is not settled: the 121.9 gf/motor and 9.2 A/motor point is a
vendor result and must be reproduced.

Planning interpretation:

- Static per-motor thrust must be at least one quarter of twice the frozen maximum mass.
- Recovery torque and angular acceleration may drive a higher requirement.
- ESC current rating should cover peak current with margin.
- Hover current must be estimated from thrust data, then measured on the built vehicle.

The bench sweep is performed at 8.4 V, 7.6 V, and **7.0 V at the ESC input under
load**. The uncertainty-adjusted 7.0 V value controls acceptance:

```math
\begin{aligned}
T_{\text{required per motor}} &= \frac{2 \times \text{vehicle mass}}{4}\\
M_{\text{allowable}} &= 2 \times \text{measured per-motor thrust}
\end{aligned}
```

At 225 g, the full-reserve threshold is 112.5 gf/motor. At the current 135.66 g
nominal mass, the threshold is 67.83 gf/motor. A shortfall against 225 g first
reduces the frozen mass; it does not automatically trigger a prop change.

## Battery and Flight Time

Estimated flight time:

```math
t_{\min} = \frac{60\, C_{\text{usable}}}{I_{\text{avg}}}
```

Where:

- $C_{\text{usable}} = 0.8 \times \text{nominal capacity}$
- $I_{\text{avg}}$ = average current during flight

Example for a 2S 550 mAh pack:

```math
C_{\text{usable}} = 0.550\ \text{Ah} \times 0.8 = 0.440\ \text{Ah}
```

If average hover current is 9 A:

```math
t_{\min} = \frac{60 \times 0.440}{9} = 2.93\ \text{min}
```

If average hover current is 7 A:

```math
t_{\min} = \frac{60 \times 0.440}{7} = 3.77\ \text{min}
```

Expected early prototype flight time:

```text
2-4 minutes
```

Longer flight time should not be pursued by adding battery mass until hover and recovery control margins are proven.

## Prop Guard Geometry

Guard inner diameter:

```math
D_{\text{inner}} = D_{\text{prop}} + 2c
```

Where:

- $D_{\text{prop}}$ is propeller diameter
- $c$ is radial clearance, target `2-3 mm`

Guard outer diameter:

```math
D_{\text{outer}} = D_{\text{inner}} + 2t_{\text{wall}}
```

Where:

- $t_{\text{wall}}$ is guard wall thickness, starting target `1.5-2.5 mm`

Example for a 2.0 in prop:

```math
\begin{aligned}
D_{\text{prop}} &= 50.8\ \text{mm}, \quad c = 2.5\ \text{mm}, \quad t_{\text{wall}} = 2.0\ \text{mm}\\
D_{\text{inner}} &= 50.8 + 2(2.5) = 55.8\ \text{mm}\\
D_{\text{outer}} &= 55.8 + 2(2.0) = 59.8\ \text{mm}
\end{aligned}
```

With four circular guards in an X layout, a 90-100 mm diagonal motor wheelbase gives a compact but plausible 125-140 mm outer footprint depending on guard spacing.

## Guard Functional Elastic Check

Define:

- $k$: radial guard stiffness, `N/m`
- $c_\sigma$: stress per unit force, `Pa/N`
- $E_{\text{impact}}$: conservatively assigned impact energy, `J`

```math
\begin{aligned}
\delta_{\text{impact}} &= \sqrt{2 E_{\text{impact}} / k}\\
F_{\text{equivalent}} &= \sqrt{2 E_{\text{impact}} k}\\
\sigma_{\text{impact}} &= c_\sigma F_{\text{equivalent}}
\end{aligned}
```

Acceptance:

```math
\begin{aligned}
\text{available clearance} / \delta_{\text{impact}} &\geq 2\\
\text{elastic allowable stress} / \sigma_{\text{impact}} &\geq 3
\end{aligned}
```

This is a low-energy linear-elastic functional check only. It cannot establish high-energy fracture survival.

## Recovery Timing

Recovery cannot be specified only as "stable within 3 seconds." During ideal free fall, distance grows with the square of time:

```math
d = \tfrac{1}{2}\, g\, t^2
```

| Unarrested Fall Time | Ideal Fall Distance |
|---:|---:|
| 0.25 s | 0.31 m |
| 0.50 s | 1.23 m |
| 0.75 s | 2.76 m |
| 1.00 s | 4.91 m |

The recovery test must separately measure:

- launch-detection latency
- motor-start latency
- attitude-arrest time
- vertical-velocity-arrest time
- time until stable hover
- minimum successful release height
- gyro saturation and estimator disagreement

The fixed 3 s value is used only as the stable-hover confirmation window after recovery, not as an acceptable time to recover.

Stable-hover confirmation:

- roll/pitch within +/-5 deg
- yaw rate below low threshold selected during tuning
- no cage contact
- altitude remains inside test envelope
- all conditions hold for 3 s

Recovery success criteria must be set from fixture data after the propulsion system, controller, and release conditions are defined. Tests should report success rate across release height, initial attitude, initial angular rate, and battery voltage.

The initial angular rate must remain below 80% of the verified gyro range. Recovery outside the externally validated estimator envelope is rejected.

The executable preliminary model and its verification tests are under [Analysis](../Analysis/README.md).

## Marker Tracking Limits

Initial command envelope:

| Command | Limit |
|---|---:|
| Horizontal velocity | 0.3 m/s |
| Yaw rate | 30 deg/s |
| Altitude change rate | 0.2 m/s |
| Target distance | 1.0-1.5 m |
| Target lost hold | 2 s |
| Target lost land | 5-10 s |

The first tracking controller should be yaw-only. Translational following should be enabled only after marker detection latency and hover stability are measured.

## Launch Detection Signals

Initial log channels:

- acceleration magnitude
- gyro magnitude
- attitude estimate
- battery voltage
- flight mode
- state-machine state
- classifier decision
- timestamp

Initial event classes:

| Actual Event | Expected Classification |
|---|---|
| held still | no launch |
| normal hand motion | no launch |
| bump while held | no launch |
| walking with drone | no launch |
| placed on table | no launch |
| controlled drop | launch candidate |
| controlled release | launch candidate |
| excessive tilt/rate | reject recovery |

No live recovery threshold should be trusted until a log dataset, confidence-bound analysis, and confusion matrix exist. Zero observed events are never reported as a true zero event rate.
