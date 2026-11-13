#!/usr/bin/env python3
"""Monte Carlo dispersion sweep for the release-to-stabilization sim (Lane A gate).

The validation-proof gates require recovery to work "across a Monte Carlo sweep, not only
a single cherry-picked run", with CG error, motor-to-motor thrust variation, sensor noise,
and battery sag as explicit test cases. This module runs that sweep: each trial draws a
dispersed vehicle (mass/inertia/authority/latency multipliers on the nominal BOM tier)
plus an :class:`Imperfections` bundle (CG offset, motor mismatch, gyro + attitude
measurement noise, battery sag), simulates the standard demo release (60 deg tilt), and
reports the recovery rate with an exact Clopper-Pearson 95% lower bound — the same
zero-inflation-proof convention as ``classifier_stats.py``.

Dispersion ranges are stated engineering bounds on the locked nominal BOM, not fitted
values; they are deliberately wider than the expected build tolerances so the pass is
conservative. Run:  python -m Analysis.monte_carlo_recovery
"""

from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from Analysis.sim_release_recovery import (DroneParams, Imperfections, nominal_params,
                                           simulate, with_mixer)

# Dispersion bounds (uniform draws unless noted). Rationale in the table in
# Analysis/current-results.md; all are multipliers on the locked nominal BOM values.
MASS_RANGE = (0.95, 1.10)          # build growth is likelier than savings
INERTIA_RANGE = (0.85, 1.25)       # inertia is estimated, not CAD-derived yet
TORQUE_RANGE = (0.85, 1.10)        # prop/motor batch variation
THRUST_RANGE = (0.85, 1.05)        # thrust rarely exceeds datasheet
LATENCY_RANGE = (0.8, 1.5)         # detection/spool timing uncertainty
CG_OFFSET_MAX_M = 0.005            # 5 mm thrust-line offset (unbalanced build)
TORQUE_BIAS_MAX_FRAC = 0.10        # motor mismatch, fraction of max torque
GYRO_NOISE_RAD_S = 0.02            # per-step white rate noise
TILT_NOISE_RAD = np.radians(2.0)   # per-step white attitude-estimate error
INIT_TILT_RAD = np.radians(60.0)

# Frozen measured-authority gate. The 2 rad/s case is primary; the 1 and
# 3 rad/s cases are descriptive sensitivity checks and cannot rescue it.
PRIMARY_RATE_RAD_S = 2.0
PRIMARY_TRIALS = 1000
DESCRIPTIVE_TRIALS = 250
PRIMARY_SUCCESS_LOWER_BOUND = 0.95
MAX_DESCENT_M = 3.0
DEFAULT_RATES_AND_N = (
    (1.0, DESCRIPTIVE_TRIALS),
    (PRIMARY_RATE_RAD_S, PRIMARY_TRIALS),
    (3.0, DESCRIPTIVE_TRIALS),
)


def draw_case(rng: np.random.Generator,
              cg_offset_max_m: float = CG_OFFSET_MAX_M) -> tuple[DroneParams, Imperfections]:
    """One dispersed vehicle + imperfection bundle around the nominal BOM tier."""
    p = nominal_params()
    p = replace(
        p,
        mass_kg=p.mass_kg * rng.uniform(*MASS_RANGE),
        inertia_lateral_kg_m2=p.inertia_lateral_kg_m2 * rng.uniform(*INERTIA_RANGE),
        max_torque_n_m=p.max_torque_n_m * rng.uniform(*TORQUE_RANGE),
        max_thrust_n=p.max_thrust_n * rng.uniform(*THRUST_RANGE),
        detection_latency_s=p.detection_latency_s * rng.uniform(*LATENCY_RANGE),
        motor_start_latency_s=p.motor_start_latency_s * rng.uniform(*LATENCY_RANGE),
    )
    ang = rng.uniform(0.0, 2.0 * np.pi)
    r = cg_offset_max_m * np.sqrt(rng.uniform())        # uniform over the disk
    bias = rng.uniform(-1.0, 1.0, 3) * TORQUE_BIAS_MAX_FRAC * p.max_torque_n_m
    imp = Imperfections(
        cg_offset_m=(r * np.cos(ang), r * np.sin(ang)),
        thrust_scale=rng.uniform(0.90, 1.00),           # battery sag only hurts
        torque_bias_n_m=tuple(bias),
        gyro_noise_rad_s=GYRO_NOISE_RAD_S,
        tilt_noise_rad=TILT_NOISE_RAD,
        seed=int(rng.integers(0, 2**31 - 1)),
    )
    return p, imp


