"""Executed illustration with four feasible motor forces and rotor-speed lag.

The display labels select historical parameter cases with optional rate filtering.
Controller gains are retained. This separate run
does not replace the historical envelope or qualify a physical aircraft.
"""
from pathlib import Path
import json
import numpy as np
from Analysis import sim_release_recovery as base
from Analysis.failure_allocation import healthy_wrench_map

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data/recovery-video"
CASES = {"best": base.nominal_params, "nominal": base.worst_params,
         "worst": base.worst_params}


def case_settings(key, cfg):
    """Apply the documented display-case assumptions without altering the legacy model."""
    overrides = cfg.get("case_modifiers", {}).get(key, {})
    lag = overrides.get("motor_lag_multiplier", 1.0)
    return {**cfg, "gyro_filter_tau_s": overrides.get("gyro_filter_tau_s", 0.0),
            "motor_tau_up_s": cfg["motor_tau_up_s"] * lag,
            "motor_tau_down_s": cfg["motor_tau_down_s"] * lag}


def allocate(thrust, torque, inverse, cap):
    """Preserve torque direction; shift collective into the feasible motor box.

    A zero-sum differential force produces the requested moment. If its span
    exceeds a rotor's available force, scale the entire differential uniformly.
    Then choose the nearest feasible collective. Every commanded force is real.
    """
    delta = inverse @ np.r_[0.0, torque]
    span = np.ptp(delta)
    if span > cap:
        delta *= cap / span
    collective_per_rotor = np.clip(thrust / 4, -delta.min(), cap - delta.max())
    return np.clip(collective_per_rotor + delta, 0, cap)


def motor_step(speed, target, dt, tau_up, tau_down):
    """Exact first-order normalized rotor-speed step; force is speed squared."""
    tau = np.where(target > speed, tau_up, tau_down)
    return target + (speed - target) * np.exp(-dt / tau)


def simulate(p, cfg, *, dt=None, lag_multiplier=1.0):
    dt = cfg["dt_s"] if dt is None else dt
    steps = round(cfg["duration_s"] / dt)
    matrix = healthy_wrench_map(cfg["arm_m"], p.max_thrust_n, p.max_torque_n_m)
    inverse = np.linalg.inv(matrix)
    cap = p.max_thrust_n / 4
    q = base.axis_angle_quat(np.array([0., 1., 0.]), np.radians(cfg["initial_tilt_deg"]))
    omega = np.array([1., 1., 0.]) / np.sqrt(2) * cfg["initial_rate_rad_s"]
    pos = np.zeros(3); vel = np.zeros(3); speed = np.zeros(4)
    phase = np.zeros(4)
    omega_feedback = omega.copy()
    gyro_tau = cfg.get("gyro_filter_tau_s", 0.0)
    delay = p.detection_latency_s + p.motor_start_latency_s
    log = {key: [] for key in ["t", "q", "pos", "vel", "omega", "tilt",
                              "motor_force", "motor_command", "motor_speed", "phase", "omega_feedback"]}
    crashed = False
    for k in range(steps + 1):
        t = k * dt
        R = base.quat_to_rotmat(q)
        tilt = np.arccos(np.clip(R[2, 2], -1, 1))
        if t >= delay:
            torque, thrust, _ = base._control(q, np.clip(omega_feedback, -p.gyro_limit_rad_s,
                                                       p.gyro_limit_rad_s), pos, vel, p)
            command = allocate(thrust, torque, inverse, cap)
        else:
            command = np.zeros(4)
        force = cap * speed**2
        for key, value in [("t", t), ("q", q), ("pos", pos), ("vel", vel),
                           ("omega", omega), ("tilt", tilt), ("motor_force", force),
                           ("motor_command", command), ("motor_speed", speed), ("phase", phase),
                           ("omega_feedback", omega_feedback)]:
            log[key].append(np.array(value, copy=True))
        if pos[2] <= -p.available_height_m:
            crashed = True
            break
        if k == steps:
            break
        # A midpoint rotor state drives this integration interval. The recorded
        # force is the instantaneous start state; the update never jumps to demand.
        target = np.sqrt(command / cap)
        tau_up = cfg["motor_tau_up_s"] * lag_multiplier
        tau_down = cfg["motor_tau_down_s"] * lag_multiplier
        mid = motor_step(speed, target, dt / 2, tau_up, tau_down)
        thrust, *torque = matrix @ (cap * mid**2)
        drag = -.5 * base.RHO_AIR * p.drag_coefficient * p.projected_area_m2 * np.linalg.norm(vel) * vel
        acc = (R[:, 2] * thrust + drag) / p.mass_kg - np.array([0., 0., base.G])
        alpha = (np.asarray(torque) - np.cross(omega, p.inertia * omega)) / p.inertia
        pos = pos + vel * dt + .5 * acc * dt**2
        vel = vel + acc * dt
        q = q + .5 * base.quat_mul(q, np.r_[0., omega + .5 * alpha * dt]) * dt
        q /= np.linalg.norm(q)
        # First-order gyro filtering acts on the interval-start angular rate.
        # Zero time constant retains the original ideal-feedback path exactly.
        if gyro_tau > 0:
            omega_feedback = motor_step(omega_feedback, omega, dt, gyro_tau, gyro_tau)
        omega = omega + alpha * dt
        if gyro_tau == 0:
            omega_feedback = omega.copy()
        # Readable blade motion is a visual proxy for normalized speed, not RPM.
        phase = phase + 2 * np.pi * 5 * mid * dt
        speed = motor_step(speed, target, dt, tau_up, tau_down)
    return {k: np.asarray(v) for k, v in log.items()}, crashed


