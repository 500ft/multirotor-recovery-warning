"""Measure the replay allocator's roll/pitch authority against the scenario C mixer bound.

Scenario C (``sim_release_recovery.with_mixer``) clips roll and pitch torque at
``tau_rp(T) = 2 sqrt(2) arm min(T/4, T_max/4 - T/4)``. The replay
(``recovery_video.allocate``) instead solves four motor forces inside
``[0, T_max/4]``. This sweep asks the allocator, at each commanded collective
and each roll/pitch direction, for the largest torque it realizes without
shifting the collective or scaling the differential, and compares the answer
with the bound. Requests beyond that envelope are passed through as well and
judged at the collective the allocator actually realizes. The committed replay
logs are checked the same way, sample by sample. Runs each displayed case's
parameter set and writes ``Data/recovery-video/allocator-envelope.json``.
"""
import json
import numpy as np
from Analysis import sim_release_recovery as base
from Analysis.failure_allocation import healthy_wrench_map
from Analysis.recovery_video import OUT, allocate

PARAMS = {"historical_nominal_params": ("best",),
          "historical_worst_params": ("nominal", "worst")}
FACTORIES = {"historical_nominal_params": base.nominal_params,
             "historical_worst_params": base.worst_params}
TOL = 1e-12
BRACKET_N_M = 1.0          # far above any bound at these thrusts
BISECTIONS = 40


def realized(thrust, torque, matrix, inverse, cap):
    """Wrench (T, tau_x, tau_y, tau_z) the allocator actually produces."""
    return matrix @ allocate(thrust, torque, inverse, cap)


def exact(thrust, torque, matrix, inverse, cap):
    w = realized(thrust, torque, matrix, inverse, cap)
    return abs(w[0] - thrust) <= TOL * max(1.0, thrust) and np.all(np.abs(w[1:] - torque) <= TOL)


def achievable(thrust, direction, matrix, inverse, cap, yaw=0.0):
    """Largest torque magnitude along ``direction`` realized exactly at ``thrust``."""
    lo, hi = 0.0, BRACKET_N_M
    if exact(thrust, hi * direction + np.r_[0., 0., yaw], matrix, inverse, cap):
        return hi
    for _ in range(BISECTIONS):
        mid = 0.5 * (lo + hi)
        if exact(thrust, mid * direction + np.r_[0., 0., yaw], matrix, inverse, cap):
            lo = mid
        else:
            hi = mid
    return lo


def sweep(p, arm_m, collective_step_n, direction_step_deg, yaw=0.0):
    """Per-collective achievable roll/pitch torque against the mixer bound."""
    cap = p.max_thrust_n / 4
    matrix = healthy_wrench_map(arm_m, p.max_thrust_n, p.max_torque_n_m)
    inverse = np.linalg.inv(matrix)
    thrusts = np.arange(0.0, p.max_thrust_n + collective_step_n / 2, collective_step_n)
    angles = np.radians(np.arange(0.0, 360.0, direction_step_deg))
    rows = []
    for thrust in thrusts:
        bound = float(base.mixer_torque_limit(thrust, p.max_thrust_n, arm_m))
        axis = magnitude = shifted_excess = 0.0
        magnitude_min = np.inf
        for angle in angles:
            u = np.array([np.cos(angle), np.sin(angle), 0.0])
            m = achievable(thrust, u, matrix, inverse, cap, yaw)
            axis = max(axis, m * max(abs(u[0]), abs(u[1])))
            magnitude = max(magnitude, m)
            magnitude_min = min(magnitude_min, m)
            # Requests beyond the envelope: judged at the realized collective.
            for request in (2.0 * m, BRACKET_N_M):
                w = realized(thrust, request * u + np.r_[0., 0., yaw], matrix, inverse, cap)
                shifted_bound = base.mixer_torque_limit(w[0], p.max_thrust_n, arm_m)
                shifted_excess = max(shifted_excess, max(abs(w[1]), abs(w[2])) - shifted_bound)
        axis, magnitude, magnitude_min, shifted_excess = map(float, (axis, magnitude, magnitude_min, shifted_excess))
        rows.append({"collective_n": float(thrust), "bound_n_m": bound,
                     "achievable_axis_n_m": axis, "achievable_magnitude_max_n_m": magnitude,
                     "achievable_magnitude_min_n_m": magnitude_min,
                     "axis_ratio": axis / bound if bound > 0 else None,
                     "magnitude_ratio_max": magnitude / bound if bound > 0 else None,
                     "magnitude_ratio_min": magnitude_min / bound if bound > 0 else None,
                     "saturated_axis_excess_n_m": shifted_excess})
    return rows


