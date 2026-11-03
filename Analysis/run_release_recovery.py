#!/usr/bin/env python3
"""Lane A deliverable runner: produce the release-to-stabilization demonstration.

Generates the data for (1) a time-series figure of a successful recovery (release -> passive tumble/fall ->
controller engages -> arrests tumble -> rights -> hovers) and (2) the recovery envelope across
the three locked-BOM tiers, plus a results JSON. This is the demonstrable result that converts
the project from "plan" to "characterized control result".

Run from the repo root:  python -m Analysis.run_release_recovery
Outputs: Data/release_recovery_results.json, the plotted series in Data/figure-data/
         (release_recovery_timeseries.csv, release_recovery_envelope.csv,
         release_recovery_figure.json) and the two captions in Figures/*.caption.md.
         Analysis/matlab/render_figures.m draws Figures/release_recovery_{timeseries,envelope}.{png,pdf}
         from those files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from Analysis.sim_release_recovery import (best_params, max_recoverable_rate,
                                           nominal_params, simulate, worst_params)

REPO = Path(__file__).resolve().parents[1]
FIGS = REPO / "Figures"
DATA = REPO / "Data"
PLOT_DATA = DATA / "figure-data"
TIERS = [("best", best_params()), ("nominal", nominal_params()), ("worst", worst_params())]
INIT_TILT = np.radians(60.0)


# Every fourth 0.5 ms solver sample (2 ms spacing) is enough to draw the traces.
TRACE_STRIDE = 4
UPRIGHT_DEG = 5.0


def timeseries_data(p, rate, name):
    """Simulate the demo case and write its plotted traces; returns the run."""
    r = simulate(p, rate, INIT_TILT)
    log = r["log"]
    PLOT_DATA.mkdir(parents=True, exist_ok=True)
    with (PLOT_DATA / "release_recovery_timeseries.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "tilt_deg", "body_rate_rad_s", "height_change_m", "thrust_n"])
        for k in range(0, len(log["t"]), TRACE_STRIDE):
            w.writerow([f"{log['t'][k]:.4f}", f"{np.degrees(log['tilt'][k]):.6g}",
                        f"{log['omega_mag'][k]:.6g}", f"{log['z'][k]:.6g}",
                        f"{log['thrust'][k]:.6g}"])
    passive = p.detection_latency_s + p.motor_start_latency_s
    on = log["t"] >= passive
    meta = {"tier": name, "initial_rate_rad_s": rate,
            "initial_tilt_deg": float(np.degrees(INIT_TILT)),
            "motors_off_s": passive, "recovery_time_s": r["recovery_time_s"],
            "altitude_lost_m": r["max_descent_m"],
            "peak_body_rate_after_motor_start_rad_s": float(log["omega_mag"][on].max()),
            "upright_deg": UPRIGHT_DEG, "available_height_m": p.available_height_m,
            "max_thrust_n": p.max_thrust_n, "sample_stride": TRACE_STRIDE,
            "solver_dt_s": float(log["t"][1] - log["t"][0])}
    return r, meta


def timeseries_caption(meta) -> str:
    rt = (f"stabilizes in {meta['recovery_time_s']:.2f} s" if meta["recovery_time_s"]
          else "does not stabilize")
    return (
        f"The {meta['tier']} tier {rt} after a {meta['initial_tilt_deg']:.0f}° tilt and "
        f"{meta['initial_rate_rad_s']:g} rad/s tumble, losing {meta['altitude_lost_m']:.2f} m of "
        f"{meta['available_height_m']:g} m. Deterministic 6-DoF simulation of the historical "
        "designed aircraft with estimated parameters; no measured hardware. "
        f"(a) Tilt [deg] falls below the {meta['upright_deg']:g}° upright line. "
        f"(b) Body rate [rad/s] peaks at {meta['peak_body_rate_after_motor_start_rad_s']:.1f} rad/s "
        "while righting, then settles. "
        f"(c) Height change [m]: the descent stops well above the ground, "
        f"{meta['available_height_m']:g} m below release. "
        f"(d) Collective thrust [N] saturates at the {meta['max_thrust_n']:g} N maximum, then "
        "settles at hover. Grey band: all motors off for detection and spool latency "
        f"({meta['motors_off_s']:g} s). Dashed line: stabilized time. Values: "
        "Data/figure-data/release_recovery_timeseries.csv."
    )


def envelope_data():
    rates = np.arange(0.0, 12.01, 0.5)
    summary, scans = {}, {}
    for name, p in TIERS:
        descent, ok_rate = [], []
        for rt in rates:
            r = simulate(p, rt, INIT_TILT)
            descent.append(r["max_descent_m"] if r["success"] else np.nan)
            ok_rate.append(r["success"])
        mr, edge = max_recoverable_rate(p, INIT_TILT, with_edge=True)
        summary[name] = {"max_recoverable_rate_rad_s": mr,
                         "max_recoverable_rate_deg_s": float(np.degrees(mr)),
                         "envelope_edge": edge,   # "failure" = real dynamic boundary;
                         # "gyro_limit" = never failed up to the sensor range — the
                         # envelope is measurement-limited, not authority-limited
                         "max_torque_n_m": p.max_torque_n_m, "max_thrust_n": p.max_thrust_n,
                         "available_height_m": p.available_height_m}
        scans[name] = (np.array(descent), np.array(ok_rate))
    return summary, rates, scans


def write_envelope_data(rates, scans, summary):
    """Write the scan already computed above; no simulation happens here."""
    PLOT_DATA.mkdir(parents=True, exist_ok=True)
    with (PLOT_DATA / "release_recovery_envelope.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tier", "initial_rate_rad_s", "recovered", "altitude_lost_m"])
        for name, _ in TIERS:
            descent, ok = scans[name]
            for rt, d, good in zip(rates, descent, ok):
                w.writerow([name, f"{rt:g}", int(bool(good)), f"{d:.6g}" if good else ""])
    return {"rates_step_rad_s": float(rates[1] - rates[0]),
            "gyro_limit_rad_s": TIERS[0][1].gyro_limit_rad_s,
            "available_height_m": TIERS[1][1].available_height_m,
            "initial_tilt_deg": float(np.degrees(INIT_TILT)),
            "tiers": [n for n, _ in TIERS]}


def read_envelope_csv(path=PLOT_DATA / "release_recovery_envelope.csv"):
    with Path(path).open() as fh:
        return list(csv.DictReader(fh))


def envelope_caption(rows, meta, summary) -> str:
    """Words for the envelope figure, from the plotted scan and the results JSON."""
    names = meta["tiers"]
    first_fail = {}
    for n in names:
        failed = [float(r["initial_rate_rad_s"]) for r in rows
                  if r["tier"] == n and r["recovered"] == "0"]
        first_fail[n] = min(failed) if failed else None
    failing = sorted((first_fail[n], n) for n in names if first_fail[n] is not None)
    never = [n for n in names if first_fail[n] is None]
    head = "; ".join(f"{n.capitalize() if k == 0 else n} tier first fails at {r:g} rad/s"
                     if k == 0 else f"{n} at {r:g}" for k, (r, n) in enumerate(failing))
    if never:
        head += f"; {' and '.join(never)} never fails in the scan"
    budget = meta["available_height_m"]
    lost = [float(r["altitude_lost_m"]) for r in rows if r["recovered"] == "1"]
    within = max(lost) < budget
    gyro = [n for n in names if summary[n]["envelope_edge"] == "gyro_limit"]
    return (
        f"{head}. Deterministic 6-DoF simulation with estimated parameter tiers; "
        f"{meta['initial_tilt_deg']:.0f}° initial tilt, {budget:g} m height budget, "
        f"{meta['rates_step_rad_s']:g} rad/s scan steps. (a) Top strip: tumble rates with no "
        "recovery (crosses). Lower panel: altitude lost [m] on recovered releases against "
        "initial tumble rate [rad/s]; "
        + (f"every recovery stays within the {budget:g} m budget (dotted line). " if within
           else f"dotted line: {budget:g} m budget. ")
        + "(b) Highest rate recovered before the first failure [rad/s], log scale. A filled "
        "marker is a dynamic failure edge; a hollow marker means no failure up to the gyro "
        f"range ({np.degrees(meta['gyro_limit_rad_s']):.0f}°/s, dotted line)"
        + (f", which only the {gyro[0]} tier reaches" if len(gyro) == 1 else "")
        + ". Values: Data/figure-data/release_recovery_envelope.csv and "
        "Data/release_recovery_results.json."
    )


def main():
    FIGS.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
    demo, ts_meta = timeseries_data(nominal_params(), rate=2.0, name="nominal")
    envelope, rates, scans = envelope_data()
    env_meta = write_envelope_data(rates, scans, envelope)
    with (PLOT_DATA / "release_recovery_figure.json").open("w") as fh:
        json.dump({"timeseries": ts_meta, "envelope": env_meta}, fh, indent=2)
        fh.write("\n")
    (FIGS / "release_recovery_timeseries.caption.md").write_text(timeseries_caption(ts_meta) + "\n")
    (FIGS / "release_recovery_envelope.caption.md").write_text(
        envelope_caption(read_envelope_csv(), env_meta, envelope) + "\n")

    results = {
        "scenario": {"initial_tilt_deg": 60.0, "available_height_m": 3.0,
                     "note": "released from rest with tumble + tilt; motors off during "
                             "detection+spool latency, then closed-loop recovery"},
        "demo_case": {"tier": "nominal", "initial_rate_rad_s": 2.0,
                      "success": demo["success"], "recovery_time_s": demo["recovery_time_s"],
                      "altitude_lost_m": demo["max_descent_m"], "peak_thrust_n": demo["peak_thrust_n"]},
        "envelope_by_tier": envelope,
    }
    with (DATA / "release_recovery_results.json").open("w") as fh:
        json.dump(results, fh, indent=2)

    print("=== Release-to-stabilization (Lane A) ===")
    print(f"demo: nominal BOM, 2.0 rad/s tumble + 60° tilt -> "
          f"recover {demo['recovery_time_s']:.2f}s, altitude lost {demo['max_descent_m']:.2f} m")
    for name, s in envelope.items():
        print(f"  {name:8s} max recoverable tumble: {s['max_recoverable_rate_rad_s']:.1f} rad/s "
              f"({s['max_recoverable_rate_deg_s']:.0f} deg/s)")
    print(f"plot data -> {PLOT_DATA}/  results -> {DATA}/release_recovery_results.json; "
          "draw the figures with Analysis/matlab/render_figures.m")


if __name__ == "__main__":
    main()
