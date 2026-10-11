"""Independent checks of the V995 propulsion envelope arithmetic."""
import json
from decimal import Decimal as D
from math import pi, sqrt
from pathlib import Path
import unittest

from Analysis.propulsion_envelope import (G, arrest_height_m, evaluate, ideal_power_W,
                                          ideal_thrust_N, rotor_thrust_N, thrust_coefficient)

ROOT = Path(__file__).resolve().parents[2]
P = json.loads((ROOT / "Data" / "v995-envelope" / "inputs.json").read_text())


class EnvelopeTests(unittest.TestCase):
    def test_deters_table3_back_calculation(self):
        # Independent Decimal arithmetic for two rows of Deters et al. 2018 Table 3.
        g = D("9.80665"); rho = D("1.225")
        cases = {"Crazyflie": (D("10.0"), D("20000"), D("0.047")), "Cheerson CX-10C": (D("4.0"), D("47000"), D("0.030"))}
        rows = {r["aircraft"]: r for r in evaluate(P)["deters_2018_table3_back_calculated_CT"]}
        for name, (grams, rpm, dia) in cases.items():
            n = rpm / D(60)
            expected = (grams / D(1000) * g) / (rho * n * n * dia**4)
            self.assertAlmostEqual(rows[name]["CT_at_rho_1p225"], float(expected), places=9)
        self.assertAlmostEqual(rows["Crazyflie"]["CT_at_rho_1p225"], 0.148, places=3)
        self.assertAlmostEqual(rows["JJRC H36"]["CT_at_rho_1p225"], 0.333, places=3)
        lo, hi = P["propeller"]["thrust_coefficient_CT"]["range"]
        two_blade = [r["CT_at_rho_1p225"] for r in rows.values() if r["blades"] == 2]
        self.assertLess(max(two_blade), hi)
        self.assertGreater(rows["JJRC H36"]["CT_at_rho_1p225"], hi)  # four blades sit above the declared three-blade band

    def test_momentum_theory_inverts(self):
        area = 4 * pi * 0.035**2 / 4
        for T in (0.1, 0.35, 0.8):
            self.assertAlmostEqual(ideal_thrust_N(ideal_power_W(T, area, 1.225), area, 1.225), T, places=12)
        # Leishman hover induced power: P = T sqrt(T / (2 rho A)).
        self.assertAlmostEqual(ideal_power_W(0.35, area, 1.225), 0.35 * sqrt(0.35 / (2 * 1.225 * area)), places=12)

    def test_rotor_thrust_and_ct_are_inverse(self):
        T = rotor_thrust_N(0.18, 30000, 0.035, 1.225)
        self.assertAlmostEqual(thrust_coefficient(T / 4, 30000, 0.035, 1.225), 0.18, places=12)

    def test_envelope_corners_are_ordered_and_battery_bound(self):
        r = evaluate(P)
        c = r["corners"]
        self.assertLess(c["low"]["total_thrust_N"], c["nominal"]["total_thrust_N"])
        self.assertLess(c["nominal"]["total_thrust_N"], c["high"]["total_thrust_N"])
        for corner in c.values():
            self.assertLessEqual(corner["total_thrust_N"], corner["ideal_thrust_from_pack_power_N"])
            self.assertEqual(corner["total_thrust_N"], min(corner["constraints_N"].values()))
        self.assertEqual(c["low"]["binding_constraint"], "rotor_CT_rpm_D")
        self.assertEqual(c["high"]["binding_constraint"], "battery_W_times_efficiency")
        # Nominal pack power by hand: 3.7 V x 15 C x 0.180 Ah = 9.99 W; x 3.5 g/W = 34.965 g.
        self.assertAlmostEqual(c["nominal"]["inputs"]["pack_power_W"], 9.99, places=9)
        self.assertAlmostEqual(c["nominal"]["constraints_N"]["battery_W_times_efficiency"], 34.965 / 1000 * G, places=9)
        # Nominal rotor bound by hand: 4 x 0.18 x 1.225 x (30000/60)^2 x 0.035^4.
        rotor = D(4) * D("0.18") * D("1.225") * D(500) ** 2 * D("0.035") ** 4
        self.assertAlmostEqual(c["nominal"]["constraints_N"]["rotor_CT_rpm_D"], float(rotor), places=12)
        self.assertLess(float(rotor), 34.965 / 1000 * G)  # the rotor bound is the smaller one at nominal
        self.assertEqual(c["nominal"]["binding_constraint"], "rotor_CT_rpm_D")

    def test_hover_feasibility_and_pre_measurement_flag(self):
        r = evaluate(P)
        self.assertTrue(r["pre_measurement"])
        h = r["hover_and_arrest_by_mass_hypothesis"]
        self.assertFalse(h["owner_estimate"]["low"]["can_hover"])
        self.assertTrue(h["listing"]["nominal"]["can_hover"])
        rotor = float(D(4) * D("0.18") * D("1.225") * D(500) ** 2 * D("0.035") ** 4)
        self.assertAlmostEqual(h["listing"]["nominal"]["thrust_to_weight"], rotor / (22.3 / 1000 * G), places=9)

    def test_arrest_height_formula(self):
        self.assertIsNone(arrest_height_m(2.0, 1.0, 0.1))
        # v = 2 m/s, T/W = 1.5, delay 0.1 s: 0.2 m coast + 4 / (2 g 0.5) m.
        self.assertAlmostEqual(arrest_height_m(2.0, 1.5, 0.1), 0.2 + 4.0 / (2 * G * 0.5), places=12)
        self.assertLess(arrest_height_m(2.0, 2.0, 0.1), arrest_height_m(2.0, 1.5, 0.1))


if __name__ == "__main__":
    unittest.main()