def clopper_pearson_lower(successes: int, n: int, alpha: float = 0.05) -> float:
    """Exact one-sided lower bound on a binomial proportion (no scipy dependency)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if successes < 0 or successes > n:
        raise ValueError("successes must lie in [0, n]")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if successes == 0:
        return 0.0
    if successes == n:
        return float(alpha ** (1.0 / n))
    # bisection on the Beta CDF via the incomplete-beta <-> binomial-tail identity:
    # P(X >= s | p) = alpha at the lower bound. Compute the binomial tail in
    # log space so the preregistered n=1000 gate does not overflow ``comb`` or
    # underflow the individual probability terms.
    def tail(pr: float) -> float:
        if pr <= 0.0:
            return 0.0
        if pr >= 1.0:
            return 1.0
        log_p = math.log(pr)
        log_q = math.log1p(-pr)
        terms = [
            math.lgamma(n + 1)
            - math.lgamma(k + 1)
            - math.lgamma(n - k + 1)
            + k * log_p
            + (n - k) * log_q
            for k in range(successes, n + 1)
        ]
        largest = max(terms)
        return math.exp(largest) * sum(math.exp(term - largest) for term in terms)
    lo, hi = 0.0, successes / n
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if tail(mid) < alpha:
            lo = mid
        else:
            hi = mid
    return lo


def required_successes_for_lower_bound(
    n: int = PRIMARY_TRIALS,
    target: float = PRIMARY_SUCCESS_LOWER_BOUND,
    alpha: float = 0.05,
) -> int:
    """Smallest success count whose exact one-sided lower bound clears target."""

    if not 0.0 < target < 1.0:
        raise ValueError("target must lie in (0, 1)")
    for successes in range(int(math.ceil(target * n)), n + 1):
        if clopper_pearson_lower(successes, n, alpha) >= target:
            return successes
    raise RuntimeError("no success count can meet the requested lower bound")


PRIMARY_REQUIRED_SUCCESSES = 962


def evaluate_primary_gate(result: dict) -> dict:
    """Apply the frozen statistical and altitude gate to one sweep result."""

    row = result.get("by_rate", {}).get(f"{PRIMARY_RATE_RAD_S:.1f}")
    if not row or row.get("n") != PRIMARY_TRIALS:
        return {"pass": False, "reason": "primary 2 rad/s result must contain 1000 trials"}
    checks = {
        "successes_at_least_962": row["successes"] >= PRIMARY_REQUIRED_SUCCESSES,
        "exact_lower_bound_at_least_0_95": (
            row["success_rate_95_lower"] >= PRIMARY_SUCCESS_LOWER_BOUND
        ),
        "maximum_descent_at_most_3m": (
            row.get("descent_max_all_m") is not None
            and row["descent_max_all_m"] <= MAX_DESCENT_M
        ),
    }
    return {"pass": all(checks.values()), "checks": checks}


def run_sweep(rates_and_n: tuple[tuple[float, int], ...] = DEFAULT_RATES_AND_N,
              seed: int = 20260702, cg_offset_max_m: float = CG_OFFSET_MAX_M,
              label: str = "as-toleranced", mixer_arm_m: float | None = None) -> dict:
    """Dispersion sweep at several tumble rates. Returns the results dict.

    With ``mixer_arm_m`` set, every drawn vehicle uses the physically-derived
    4-motor mixer authority (``with_mixer``) instead of the placeholder torque
    clip; the torque dispersion multiplier then scales the arm (authority)
    rather than the placeholder budget.
    """
    rng = np.random.default_rng(seed)
    out: dict = {"label": label, "init_tilt_deg": 60.0, "dispersions": {
        "mass_x": MASS_RANGE, "inertia_x": INERTIA_RANGE, "torque_x": TORQUE_RANGE,
        "thrust_x": THRUST_RANGE, "latency_x": LATENCY_RANGE,
        "cg_offset_max_m": cg_offset_max_m, "torque_bias_max_frac": TORQUE_BIAS_MAX_FRAC,
        "gyro_noise_rad_s": GYRO_NOISE_RAD_S, "tilt_noise_deg": 2.0,
        "thrust_sag_x": (0.90, 1.00),
        "authority_model": ("mixer" if mixer_arm_m else "placeholder"),
        "mixer_arm_m": mixer_arm_m}, "by_rate": {}}
    for rate, n in rates_and_n:
        succ, recovered_descents, all_descents = 0, [], []
        for _ in range(n):
            p, imp = draw_case(rng, cg_offset_max_m)
            if mixer_arm_m is not None:
                arm_scale = p.max_torque_n_m / nominal_params().max_torque_n_m
                p = with_mixer(p, arm_m=mixer_arm_m * arm_scale)
            r = simulate(p, rate, INIT_TILT_RAD, imperfections=imp)
            all_descents.append(r["max_descent_m"])
            if r["success"]:
                succ += 1
                recovered_descents.append(r["max_descent_m"])
        lb = clopper_pearson_lower(succ, n)
        out["by_rate"][f"{rate:.1f}"] = {
            "n": n, "successes": succ, "success_rate": succ / n,
            "success_rate_95_lower": lb,
            "descent_p50_m": (float(np.median(recovered_descents))
                              if recovered_descents else None),
            "descent_max_m": (float(np.max(recovered_descents))
                              if recovered_descents else None),
            "descent_max_all_m": float(np.max(all_descents)) if all_descents else None,
        }
        print(f"[{label}] rate {rate:.1f} rad/s: {succ}/{n} recovered "
              f"({100*succ/n:.1f}%, 95% lower bound {100*lb:.1f}%)"
              + (f", worst descent {np.max(all_descents):.2f} m" if all_descents else ""))
    return out


def cg_tolerance_scan(thrusts_n: tuple[float, ...] = (1.27, 4.2),
                      torque_n_m: float = 0.004) -> dict:
    """Static bound: max thrust-line offset the torque budget can even cancel.

    The disturbance torque is ``cg * thrust``; the controller cannot right the vehicle
    once that consumes the whole per-axis budget. This is the analytic version of what
    the Monte Carlo shows dynamically, and it converts the FAIL into a requirement.
    """
    return {f"thrust_{t:.2f}N": {"cg_100pct_budget_mm": 1e3 * torque_n_m / t,
                                 "cg_50pct_margin_mm": 1e3 * 0.5 * torque_n_m / t}
            for t in thrusts_n}


if __name__ == "__main__":
    import json
    from pathlib import Path

    # Scenario A — as-toleranced build (cg up to 5 mm): the honest headline.
    a = run_sweep(label="as-toleranced_cg5mm")
    # Scenario B — balance-controlled build (cg <= 1 mm): isolates CG as the driver.
    b = run_sweep(seed=20260703, cg_offset_max_m=0.001, label="balance-controlled_cg1mm")
    # Scenario C — as-toleranced build under the MIXER authority model (ASSUMED
    # 60 mm arm + datasheet thrust): the prediction the EST-REC-007 bench
    # measurement will confirm or kill.
    c = run_sweep(seed=20260704, label="as-toleranced_cg5mm_mixer-authority",
                  mixer_arm_m=0.060)
    static = cg_tolerance_scan()
    print("\nStatic CG-tolerance bound at the placeholder 0.004 N*m budget:")
    for k, v in static.items():
        print(f"  {k}: 100%-budget {v['cg_100pct_budget_mm']:.2f} mm, "
              f"50%-margin {v['cg_50pct_margin_mm']:.2f} mm")

    repo = Path(__file__).resolve().parents[1]
    out = {"note": ("GATE RESULT: FAIL at the placeholder torque authority "
                    "(EST-REC-007) — scenarios A/B. Scenario C is the PREDICTION "
                    "under the physically-derived mixer authority (ASSUMED 60 mm "
                    "arm, datasheet thrust, PID+airmode controller): it is what "
                    "the EST-REC-007 bench measurement must confirm before the "
                    "robustness claim is made. See Analysis/current-results.md."),
           "scenarios": [a, b, c], "static_cg_tolerance": static}
    with (repo / "Data" / "monte_carlo_results.json").open("w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n[written] Data/monte_carlo_results.json")
