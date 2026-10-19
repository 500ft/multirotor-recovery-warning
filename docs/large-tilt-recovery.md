# Large-tilt recovery development study

The optional `tilt_angle` controller corrects the historical controller's vanishing
attitude command near inversion. The executed comparison and tested release
heights are in [results.json](../Data/large-tilt-recovery/results.json). The
[protocol](../Data/large-tilt-recovery/protocol.json) defines the development cases,
settling rule, integration steps and illustrative clearance.

## Controller change

The historical law uses the cross product of the body thrust direction with
world up. Its magnitude is the sine of tilt. It approaches zero both upright
and inverted. Rate damping alone cannot deliberately choose a righting direction
from a stationary inverted state.

The new option uses the shortest thrust-axis rotation vector instead. Its
magnitude is the tilt angle, preserving the small-angle gain while maintaining
an attitude demand near inversion. At exactly inverted, there is no unique
shortest rotation axis. The implementation chooses body x deterministically and latches that axis
until it is clear of inversion by the amount recorded in the protocol. This
prevents roundoff-sized cross products from repeatedly changing the chosen axis.
That discontinuous convention is part of the implementation, not a global
stability proof. Torque clipping, collective control, gains, physical parameters
and startup delays are unchanged. `legacy` remains the default.

This uses an established reduced-attitude idea. [Brescianini and D'Andrea,
Tilt-Prioritized Quadrocopter Attitude Control](https://brescianini.info/wp-content/uploads/publications/breTCST18.pdf)
describe thrust-direction priority and the importance of allocation under
saturation. The implementation here is a simple development option in the retained
simulator; it is not a reproduction of their complete controller or a new method.

## Height comparison

The video cases begin at the tilt recorded in the protocol. The largest logged
angle in its best-tier high-rate trace is also used as a *new initial angle* in
this study. A reached angle during a trajectory and an initial attitude are
separate conditions. Exactly inverted cases test the correction's limiting case.

A large virtual ground clearance first lets each trajectory evolve for the
specified observation window. Altitude is displacement from the release point,
and the controller's target remains the release altitude. The available height
only moves the collision plane; increasing it cannot improve the attitude law.
For cases that settle, the runner rounds the observed descent plus a declared
illustrative clearance upward to the declared height grid. It then verifies a
separate run with that ground plane. Failure to settle within the observation
window is recorded without inferring that no possible height could work.

The runner checks the settling predicate independently on simultaneous logged
states. Historical simulator bookkeeping checks some quantities on opposite
sides of an integration update; its success flag is retained, and both checks
must pass for a tested release height. Each comparison is repeated at half the
integration step. These are development cases, not a reserved statistical test.

The first implementation normalized the cross product afresh at every update.
Its stationary inverted pessimistic case recovered at both primary timesteps,
but descent changed substantially under refinement. The earlier
[comparison](../Data/large-tilt-recovery/before-axis-latch-results.json),
[extra refinement](../Data/large-tilt-recovery/before-axis-latch-refinement.json)
and [source snapshot](../Data/large-tilt-recovery/before-axis-latch-model.py)
retain that failed numerical check. The axis latch addresses that mechanism;
the current result is a separately executed rerun.

## Limits

All comparisons use the historical estimated plant with independently clipped
thrust and torque. That model can exert righting torque while collective thrust
is zero; real rotor commands couple these quantities. The present changes do
not establish actuator feasibility, Crazyflie performance or a physical release
height. Motor dynamics, battery behavior, estimator errors, horizontal speed,
obstacle clearance and vehicle dimensions are not qualified by these results.
The illustrative clearance is not an operational safety margin. The physical
measurement and trial gates in [ROADMAP.md](../ROADMAP.md) remain open.

## Reproduce

```sh
python -m unittest Analysis.tests.test_large_tilt_recovery -v
python -m Analysis.run_large_tilt_recovery
python -m Analysis.plot_large_tilt_recovery
```

The runner writes the protocol before execution, hashes the model, retains both
controllers and all cases, and saves sampled plotting traces separately from
full-resolution metrics. Original results are not overwritten.