def metrics(a, crashed, cfg, p):
    dt = a["t"][1] - a["t"][0]
    count = round(.25 / dt)
    stable = ((a["t"] >= p.detection_latency_s + p.motor_start_latency_s)
              & (a["tilt"] < np.radians(5))
              & (np.linalg.norm(a["omega"], axis=1) < .3)
              & (np.abs(a["vel"][:, 2]) < .2))
    elapsed = 0; settled = None
    for j, good in enumerate(stable):
        elapsed = elapsed + 1 if good else 0
        if elapsed >= count:
            settled = float(a["t"][j]); break
    # Recovery must also return close to release altitude and remain within the
    # bounds through the end of the run. A brief earlier crossing is insufficient.
    recovered = stable & (np.abs(a["pos"][:, 2]) < .1)
    outside = np.flatnonzero(~recovered)
    start = int(outside[-1] + 1) if len(outside) else 0
    held = float(a["t"][start + count - 1]) if start + count <= len(recovered) else None
    peaks = np.flatnonzero((np.diff(a["tilt"])[:-1] > 0) & (np.diff(a["tilt"])[1:] < 0)) + 1
    under = np.flatnonzero(a["tilt"] < np.radians(5))
    return {"ground_contact": bool(crashed), "first_under_5deg_s": float(a["t"][under[0]]) if len(under) else None,
            "attitude_vertical_settled_s": settled,
            "recovery_held_to_end_s": held,
            "post_righting_tilt_peaks": [{"time_s": float(a["t"][j]), "tilt_deg": float(np.degrees(a["tilt"][j]))}
                                          for j in peaks if len(under) and j > under[0] and a["tilt"][j] > np.radians(.1)],
            "max_drop_m": float(max(0., -a["pos"][:, 2].min())),
            "final_horizontal_displacement_m": float(np.linalg.norm(a["pos"][-1, :2])),
            "final_horizontal_speed_m_s": float(np.linalg.norm(a["vel"][-1, :2])),
            "min_motor_force_n": float(a["motor_force"].min()),
            "max_motor_force_n": float(a["motor_force"].max()),
            "quaternion_norm_max_error": float(np.max(abs(np.linalg.norm(a["q"], axis=1) - 1)))}


def main():
    cfg = json.loads((OUT / "settings.json").read_text())
    results = {"settings": "settings.json", "cases": {}, "lag_sensitivity": {}, "convergence": {}}
    for key, factory in CASES.items():
        p = factory()
        ccfg = case_settings(key, cfg)
        a, crashed = simulate(p, ccfg)
        np.savez_compressed(OUT / f"{key}.npz", **a)
        m = metrics(a, crashed, cfg, p)
        results["cases"][key] = m
        fine, fine_crash = simulate(p, ccfg, dt=cfg["dt_s"] / 2)
        mf = metrics(fine, fine_crash, cfg, p)
        n = min(len(a["t"]), len(fine["t"][::2]))
        results["convergence"][key] = {
            "same_contact_outcome": crashed == fine_crash,
            "recovery_held_to_end_difference_s": (abs(m["recovery_held_to_end_s"] - mf["recovery_held_to_end_s"])
                                                 if m["recovery_held_to_end_s"] is not None and mf["recovery_held_to_end_s"] is not None else None),
            "max_position_difference_m": float(np.max(np.linalg.norm(a["pos"][:n] - fine["pos"][::2][:n], axis=1))),
            "max_tilt_difference_deg": float(np.degrees(np.max(abs(a["tilt"][:n] - fine["tilt"][::2][:n])))),
            "max_drop_difference_m": abs(m["max_drop_m"] - mf["max_drop_m"])}
        results["lag_sensitivity"][key] = {}
        for factor in cfg["lag_sensitivity_multipliers"]:
            if factor == 1:
                result = m
            else:
                alt, hit = simulate(p, ccfg, lag_multiplier=factor)
                result = metrics(alt, hit, cfg, p)
            results["lag_sensitivity"][key][str(factor)] = result
        print(key, json.dumps(m), flush=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
