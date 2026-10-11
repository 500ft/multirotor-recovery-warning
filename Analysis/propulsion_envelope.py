#!/usr/bin/env python3
"""Hand-calculated propulsion envelope for the stock Veeniix V995.

Bounds the total thrust the four stock rotors can produce, and the resulting
thrust-to-weight ratio and arrest height, from manufacturer figures, published
static tests of same-size propellers, and declared ranges for what nobody has
measured yet. Every input in ``Data/v995-envelope/inputs.json`` carries an
evidence state. Nothing here is a measurement of the V995; the result is the
pre-measurement bound for the physics feasibility baseline (ROADMAP step C) and
tells the bench what force range to expect.

Three constraints bound total thrust. The envelope takes the smallest at each
corner (low, nominal, high):

* battery: pack power (load voltage times C-rate times capacity) times the
  whole-vehicle thrust efficiency in g/W observed on a same-class 1S coreless
  aircraft, capped by the momentum-theory ideal for that power and disk area;
* rotor: T = 4 CT rho n^2 D^4 at the rotational speed range of same-size props;
* motor: four motors at the maximum continuous current of the coreless class,
  at the same efficiency.

Run: python -m Analysis.propulsion_envelope   (writes results.json next to inputs)
"""

from __future__ import annotations

import hashlib
import json
from math import pi, sqrt
from pathlib import Path

G = 9.80665
ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "Data" / "v995-envelope" / "inputs.json"
RESULTS = ROOT / "Data" / "v995-envelope" / "results.json"
CORNERS = ("low", "nominal", "high")


def pick(spec, corner):
    """Low, nominal or high value of a range input; scalars pass through."""
    if not isinstance(spec, dict) or "range" not in spec:
        return spec["value"] if isinstance(spec, dict) else spec
    lo, hi = spec["range"]
    if corner == "low":
        return lo
    if corner == "high":
        return hi
    return spec.get("nominal", 0.5 * (lo + hi))


def thrust_coefficient(thrust_N, rpm, diameter_m, rho):
    """CT = T / (rho n^2 D^4) with n in rev/s (Deters et al. 2018, eq. 3)."""
    n = rpm / 60.0
    return thrust_N / (rho * n * n * diameter_m**4)


def rotor_thrust_N(ct, rpm, diameter_m, rho, rotors=4):
    n = rpm / 60.0
    return rotors * ct * rho * n * n * diameter_m**4


def ideal_power_W(thrust_N, disk_area_m2, rho):
    """Momentum theory: induced power for a given thrust at hover, no losses."""
    return thrust_N**1.5 / sqrt(2.0 * rho * disk_area_m2)


def ideal_thrust_N(power_W, disk_area_m2, rho):
    """Inverse of ideal_power_W: the most thrust any rotor can make from power_W."""
    return (power_W * sqrt(2.0 * rho * disk_area_m2)) ** (2.0 / 3.0)


def arrest_height_m(descent_speed, thrust_to_weight, delay_s):
    """Height to stop a vertical descent: coast through the delay, then constant
    net deceleration (T/W - 1) g. None when thrust cannot exceed weight."""
    if thrust_to_weight <= 1.0:
        return None
    return descent_speed * delay_s + descent_speed**2 / (2.0 * G * (thrust_to_weight - 1.0))


