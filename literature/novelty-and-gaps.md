# Novelty assessment and open gaps

The active question is in [ROADMAP.md](../ROADMAP.md). Section 6 addresses
maneuver-specific warning. Sections 1–5 retain the earlier recovery-study
assessment as history and do not authorize those experiments.

## 1. Established — never claim as novel

| # | Established result | Anchor | Evidence |
| --- | --- | --- | --- |
| 1 | A quadrotor hovers and is position-controlled after **one rotor loss** by sacrificing yaw | Freddi/Lanzon/Longhi (2011, 2014); Mueller & D'Andrea (2014) | A, flight |
| 2 | The **relaxed-hover / primary-axis spinning** mechanism itself | Mueller & D'Andrea (2014, 2016) — **and patented, US 9,856,016 B2 + continuations** | A + IP |
| 3 | **Two-opposite** rotor loss, flight-validated at >8 m/s under wind | Sun, Wang, Chu & de Visser (T-RO 2021) | A, flight |
| 4 | **Two-adjacent and three-rotor** loss — solved analytically/in sim, and in **outdoor flight** with a single non-switching passive controller requiring no fault information | Mueller & D'Andrea (2016); **Ke, Cai & Quan (T-RO 2023)** | A, outdoor flight |
| 5 | **Recovery from arbitrary tumbling attitude/rate** after a rotor loss, including the allocator constraint that makes it work | **Sun, Baert, Strack van Schijndel & de Visser (ICRA 2020)** | A/B, MC + flight |
| 6 | Onboard-only operation through the post-failure spin (vision-based estimation; NMPC with per-rotor constraints) | Sun et al. (RA-L 2021); Nan et al. (RA-L 2022) | A/B, flight |
| 7 | **Fast detection exists**: 0.18 s identification with 0.60 m height loss | Tzoumanikas et al. (ICRA 2020) — *hexacopter, a floor not a quad number* | A/B |
| 8 | Controllability under **partial degradation** is solved theory: classical LTI controllability is insufficient under positive/bounded inputs | Du, Quan, Yang & Cai (JGCD 2015) | C |
| 9 | A **two-action switching threshold** between adaptive compensation and full FTC, derived experimentally | **Mao, Yeom, Nair & Loianno (RA-L 2024)** | B |
| 10 | Learned passive FTC spanning fault-free → partial → complete single-rotor failure without switching | Chen et al. (IROS 2025) | modality unverified |
| 11 | **Redistributed pseudo-inverse** allocation — our method, 30 years old, and known-suboptimal | Virnig & Bodden (1994); Härkegård (2002) | A/B |
| 12 | **Attitude-priority desaturation** (roll/pitch → collective → yaw) | Faessler et al. (RA-L 2017); PX4 airmode | A / deployed |
| 13 | **Monte-Carlo estimation of a quadrotor safe flight envelope**, substituting for HJ reachability | **Sun & de Visser (AIAA 2019)** | B |
| 14 | Parachute recovery of small UAS **at ≥900 g**, with a 10–15 m altitude floor | ASTM F3322; EASA M2 MoC; Siotia et al. (2026); ParaZero test data | A / B / C |
| 15 | Onboard loss-of-control warning with scenario-dependent transfer; see the [full-text findings](notes/07-loss-of-control-prediction.md#verified-paper-findings) for scope and failures. | Altena, van Beers & de Visser (JAIS 2023) | Full article reviewed; no local reproduction |

## 2. Genuinely open — the defensible lane

The literature is overwhelmingly about **one action**: here is a controller, it
stabilises the damaged vehicle. Recovery as a **choice among qualitatively
different actions, indexed by post-failure state**, is close to unoccupied.

1. **Action selection over (h, v_z, tumble rate, detection delay).** Mao et al.
   (2024) do two actions on one axis (damage severity). Nothing maps the
   height / vertical-speed / tumble-rate / detection-delay space to a *choice*.
2. **Height and vertical speed as decision variables.** The FTC literature
   reports height loss as an *outcome* (0.60 m), never as an *input that changes
   which action is correct*. The only altitude-indexed numbers found come from
   the parachute literature, which does not talk to the FTC literature.
3. **The recoverable set as a function of detection delay.** Everyone reports how
   fast they detect; nobody publishes "at 0.3 s delay and 4 m height, thrust
   reallocation cannot succeed for failure class X." **This is the natural core
   of our contribution.**
4. **The abort boundary.** Sun et al. (2020) recover from arbitrary attitude at
   generous altitude; nobody characterises where the **vertical budget** runs out
   first.
5. **Sub-250 g complete rotor loss: search-bounded, not empty** (amended
   2026-09-24). We found no published demonstration of recovery from *complete*
   rotor loss below 250 g — but a dedicated verified pass was not completed, so
   this is an open question rather than a confirmed gap. **Partial degradation at
   this scale is NOT open**: Çintaş & Özyer (2026) demonstrate it in real flight
   on a 30.6 g Crazyflie. The earlier claim that the spin/sensing failure mode
   "worsens as the vehicle shrinks" is **withdrawn** — terminal spin is
   independent of `Izz` (note 01 §6), so that scaling does not follow.
6. **Per-cell probability with exact bounds against a preregistered criterion.**
   The nearest work labels states binary safe/unsafe (Sun & de Visser 2019) or
   attaches probabilities on a fixed-wing, non-failure envelope (Yin et al. 2019).

### Scope correction, 2026-09-24 (critique C01)

The open lane above is stated in terms of a **policy over actions**. Our own
study does not yet deliver one: its `mechanism` and `realloc_only` cases differ in
installed hardware, so it compares **design packages**, not actions a single
aircraft could choose between in flight (`design.md` §6b). The novelty wording
below therefore describes work that is **specified but not yet performed**, and
must not be cited as a result of the current sweep. A runtime-policy claim
requires one fixed configuration with `A(c)` executable on it.

### The wording that survives

> We are not aware of published work that estimates, **per post-failure state
> cell**, P(survivable landing) with **exact binomial bounds** against a
> **preregistered** survivability criterion, and uses it to select among distinct
> recovery *actions*. The closest prior work is Sun & de Visser (2019)
> (Monte-Carlo quadrotor safe envelope; binary labels, nominal conditions), Yin
> et al. (2019) (probabilistic envelope, fixed-wing, not failure-conditioned),
> and Sun et al. (2020) (post-rotor-failure recovery validated by Monte Carlo,
> no set estimate with boundary uncertainty).

Checkable, and it survives a reviewer finding one more paper.

## 3. Contested gap — cite, don't collide

**Siotia, Shankar, Nair & Nair (2026)**, *Enhancing UAV survivability through
real-time stall detection and parachute assisted recovery*, Scientific Reports
16:18189, [10.1038/s41598-026-47045-0](https://doi.org/10.1038/s41598-026-47045-0).

Their published abstract asserts the field lacks "an integrated framework that
explicitly detects unrecoverable loss-of-control states and dynamically
transitions between active stabilization and passive descent using
**altitude-aware decision logic**." That is adjacent to — arguably overlapping —
our positioning.

**How we differ, and it must be stated this sharply:**

| | Siotia et al. (2026) | This repo |
| --- | --- | --- |
| Trigger | stall detection → deployment **threshold** | ranking over a gridded post-failure state (a *policy* is the stated goal, **not yet delivered** — see Status row) |
| State | altitude | (h, v_z, tumble rate, **detection delay**) × failure class |
| Status | published result | **package comparison performed; runtime policy specified but NOT performed** (§ scope correction) |
| Actions | stabilise **or** deploy | reallocation / mechanism / descent device — compared as **whole aircraft configurations**, not as choices one aircraft can make |
| Output | a decision rule | **P(survivable landing) per cell with exact bounds** |
| Failure mode | stall / loss of control, unspecified cause | **specified propulsion-failure classes** |
| Validation | HIL + simulation, 2 kg, no free-flight drops | simulation on EST inputs, sub-250 g, preregistered |

Our differentiator is **not** "altitude-aware". It is *a survivability estimate
per failure class over a post-failure state grid that includes detection delay,
with preregistered criteria and exact interval arithmetic.*

## 4. Gaps in the literature we could fill cheaply

These are real absences, verified, and within reach of this project:

1. **No dimensional prescription for weighting force against moment residuals in
   multirotor allocation.** Normalising to reference scales and reporting the
   effect would be a small, citable contribution (note 02 §3).
2. **~~No detection-latency distribution.~~ WITHDRAWN 2026-09-24 (critique C02).**
   Strack van Schijndel et al. (2021) report 95 % bounds of **[28, 132] ms** with
   box plots over 26 real propeller ejections. What remains open is narrower:
   delay as a function of the *failure condition* (rotor index, thrust level,
   degraded vs sudden-total loss) — their fault is idealised as "sudden and
   total". Our use of delay as a **state coordinate of the recovery problem** is
   a different construct from a detector's achieved latency, and should be
   described that way rather than as a gap in the literature.
3. **No quantitative recirculation correction for a small restrained multirotor
   bench test** — NASA Ames explicitly leaves it unquantified. A height/wall
   sweep at fixed commanded RPM would close it (note 06 §4).
4. **No crashworthiness / survivable-landing drop standard for small
   multirotors.** NIST's sUAS methods cover proficiency, not survivability; ASTM
   F3389/F3322 test the human side. ASSURE A4 flags the adjacent gap ("blade
   guard standards exist for consumer grade fans but not for flight worthy
   stands"). A 27.725-structured drop test on our own vehicle is a
   one-afternoon experiment that converts our criterion from assumed to measured.
5. **No canopy-sizing or inflation study for sub-250 g parachutes** — and a mass
   budget argument suggests there may be no viable product to study.

## 5. What this means for the research plan

- **Study A/B keeps its question** but must narrow its novelty wording (§2) and
  add the related-work anchors (§1 rows 5, 9, 13).
- **Study A2's "spin-locked controller" is adoption, not invention** — cite
  Mueller & D'Andrea and the patent.
- **Study C's drop test becomes the single highest-value experiment in the
  portfolio**, because it converts the landing criterion (gap 4) from an analogy
  into a measurement — and no one else has published one.
- **The paired-comparison fix (note 05 §3) is a correctness prerequisite** for
  any future claim about mechanism vs reallocation.

## 6. Warning versus physics baseline

The [full-text comparison](notes/07-loss-of-control-prediction.md) replaces the
abstract-only assessment. It holds the source findings, qualifications and M2
options in one place. The current testable contrast is incremental warning
value against matched physics and simple signal baselines for independently
labeled recovery outcomes. Command saturation and calibrated thrust margin
remain separate quantities. Field-wide novelty and a likely null result are
unestablished; M2–M4 remain owner decisions.
