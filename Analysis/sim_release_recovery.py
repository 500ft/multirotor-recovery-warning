#!/usr/bin/env python3
"""Closed-loop 6-DoF release-to-stabilization simulation (Lane A deliverable).

Unlike ``recovery.py`` — which is a conservative *algebraic* altitude-loss envelope — this
module is an actual time-domain rigid-body flight simulation: full quaternion attitude
dynamics (reusing the ``rigid_body`` kernel's conventions) plus translational dynamics with
attitude-coupled thrust, driven by a saturated stabilization controller. It demonstrates the
guarded micro-UAV being released with an initial tumble + tilt, detecting the release after a
sensing/actuation latency, arresting the tumble, righting itself, and recovering to hover —
the maneuver the whole project is about.

Frames: world z is up; body z is the thrust axis. Quaternion ``q = (w, x, y, z)`` maps body→world.
All actuation respects the locked-BOM limits (max control torque, max collective thrust).
Parameters are taken from ``recovery.py``'s characterized cases so the two analyses agree.

The controller acts on MEASURED state: the body-rate measurement saturates at the BOM gyro
range (``gyro_limit_rad_s`` — a rate the sensor cannot report cannot be controlled against),
and an optional :class:`Imperfections` bundle injects the dispersions the validation gates
require (CG offset, motor-to-motor thrust mismatch, gyro/attitude measurement noise, battery
sag). Truth dynamics always integrate the true state.

Two authority models are supported:

* **Placeholder (default)**: independent per-axis torque clip at the BOM placeholder
  ``max_torque_n_m`` (EST-REC-007) and an independent collective-thrust clip. Simple, but
  optimistic at full collective (no headroom left for differential torque in reality) and
  ~10x pessimistic at mid-collective.
* **Mixer (:func:`with_mixer`)**: roll/pitch torque is bounded by what a 4-motor X mixer
  can actually produce at the commanded collective — per-motor thrust in ``[0, T_max/4]``,
  differential headroom ``d_max = min(T/4, T_max/4 - T/4)``, giving
  ``tau_rp(T) = 2*sqrt(2)*arm*d_max`` (zero at both zero and full collective). Yaw keeps
  the small placeholder bound (drag-generated, genuinely weak). While the >78 deg thrust
  cut is active, the mixer holds a quarter-collective **control-authority floor** — motors
  keep spinning to produce differential torque, the physical reason a real quad can right
  itself while inverted. The arm length is an ASSUMED build parameter until CAD/bench.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, cos, sin, sqrt

import numpy as np

G = 9.81
RHO_AIR = 1.225

# DR-SS-SCENARIO-01 arms. "release_startup" is the frozen legacy behaviour.
SCENARIOS = ("release_startup", "in_flight_hold_matched", "in_flight_hold_immediate")


@dataclass(frozen=True)
class DroneParams:
    """Locked-BOM physical + actuation limits (see recovery.RecoveryCase)."""

    mass_kg: float
    inertia_lateral_kg_m2: float           # roll/pitch (the recovery-relevant axes)
    inertia_yaw_factor: float = 1.6        # ASSUMED Izz / Ixx for a small quad
    max_torque_n_m: float = 0.004          # per-axis control-torque saturation
    max_thrust_n: float = 4.2              # collective-thrust saturation
    drag_coefficient: float = 1.0
    projected_area_m2: float = 0.012
    detection_latency_s: float = 0.05
    motor_start_latency_s: float = 0.06
    gyro_limit_rad_s: float = 2000.0 * np.pi / 180.0
    available_height_m: float = 3.0
    arm_m: float | None = None             # motor arm; set via with_mixer() -> mixer authority
    yaw_torque_n_m: float | None = None    # separate yaw bound in mixer mode (drag-generated)
    # rotational yaw drag tau_z = -c*w_z*|w_z| (frame/prop aero). Default 0 preserves the
    # gated release-recovery behavior exactly; Study A2 sets an EST value so the rotor-out
    # drag-torque spin reaches a bounded terminal rate instead of growing without limit.
    yaw_drag_n_m_s2: float = 0.0

    @property
    def inertia(self) -> np.ndarray:
        i = self.inertia_lateral_kg_m2
        return np.array([i, i, i * self.inertia_yaw_factor])


def with_mixer(p: DroneParams, arm_m: float = 0.060) -> DroneParams:
    """Switch a parameter set to the physically-derived mixer authority model.

    ``arm_m`` is the motor-to-CG arm (ASSUMED 60 mm for the locked 2.0-2.3'' prop,
    sub-250g class until CAD fixes it). The per-axis command clip is opened up (the
    mixer clip in ``simulate`` becomes the binding roll/pitch limit) and the original
    placeholder torque bound is kept as the yaw limit, since yaw torque is
    drag-generated and genuinely small.
    """
    from dataclasses import replace
    return replace(p, arm_m=arm_m, yaw_torque_n_m=p.max_torque_n_m,
                   max_torque_n_m=1.0)


def mixer_torque_limit(thrust_n: float, max_thrust_n: float, arm_m: float) -> float:
    """Roll/pitch differential-torque capability of a 4-motor X mixer at a collective.

    Motors sit at (+-arm/sqrt(2), +-arm/sqrt(2)); per-motor thrust in [0, T_max/4].
    Raising one motor pair by d and lowering the other by d holds the collective and
    yields torque 2*sqrt(2)*arm*d with d_max = min(T/4, T_max/4 - T/4). Zero at both
    zero and full collective — the coupling the placeholder model ignored.
    """
    f_max = max_thrust_n / 4.0
    d_max = max(0.0, min(thrust_n / 4.0, f_max - thrust_n / 4.0))
    return 2.0 * sqrt(2.0) * arm_m * d_max


@dataclass(frozen=True)
class Imperfections:
    """Dispersions/imperfections applied to one run (validation-gate test cases).

    All default to "perfect", so ``simulate(...)`` without this argument is unchanged.
    Measurement noises are white, applied per integration step, seeded for repeatability.
    """

    cg_offset_m: tuple[float, float] = (0.0, 0.0)   # thrust-line offset (body x, y)
    thrust_scale: float = 1.0                       # battery-sag multiplier on max thrust
    torque_bias_n_m: tuple[float, float, float] = (0.0, 0.0, 0.0)  # motor mismatch
    gyro_noise_rad_s: float = 0.0                   # per-axis white rate-measurement noise
    tilt_noise_rad: float = 0.0                     # white attitude-estimate error magnitude
    seed: int = 0


# control gains (tuned so the torque-limited arrest saturates, then eases — see __main__)
KP_ATT, KD_ATT = 0.012, 0.0026
KP_ALT, KD_ALT = 2.2, 2.2
# integral attitude trim, mixer mode only: a constant CG-offset disturbance leaves a PD
# controller hovering at a steady tilt of tau_dist/KP_ATT (>25 deg at 2 mm offset) — the
# standard fix is integral action. Clamped hard (anti-windup) well below the hover-collective
# mixer capability so the trim can never consume the stabilization authority.
KI_ATT = 0.010
I_TORQUE_CLAMP = 0.020
# descent mode: brake (hold vertical speed) until the vehicle is upright-ish, then
# track the commanded touchdown rate — descending while righting wastes the height
# the arrest needs and arrives at the ground hot.
BRAKE_TILT_RAD = np.radians(25.0)
# mixer mode re-tune: the base PD gains were sized for the 0.004 N*m placeholder clip.
# With mixer-level authority (~0.05 N*m at hover) the same gains leave the loop too soft
# to out-torque a CG-offset disturbance at large tilt, so the attitude command is scaled
# up (P and D together, preserving damping character) before the mixer clip.
MIXER_ATT_GAIN_SCALE = 3.0


def quat_to_rotmat(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def quat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def axis_angle_quat(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, float)
    n = np.linalg.norm(axis)
    if n == 0:
        return np.array([1.0, 0.0, 0.0, 0.0])
    axis = axis / n
    return np.array([cos(angle / 2), *(axis * sin(angle / 2))])


def tilt_rotation_error(q: np.ndarray) -> np.ndarray:
    """Shortest thrust-axis correction in body coordinates, with magnitude in radians.

    At exactly inverted, every horizontal correction axis is equally short. Choose
    body x deterministically there; the resulting discontinuity is intentional.
    This is a simulation controller option, not a global stability guarantee.
    """
    R = quat_to_rotmat(q)
    target_body = R.T @ np.array([0.0, 0.0, 1.0])
    axis = np.array([-target_body[1], target_body[0], 0.0])
    sine = float(np.linalg.norm(axis))
    cosine = float(np.clip(target_body[2], -1.0, 1.0))
    if sine > 1e-12:
        return axis * (float(np.arctan2(sine, cosine)) / sine)
    return np.array([np.pi, 0.0, 0.0]) if cosine < 0.0 else np.zeros(3)


def _control(q, omega, pos, vel, p: DroneParams, descent_rate_m_s: float | None = None,
             *, attitude_controller: str = "legacy", inverted_axis=None):
    """Saturated attitude + altitude controller. Returns (torque_body[3], thrust_collective).

    With ``descent_rate_m_s`` set, the altitude hold is replaced by a vertical-rate
    reference of ``-descent_rate_m_s`` (controlled descent to touchdown, Study A).
    """
    R = quat_to_rotmat(q)
    body_up_world = R[:, 2]
    tilt = acos(np.clip(body_up_world[2], -1.0, 1.0))
    # attitude: drive body-up toward world-up; correcting rotation vector in the body frame
    e_world = np.cross(body_up_world, np.array([0.0, 0.0, 1.0]))
    e_body = R.T @ e_world
    if attitude_controller == "tilt_angle":
        e_body = (np.asarray(inverted_axis, float) * tilt
                  if inverted_axis is not None else tilt_rotation_error(q))
    elif attitude_controller != "legacy":
        raise ValueError(f"unknown attitude controller {attitude_controller!r}")
    torque = KP_ATT * e_body - KD_ATT * omega
    torque = np.clip(torque, -p.max_torque_n_m, p.max_torque_n_m)
    # altitude: tilt-compensated hold. Command the vertical force (gravity + PD recovery), then
    # divide by cos(tilt) so the body-up thrust still delivers it while righting; cut once past
    # ~78 deg (cos<0.2), where thrust can no longer help vertically and would only fight the
    # attitude loop. This is the standard release-recovery priority: limit the fall *while*
    # righting, instead of free-falling until upright.
    cos_tilt = R[2, 2]
    if cos_tilt > 0.2:
        if descent_rate_m_s is None:
            desired_fz = p.mass_kg * G - KP_ALT * pos[2] - KD_ALT * vel[2]
        else:
            # arrest-first: brake the fall while still righting (tilt large),
            # only then track the touchdown descent rate
            v_ref = -descent_rate_m_s if tilt < BRAKE_TILT_RAD else 0.0
            desired_fz = p.mass_kg * G + KD_ALT * (v_ref - vel[2])
        thrust = float(np.clip(desired_fz / cos_tilt, 0.0, p.max_thrust_n))
    else:
        thrust = 0.0
    return torque, thrust, tilt


def simulate(p: DroneParams, initial_rate_rad_s: float, initial_tilt_rad: float,
             *, tumble_axis=(1.0, 1.0, 0.0), tilt_axis=(0.0, 1.0, 0.0),
             dt: float = 5e-4, t_max: float = 6.0,
             imperfections: Imperfections | None = None,
             initial_vz_m_s: float = 0.0,
             descent_rate_m_s: float | None = None,
             motor_alloc=None,
             control_floor: bool = True,
             spin_aware: bool = False,
             scenario: str = "release_startup",
             trim_thrusts=None,
             attitude_controller: str = "legacy") -> dict:
    """Release the drone with an initial tumble + tilt and run closed-loop recovery.

    ``attitude_controller="tilt_angle"`` replaces the legacy sine-of-tilt error
    with a shortest rotation vector. Gains and actuator limits are unchanged.
    A body-x axis chosen at exact inversion is latched until five degrees clear.
    The default preserves all historical calculations.

    Motors are off for ``detection_latency + motor_start_latency`` (passive tumble + free
    fall), then the controller engages. The controller sees the MEASURED state: body rate
    clipped to the gyro range, plus (optional) measurement noise and actuation dispersions
    from ``imperfections``. Returns time-series arrays + recovery metrics.

    Study-A extensions (all default to the original release-recovery behavior):
    ``initial_vz_m_s`` sets the vertical speed at release (in-flight failure states);
    ``descent_rate_m_s`` switches the altitude hold to a controlled descent so every
    run terminates at touchdown and the impact state can be judged; ``motor_alloc``
    (a ``failure_allocation.MotorAllocation``, mixer-mode params required) replaces
    the scalar mixer clip with per-motor allocation under a failure class; and
    ``control_floor=False`` disables the quarter-collective inverted-authority floor —
    the guard-enabled mechanism behavior — to model the mechanism-less vehicle.
    ``scenario`` selects the pre-reconfiguration behaviour (DR-SS-SCENARIO-01):

    * ``"release_startup"`` (default, legacy): every rotor is off until
      ``detection_latency + motor_start_latency``. A release/startup transient.
    * ``"in_flight_hold_matched"``: failed rotors produce nothing from t=0 while
      healthy rotors HOLD their pre-fault trim thrust; recovery control still
      begins at ``detection_latency + motor_start_latency`` so the switch time
      matches the legacy arm.
    * ``"in_flight_hold_immediate"``: same held outputs, recovery control begins
      at ``detection_latency`` — healthy motors are already spinning, so the
      release spool-up dead time does not apply to them.

    The two in-flight arms require ``motor_alloc`` (for the failed indices) and
    ``trim_thrusts`` (the pre-fault four-rotor equilibrium from
    ``failure_allocation.solve_healthy_trim``). Force AND all three moments are
    derived from the realized rotor vector through the same wrench map the
    post-switch dynamics use — retaining 3/4 of collective while applying zero
    roll/pitch torque would not be rotor-loss physics.

    ``spin_aware=True`` (Study A2) adds gyroscopic feedforward in the tilt plane:
    the PD law alone ignores the precession torque ``w x Iw``, which grows with the
    rotor-out drag spin until it overwhelms the attitude authority; the feedforward
    cancels its roll/pitch component using the MEASURED rate and the modeled inertia
    (the same idealization the gravity compensation already makes).
    """
    if attitude_controller not in ("legacy", "tilt_angle"):
        raise ValueError(f"unknown attitude controller {attitude_controller!r}")
    imp = imperfections or Imperfections()
    rng = np.random.default_rng(imp.seed)
    cg = np.asarray(imp.cg_offset_m, float)
    torque_bias = np.asarray(imp.torque_bias_n_m, float)
    max_thrust_avail = p.max_thrust_n * imp.thrust_scale

    q = axis_angle_quat(np.asarray(tilt_axis, float), initial_tilt_rad)
    omega = initial_rate_rad_s * (np.asarray(tumble_axis, float)
                                  / np.linalg.norm(tumble_axis))
    pos = np.zeros(3)
    vel = np.array([0.0, 0.0, initial_vz_m_s])
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; expected one of {SCENARIOS}")
    in_flight = scenario != "release_startup"
    if in_flight and (motor_alloc is None or trim_thrusts is None):
        raise ValueError("in-flight scenarios need motor_alloc and trim_thrusts")
    # when fault-aware control takes over. The legacy arm and the matched arm
    # share a switch time; the immediate arm drops the release spool-up dead
    # time, which does not apply to motors that are already running (R07).
    if scenario == "in_flight_hold_immediate":
        passive_time = p.detection_latency_s
    else:
        passive_time = p.detection_latency_s + p.motor_start_latency_s
    held_wrench = None
    if in_flight:
        from Analysis.failure_allocation import healthy_wrench_map
        b_full = healthy_wrench_map(p.arm_m, p.max_thrust_n, p.yaw_torque_n_m)
        f_held = np.asarray(trim_thrusts, float).copy()
        f_held[list(motor_alloc.case.failed)] = 0.0      # failed outputs vanish
        # partial_authority is a per-rotor CAP, not a multiplicative loss of
        # effectiveness (DR-SS-SCENARIO-01 R02): a held command below the reduced
        # cap is unaffected. Multiplying here would silently turn the class into
        # an effectiveness fault and change what the study measures.
        _cap = motor_alloc.case.authority_frac * p.max_thrust_n / 4.0
        f_held = np.minimum(f_held, _cap)
        held_wrench = b_full @ f_held                    # (T, tau_x, tau_y, tau_z)
    t_switch_realized = None
    I = p.inertia
    e_int = np.zeros(3)                    # integral attitude trim state (mixer mode)
    inverted_axis = None                  # choose once at the antipodal state

    T = int(t_max / dt)
    log = {k: np.empty(T) for k in ("t", "tilt", "omega_mag", "z", "vz", "thrust")}
    recovered_at = None
    settled_steps = 0

    for k in range(T):
        t = k * dt
        R = quat_to_rotmat(q)
        tilt = acos(np.clip(R[2, 2], -1.0, 1.0))
        motors_on = t >= passive_time
        if motors_on and t_switch_realized is None:
            t_switch_realized = t
        if motors_on:
            # measured state: gyro clips at its range; optional white noise on the rate
            # and on the attitude estimate (small random rotation of q).
            omega_meas = omega
            if imp.gyro_noise_rad_s > 0.0:
                omega_meas = omega_meas + rng.normal(0.0, imp.gyro_noise_rad_s, 3)
            omega_meas = np.clip(omega_meas, -p.gyro_limit_rad_s, p.gyro_limit_rad_s)
            q_meas = q
            if imp.tilt_noise_rad > 0.0:
                axis = rng.normal(size=3)
                q_meas = quat_mul(q, axis_angle_quat(axis, rng.normal(0.0, imp.tilt_noise_rad)))
                q_meas = q_meas / np.linalg.norm(q_meas)
            if attitude_controller == "tilt_angle":
                measured_cosine = quat_to_rotmat(q_meas)[2, 2]
                # Exactly inverted has no unique correction axis. Keep a chosen
                # body-x axis until five degrees clear; repeated normalization
                # of roundoff-sized cross products would change the choice.
                if inverted_axis is None and measured_cosine <= -1.0 + 1e-12:
                    inverted_axis = np.array([1.0, 0.0, 0.0])
                elif inverted_axis is not None and measured_cosine > -cos(np.radians(5.0)):
                    inverted_axis = None
            torque, thrust, _ = _control(q_meas, omega_meas, pos, vel, p,
                                         descent_rate_m_s=descent_rate_m_s,
                                         attitude_controller=attitude_controller,
                                         inverted_axis=inverted_axis)
            thrust = min(thrust, max_thrust_avail)          # battery sag caps thrust
            if p.arm_m is not None:
                # mixer authority: keep a quarter-collective control floor while the
                # >78deg thrust cut is active (motors spin for differential torque),
                # then bound roll/pitch by the mixer capability at this collective.
                # The floor is the guard-enabled mechanism behavior; Study A's
                # mechanism-less action disables it (control_floor=False).
                max_coll = (motor_alloc.max_collective(max_thrust_avail)
                            if motor_alloc is not None else max_thrust_avail)
                if thrust <= 0.0:
                    floor = (motor_alloc.max_collective(p.max_thrust_n)
                             if motor_alloc is not None else p.max_thrust_n)
                    thrust = min(0.25 * floor, max_coll) if control_floor else 0.0
                # attitude-priority desaturation ("airmode"): never command full
                # collective — cap at 75% so differential headroom cannot vanish
                # (tau_avail(T_max) = 0). Costs peak climb thrust, preserves control.
                # In allocation mode the ceiling is already the BALANCED collective
                # (much lower than 4 f_max under failures) and the allocator's
                # direction-preserving desaturation manages the torque trade, so a
                # smaller reserve suffices — 0.75 there would starve the vertical
                # axis below hover thrust for one_out.
                thrust = min(thrust, (0.9 if motor_alloc is not None else 0.75)
                             * max_coll)
                torque = torque * MIXER_ATT_GAIN_SCALE
                # integral trim of constant disturbances (CG offset, motor bias):
                # integrate the attitude error only when upright-ish (tilt < 45 deg,
                # past the arrest phase) and clamp the trim torque (anti-windup).
                R_m = quat_to_rotmat(q_meas)
                if R_m[2, 2] > 0.7071:
                    e_b = R_m.T @ np.cross(R_m[:, 2], np.array([0.0, 0.0, 1.0]))
                    e_int = e_int + e_b * dt
                trim = np.clip(KI_ATT * e_int, -I_TORQUE_CLAMP, I_TORQUE_CLAMP)
                torque = torque + trim
                if spin_aware:
                    # cancel the measured precession torque in the tilt plane (yaw
                    # is uncontrollable under rotor loss and is left to the drag)
                    ff = np.cross(omega_meas, I * omega_meas)
                    torque[:2] = torque[:2] + ff[:2]
                if motor_alloc is not None:
                    torque, thrust = motor_alloc.apply(torque, thrust, max_thrust_avail)
                else:
                    tau_rp = mixer_torque_limit(thrust, max_thrust_avail, p.arm_m)
                    torque[:2] = np.clip(torque[:2], -tau_rp, tau_rp)
                    yaw_lim = p.yaw_torque_n_m if p.yaw_torque_n_m is not None else tau_rp
                    torque[2] = np.clip(torque[2], -yaw_lim, yaw_lim)
            # actuation imperfections: thrust line offset from CG -> disturbance torque
            # tau = r_cg x F_body (F_body = [0,0,thrust]); plus motor-mismatch bias.
            torque = torque + np.array([cg[1] * thrust, -cg[0] * thrust, 0.0]) + torque_bias
        elif in_flight:
            # healthy rotors hold their pre-fault commands; the failed ones are
            # already zero. All three moments come from the realized vector.
            thrust = float(held_wrench[0])
            torque = held_wrench[1:4].copy()
            torque = torque + np.array([cg[1] * thrust, -cg[0] * thrust, 0.0]) \
                + torque_bias
        else:
            torque, thrust = np.zeros(3), 0.0

        # translational dynamics (world frame): thrust along body-up, gravity, quadratic drag
        F = R @ np.array([0.0, 0.0, thrust])
        F[2] -= p.mass_kg * G
        speed = np.linalg.norm(vel)
        if speed > 0:
            F -= 0.5 * RHO_AIR * p.drag_coefficient * p.projected_area_m2 * speed * vel
        acc = F / p.mass_kg

        # attitude dynamics (Euler equations with gyroscopic coupling) + quaternion integration
        gyro = np.cross(omega, I * omega)
        drag_z = -p.yaw_drag_n_m_s2 * omega[2] * abs(omega[2])
        alpha = (torque - gyro + np.array([0.0, 0.0, drag_z])) / I

        log["t"][k] = t; log["tilt"][k] = tilt; log["omega_mag"][k] = np.linalg.norm(omega)
        log["z"][k] = pos[2]; log["vz"][k] = vel[2]; log["thrust"][k] = thrust

        vel = vel + acc * dt
        pos = pos + vel * dt
        omega = omega + alpha * dt
        q = q + 0.5 * quat_mul(q, np.array([0.0, *omega])) * dt
        q = q / np.linalg.norm(q)

        if pos[2] <= -p.available_height_m:        # hit the ground while recovering
            for key in log:
                log[key] = log[key][:k + 1]
            return _result(p, log, success=False, crashed=True,
                           recovery_time=None, initial_rate_rad_s=initial_rate_rad_s,
                           scenario=scenario, t_switch_requested=passive_time,
                           t_switch_realized=t_switch_realized)

        # stabilized = upright, low rate, near-zero vertical speed, after motors engaged
        if motors_on and tilt < np.radians(5) and np.linalg.norm(omega) < 0.3 and abs(vel[2]) < 0.2:
            settled_steps += 1
            if settled_steps * dt >= 0.25 and recovered_at is None:   # held for 0.25 s
                recovered_at = t - passive_time
        else:
            settled_steps = 0

    for key in log:
        log[key] = log[key][:T]
    return _result(p, log, success=recovered_at is not None, crashed=False,
                   recovery_time=recovered_at, initial_rate_rad_s=initial_rate_rad_s,
                   scenario=scenario, t_switch_requested=passive_time,
                   t_switch_realized=t_switch_realized)


def _result(p, log, *, success, crashed, recovery_time, initial_rate_rad_s,
            scenario="release_startup", t_switch_requested=None,
            t_switch_realized=None):
    max_descent = float(-np.min(log["z"])) if log["z"].size else float("nan")
    return {
        "scenario": scenario,
        "t_switch_requested_s": t_switch_requested,
        "t_switch_realized_s": t_switch_realized,
        "initial_rate_rad_s": initial_rate_rad_s,
        "success": bool(success),
        "crashed": bool(crashed),
        "recovery_time_s": recovery_time,
        "max_descent_m": max_descent,
        "available_height_m": p.available_height_m,
        "final_tilt_deg": float(np.degrees(log["tilt"][-1])) if log["tilt"].size else float("nan"),
        "peak_thrust_n": float(np.max(log["thrust"])) if log["thrust"].size else 0.0,
        "log": log,
    }


def max_recoverable_rate(p: DroneParams, initial_tilt_rad: float,
                         hi: float | None = None, step: float = 0.5,
                         with_edge: bool = False):
    """Largest initial tumble rate that still recovers, scanning up to the first failure.

    Scanning to the *first* failure (rather than bisecting) defines the usable envelope edge
    robustly even if recovery is not perfectly monotonic in rate near the boundary.

    The scan is capped at the BOM gyro range: a release faster than the gyro can measure
    cannot be claimed as recoverable, whatever the dynamics say. With ``with_edge=True``
    returns ``(rate, edge)`` where ``edge`` is ``"failure"`` (a real dynamic boundary was
    found) or ``"gyro_limit"`` (recovery never failed up to the measurement cap — the
    envelope is sensor-limited, not authority-limited).
    """
    if hi is None:
        hi = p.gyro_limit_rad_s
    hi = min(hi, p.gyro_limit_rad_s)
    last_ok = 0.0
    rate = 0.0
    edge = "gyro_limit"
    while rate <= hi:
        if simulate(p, rate, initial_tilt_rad)["success"]:
            last_ok = rate
            rate += step
        else:
            edge = "failure"
            break
    return (last_ok, edge) if with_edge else last_ok


# locked-BOM cases, mirroring recovery.default_cases() so the two analyses agree
def nominal_params() -> DroneParams:
    return DroneParams(mass_kg=0.12976, inertia_lateral_kg_m2=0.00035,
                       max_torque_n_m=0.0040, max_thrust_n=4.2,
                       drag_coefficient=1.0, projected_area_m2=0.012,
                       detection_latency_s=0.05, motor_start_latency_s=0.06)


def best_params() -> DroneParams:
    return DroneParams(mass_kg=0.11796, inertia_lateral_kg_m2=0.00020,
                       max_torque_n_m=0.0060, max_thrust_n=5.0,
                       drag_coefficient=1.3, projected_area_m2=0.016,
                       detection_latency_s=0.02, motor_start_latency_s=0.03)


def worst_params() -> DroneParams:
    return DroneParams(mass_kg=0.155, inertia_lateral_kg_m2=0.00055,
                       max_torque_n_m=0.0025, max_thrust_n=3.5,
                       drag_coefficient=0.8, projected_area_m2=0.008,
                       detection_latency_s=0.10, motor_start_latency_s=0.12)


if __name__ == "__main__":
    for name, p in [("nominal", nominal_params()), ("worst", worst_params())]:
        r = simulate(p, initial_rate_rad_s=5.0, initial_tilt_rad=np.radians(60))
        mr = max_recoverable_rate(p, np.radians(60))
        print(f"{name}: success={r['success']} recovery_time={r['recovery_time_s']} "
              f"max_descent={r['max_descent_m']:.2f}/{p.available_height_m} m "
              f"peak_thrust={r['peak_thrust_n']:.2f}/{p.max_thrust_n} N "
              f"max_recoverable_rate={mr:.1f} rad/s ({np.degrees(mr):.0f} deg/s)")