def evaluate(p):
    rho = p["air_density_kg_m3"]["value"]
    b, m, prop = p["battery"], p["motor"], p["propeller"]
    capacity_Ah = b["capacity_mAh"] / 1000.0
    corners = {}
    for c in CORNERS:
        V = pick(b["load_voltage_V"], c)
        I_batt = pick(b["discharge_rate_C"], c) * capacity_Ah
        eff = pick(p["system_thrust_efficiency_g_per_W"], c)
        D = pick(prop["diameter_mm"], c) / 1000.0
        ct = pick(prop["thrust_coefficient_CT"], c)
        rpm = pick(m["max_rpm"], c)
        I_motor = pick(m["max_current_per_motor_A"], c)
        area = 4 * pi * D * D / 4.0
        P_batt = V * I_batt
        P_motor = 4 * V * I_motor
        battery_T = min(P_batt * eff * G / 1000.0, ideal_thrust_N(P_batt, area, rho))
        motor_T = min(P_motor * eff * G / 1000.0, ideal_thrust_N(P_motor, area, rho))
        rotor_T = rotor_thrust_N(ct, rpm, D, rho)
        constraints = {"battery_W_times_efficiency": battery_T, "rotor_CT_rpm_D": rotor_T, "motor_current": motor_T}
        binding = min(constraints, key=constraints.get)
        T = constraints[binding]
        corners[c] = {
            "inputs": {"load_voltage_V": V, "pack_current_A": I_batt, "pack_power_W": P_batt,
                       "efficiency_g_per_W": eff, "diameter_m": D, "CT": ct, "max_rpm": rpm,
                       "motor_current_A": I_motor, "disk_area_total_m2": area},
            "ideal_thrust_from_pack_power_N": ideal_thrust_N(P_batt, area, rho),
            "constraints_N": constraints,
            "binding_constraint": binding,
            "total_thrust_N": T,
            "total_thrust_g": T * 1000.0 / G,
            "implied_rpm_at_envelope_thrust": 60.0 * sqrt(T / (4 * ct * rho * D**4)),
        }
        corners[c]["implied_blade_pass_Hz"] = corners[c]["implied_rpm_at_envelope_thrust"] / 60.0 * prop["blade_count"]["value"]
    hover = {}
    for name, mass_g in p["mass_g"]["hypotheses"].items():
        W = mass_g / 1000.0 * G
        hover[name] = {"mass_g": mass_g, "weight_N": W}
        for c in CORNERS:
            tw = corners[c]["total_thrust_N"] / W
            heights = {}
            for v in p["arrest"]["descent_speeds_m_s"]:
                heights[str(v)] = {d: arrest_height_m(v, tw, pick(p["arrest"]["delay_s"], d)) for d in CORNERS}
            hover[name][c] = {"thrust_to_weight": tw, "can_hover": tw > 1.0,
                              "hover_power_W_at_efficiency": W * 1000.0 / G / corners[c]["inputs"]["efficiency_g_per_W"],
                              "arrest_height_m_by_descent_speed_and_delay": heights}
    deters = []
    for row in prop["thrust_coefficient_CT"]["deters_table3_rows"]:
        deters.append({**row, "CT_at_rho_1p225": thrust_coefficient(row["max_thrust_g"] / 1000.0 * G, row["max_rpm"], row["diameter_mm"] / 1000.0, 1.225)})
    states = sorted({v["state"] for v in walk_states(p)})
    return {
        "evidence": "PRE-MEASUREMENT ENVELOPE. No V995 quantity is measured; evidence states of the inputs are listed. Not a bench result and not the physics baseline itself.",
        "input_evidence_states_present": states,
        "pre_measurement": "measured" not in states,
        "corners": corners,
        "hover_and_arrest_by_mass_hypothesis": hover,
        "deters_2018_table3_back_calculated_CT": deters,
        "reading": "Which constraint binds changes with the corner: the rotor-speed bound at the low and nominal corners (a toy motor that cannot spin a small, low-CT propeller fast), the pack power at the high corner. The low corner stacks every pessimistic choice and is not a realistic aircraft. Thrust-to-weight depends on the unmeasured mass more than on any other input, so AC-06 is the first number to take; if the aircraft hovers, every corner with thrust-to-weight at or below one at the true mass is excluded. The implied blade-pass frequency is what a phone spectrogram can check during a hover; with the measured diameter and a scale reading it gives a direct CT for the real propeller.",
    }


def walk_states(obj):
    if isinstance(obj, dict):
        if "state" in obj:
            yield obj
        for v in obj.values():
            yield from walk_states(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_states(v)


def main():
    raw = INPUTS.read_bytes()
    result = evaluate(json.loads(raw))
    result["inputs_sha256"] = hashlib.sha256(raw).hexdigest()
    result["implementation_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    RESULTS.write_text(json.dumps(result, indent=2) + "\n")
    c = result["corners"]
    print(f"total thrust envelope: {c['low']['total_thrust_g']:.1f} / {c['nominal']['total_thrust_g']:.1f} / {c['high']['total_thrust_g']:.1f} g (low / nominal / high)")
    for name, h in result["hover_and_arrest_by_mass_hypothesis"].items():
        print(f"  mass {h['mass_g']:.1f} g ({name}): T/W {h['low']['thrust_to_weight']:.2f} / {h['nominal']['thrust_to_weight']:.2f} / {h['high']['thrust_to_weight']:.2f}")
    print(RESULTS)


if __name__ == "__main__":
    main()