def summarize(rows):
    with_bound = [r for r in rows if r["axis_ratio"] is not None]
    peak = max(with_bound, key=lambda r: r["axis_ratio"])
    trough = min(with_bound, key=lambda r: r["magnitude_ratio_min"])
    zero_bound = [r for r in rows if r["axis_ratio"] is None]
    return {
        "max_axis_ratio": peak["axis_ratio"],
        "max_axis_ratio_at_collective_n": peak["collective_n"],
        "min_axis_ratio": min(r["axis_ratio"] for r in with_bound),
        "collectives_with_axis_ratio_within_1e-9_of_1": sum(1 for r in with_bound if r["axis_ratio"] >= 1 - 1e-9),
        "collectives_with_bound": len(with_bound),
        "max_magnitude_ratio": max(r["magnitude_ratio_max"] for r in with_bound),
        "min_magnitude_ratio": trough["magnitude_ratio_min"],
        "min_magnitude_ratio_at_collective_n": trough["collective_n"],
        "max_achievable_where_bound_is_zero_n_m": max((r["achievable_axis_n_m"] for r in zero_bound), default=0.0),
        "max_saturated_axis_excess_n_m": max(r["saturated_axis_excess_n_m"] for r in rows),
    }


def logged_trajectory(case, p, arm_m):
    """Realized wrench of every logged replay sample against the bound at its own collective."""
    matrix = healthy_wrench_map(arm_m, p.max_thrust_n, p.max_torque_n_m)
    with np.load(OUT / f"{case}.npz") as a:
        w = a["motor_force"] @ matrix.T
    bound = np.array([base.mixer_torque_limit(t, p.max_thrust_n, arm_m) for t in w[:, 0]])
    powered = bound > 0
    axis = np.max(np.abs(w[:, 1:3]), axis=1)
    ratio = axis[powered] / bound[powered]
    peak = int(np.argmax(ratio))
    return {"samples": int(len(w)), "samples_with_bound": int(powered.sum()),
            "max_axis_torque_where_bound_is_zero_n_m": float(axis[~powered].max()) if (~powered).any() else 0.0,
            "max_axis_ratio": float(ratio[peak]),
            "max_axis_ratio_at_collective_n": float(w[powered][peak, 0]),
            "max_yaw_torque_n_m": float(np.abs(w[:, 3]).max()),
            "max_yaw_fraction_of_placeholder": float(np.abs(w[:, 3]).max() / p.max_torque_n_m)}


def main(collective_step_n=0.01, direction_step_deg=2.0, table_every_n=0.05):
    cfg = json.loads((OUT / "settings.json").read_text())
    out = {"settings": "settings.json", "arm_m": cfg["arm_m"],
           "bound": "tau_rp(T) = 2 sqrt(2) arm min(T/4, T_max/4 - T/4), sim_release_recovery.mixer_torque_limit",
           "collective_step_n": collective_step_n, "direction_step_deg": direction_step_deg,
           "bisection_iterations": BISECTIONS, "exactness_tolerance": TOL,
           "yaw_sweeps": {"collective_step_n": 5 * collective_step_n, "direction_step_deg": 15 * direction_step_deg},
           "parameter_sets": {}}
    for name, cases in PARAMS.items():
        p = FACTORIES[name]()
        rows = sweep(p, cfg["arm_m"], collective_step_n, direction_step_deg)
        out["parameter_sets"][name] = {
            "replay_cases": list(cases), "max_thrust_n": p.max_thrust_n,
            "yaw_placeholder_n_m": p.max_torque_n_m,
            "zero_yaw": summarize(rows),
            "yaw_at_half_placeholder": summarize(sweep(p, cfg["arm_m"], 5 * collective_step_n,
                                                       15 * direction_step_deg, yaw=0.5 * p.max_torque_n_m)),
            "yaw_at_placeholder": summarize(sweep(p, cfg["arm_m"], 5 * collective_step_n,
                                                  15 * direction_step_deg, yaw=p.max_torque_n_m)),
            "logged_replay": {case: logged_trajectory(case, p, cfg["arm_m"]) for case in cases},
            "table_every_n": table_every_n,
            "table": rows[::round(table_every_n / collective_step_n)]}
        print(name, json.dumps({k: v for k, v in out["parameter_sets"][name].items() if k != "table"}), flush=True)
    (OUT / "allocator-envelope.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
