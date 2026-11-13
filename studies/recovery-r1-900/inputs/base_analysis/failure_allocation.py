#!/usr/bin/env python3
"""Motor-level control allocation under propulsion failures (Study A, DR-SS-01).

The mixer model in ``sim_release_recovery`` bounds roll/pitch torque by a scalar
capability formula that assumes all four motors are healthy. This module replaces
that scalar with the actual actuator map so *failure classes* become representable:
each motor's thrust is a decision variable in ``[0, cap]``, failed motors are forced
to zero, and the partial-authority class caps every motor below its healthy limit.

Geometry (X configuration, top view, body axes x forward / y left):

    m2 (-a, +a, CW)      m1 (+a, +a, CCW)
    m3 (-a, -a, CCW)     m4 (+a, -a, CW)

with ``a = arm / sqrt(2)``. The wrench map is ``w = B f`` with
``w = (T, tau_x, tau_y, tau_z)``:

    T     = f1 + f2 + f3 + f4
    tau_x = a (f1 + f2 - f3 - f4)
    tau_y = a (-f1 + f2 + f3 - f4)
    tau_z = kappa (f1 - f2 + f3 - f4)

``kappa`` (drag-torque per unit thrust) is derived from the same yaw-torque bound the
mixer model uses: full differential thrust on one spin pair produces the placeholder
yaw limit, so ``kappa = yaw_torque_n_m / (2 f_max)``.

Allocation is REDUCED-ATTITUDE by design: the commanded wrench is ``(T, tau_x,
tau_y)`` only. After the loss of a rotor the drag-torque budget cannot balance yaw
(the vehicle spins about body z — the established rotor-out flight regime), so
spending clipped motor authority on a hopeless yaw command would misallocate the
little control that remains. The achieved yaw torque (including the spin-direction
imbalance that drives the post-failure spin) is still computed and fed to the
dynamics, so the spin and its gyroscopic coupling are simulated, not ignored.

Allocation is trim-anchored with direction-preserving desaturation (collective on
the zero-torque trim direction; torque increment solved at invariant collective and
scaled — never bent — into the per-motor box). The first committed version used a
single-pass pseudo-inverse + clip, which distorts both the torque axis and the
collective under saturation; the revision and its effect on Study A results are
recorded in ``docs/specs/survivable-set/design-a2.md``.

Analytic anchors reproduced exactly by the map (tested in
``tests/test_failure_allocation.py``):

* one rotor out (m4): zero roll/pitch torque forces ``f2 = 0, f1 = f3`` — flight on
  the remaining diagonal pair, balanced collective ceiling ``2 f_max``, unbalanced
  yaw (spin).
* two opposite out (m2, m4): torque available only about the diagonal joining the
  survivors; spin, collective ceiling ``2 f_max``.
* two adjacent out (m3, m4): both survivors on one side — roll trim is impossible
  at any positive thrust. No hover exists; the class is expected to depend on the
  descent-device actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np


@dataclass(frozen=True)
class FailureCase:
    """One propulsion-failure class: dead motors and a per-motor authority cap."""

    name: str
    failed: tuple[int, ...] = ()      # 0-based motor indices forced to zero thrust
    authority_frac: float = 1.0       # per-motor cap as a fraction of the healthy cap


FAILURE_CLASSES: dict[str, FailureCase] = {
    "one_out": FailureCase("one_out", failed=(3,)),
    "two_adjacent": FailureCase("two_adjacent", failed=(2, 3)),
    "two_opposite": FailureCase("two_opposite", failed=(1, 3)),
    "partial_authority": FailureCase("partial_authority", authority_frac=0.6),
}

# X-configuration geometry: unit-arm positions and spin directions (CCW = +1).
_MOTOR_XY = np.array([[+1.0, +1.0], [-1.0, +1.0], [-1.0, -1.0], [+1.0, -1.0]])
_SPIN = np.array([+1.0, -1.0, +1.0, -1.0])


def healthy_wrench_map(arm_m: float, max_thrust_n: float,
                       yaw_torque_n_m: float) -> np.ndarray:
    """Full four-rotor wrench map ``w = B f``, w = (T, tau_x, tau_y, tau_z).

    Exposed so the pre-switch interval of an in-flight failure uses the SAME map
    as the post-switch dynamics rather than a second, drifting copy
    (DR-SS-SCENARIO-01 R05). ``MotorAllocation`` builds its own view from this.
    """
    a = arm_m / sqrt(2.0)
    kappa = yaw_torque_n_m / (2.0 * (max_thrust_n / 4.0))
    return np.vstack([
        np.ones(4),
        a * _MOTOR_XY[:, 1],
        -a * _MOTOR_XY[:, 0],
        kappa * _SPIN,
    ])


def solve_healthy_trim(arm_m: float, max_thrust_n: float, yaw_torque_n_m: float,
                       mass_kg: float, g: float,
                       cg_offset_m=(0.0, 0.0), torque_bias_n_m=(0.0, 0.0, 0.0),
                       cap_n: float | None = None):
    """Pre-fault four-rotor equilibrium (DR-SS-SCENARIO-01 R03).

    Solves, in the dynamics' own conventions, for per-rotor thrusts that hold
    hover with the modelled CG-offset moment and motor bias cancelled:

        sum(f)            = m g
        B_moment f + tau_cg(sum f) + bias = 0,   tau_cg = (cg_y T, -cg_x T, 0)

    which is linear in ``f``. Returns ``(f_trim, feasible)``. ``feasible`` is
    False when any rotor leaves ``[0, cap]`` — the caller must record
    ``trim_infeasible`` and must NOT silently substitute equal thrust or drop the
    sample (R03). With zero CG offset and zero bias this returns m*g/4 per rotor.
    """
    b = healthy_wrench_map(arm_m, max_thrust_n, yaw_torque_n_m)
    cg = np.asarray(cg_offset_m, float)
    bias = np.asarray(torque_bias_n_m, float)
    # moment rows plus the CG term, which is itself proportional to total thrust
    a_moment = b[1:4, :] + np.outer(np.array([cg[1], -cg[0], 0.0]), np.ones(4))
    a_full = np.vstack([np.ones(4), a_moment])
    rhs = np.array([mass_kg * g, -bias[0], -bias[1], -bias[2]])
    f_trim, *_ = np.linalg.lstsq(a_full, rhs, rcond=None)
    cap = cap_n if cap_n is not None else max_thrust_n / 4.0
    feasible = bool(np.all(f_trim >= -1e-9) and np.all(f_trim <= cap + 1e-9)
                    and np.allclose(a_full @ f_trim, rhs, atol=1e-6))
    return f_trim, feasible


class MotorAllocation:
    """Wrench allocation onto the healthy motors of one failure case.

    Build from mixer-mode parameters (``with_mixer`` — ``arm_m`` and
    ``yaw_torque_n_m`` set); ``apply`` replaces the scalar mixer clip inside
    ``simulate``.
    """

    def __init__(self, case: FailureCase, arm_m: float, max_thrust_n: float,
                 yaw_torque_n_m: float):
        a = arm_m / sqrt(2.0)
        f_max = max_thrust_n / 4.0
        kappa = yaw_torque_n_m / (2.0 * f_max)
        b_full = np.vstack([
            np.ones(4),
            a * _MOTOR_XY[:, 1],
            -a * _MOTOR_XY[:, 0],
            kappa * _SPIN,
        ])
        self.case = case
        self.healthy = tuple(i for i in range(4) if i not in case.failed)
        if not self.healthy:
            raise ValueError("all motors failed: no allocation exists")
        self._b = b_full[:, self.healthy]
        n = len(self.healthy)
        # constraint matrix [tau_x row; tau_y row; collective row]: used for the
        # zero-torque trim direction and for collective-invariant torque increments
        self._a = np.vstack([self._b[1:3, :], np.ones(n)])
        # trim direction u: least-squares solution of (tau=0, collective=1). Exact
        # where a trim exists (one_out: the diagonal pair; nominal: even split);
        # the best compromise where none does (two_adjacent).
        self._u, *_ = np.linalg.lstsq(self._a, np.array([0.0, 0.0, 1.0]), rcond=None)

    def max_collective(self, max_thrust_avail_n: float) -> float:
        """Balanced (zero roll/pitch torque) collective ceiling of the survivors.

        This is the hover-relevant ceiling: one motor out caps at 2 f_max (the
        remaining diagonal pair), not 3 f_max — thrust from the odd motor cannot be
        used without unbalancing the vehicle.
        """
        cap = self.case.authority_frac * max_thrust_avail_n / 4.0
        return cap / float(np.max(self._u))

    # weight on the torque rows relative to collective in the saturated re-solve:
    # when the box binds, attitude authority is worth more than climb thrust
    TORQUE_PRIORITY = 10.0

    def apply(self, torque_cmd: np.ndarray, thrust_cmd: float,
              max_thrust_avail_n: float) -> tuple[np.ndarray, float]:
        """Allocate (T, tau_x, tau_y) onto the healthy motors; return achieved wrench.

        Cascaded allocation: an exact/least-squares joint solve first (identical to
        the commanded wrench whenever it is feasible), then — if any motor
        saturates — the saturated motors are pinned at their bounds and the free
        ones re-solved with torque-priority weighting, so the attitude loop keeps
        the best achievable moment instead of an arbitrarily distorted one. Yaw
        command is dropped (reduced-attitude allocation, see module docstring); the
        achieved yaw torque of the final thrust pattern is returned so the dynamics
        integrate the post-failure spin.
        """
        cap = self.case.authority_frac * max_thrust_avail_n / 4.0
        a3 = self._b[:3, :]
        target = np.array([max(thrust_cmd, 0.0), torque_cmd[0], torque_cmd[1]])
        n = a3.shape[1]
        f = np.zeros(n)
        free = np.ones(n, dtype=bool)
        weights = np.array([1.0, self.TORQUE_PRIORITY, self.TORQUE_PRIORITY])
        for _ in range(2):
            residual = target - a3[:, ~free] @ f[~free]
            sol, *_ = np.linalg.lstsq(weights[:, None] * a3[:, free],
                                      weights * residual, rcond=None)
            f[free] = sol
            saturated = free & ((f < 0.0) | (f > cap))
            f = np.clip(f, 0.0, cap)
            if not saturated.any():
                break
            free = free & ~saturated
            if not free.any():
                break
        w = self._b @ f
        return np.array([w[1], w[2], w[3]]), float(w[0])
