import json
from dataclasses import replace
import unittest
import numpy as np
from Analysis.recovery_video import OUT, allocate, motor_step, simulate, metrics
from Analysis.sim_release_recovery import nominal_params, G
from Analysis.failure_allocation import healthy_wrench_map


class TestRecoveryVideoPhysics(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((OUT / 'settings.json').read_text())
        self.p = nominal_params()
        self.B = healthy_wrench_map(self.cfg['arm_m'], self.p.max_thrust_n,
                                   self.p.max_torque_n_m)
        self.inv = np.linalg.inv(self.B)
        self.cap = self.p.max_thrust_n / 4

    def test_feasible_wrenches_reproduce_rotor_forces(self):
        rng = np.random.default_rng(42)
        for forces in rng.uniform(0, self.cap, (100, 4)):
            wrench = self.B @ forces
            actual = allocate(wrench[0], wrench[1:], self.inv, self.cap)
            np.testing.assert_allclose(actual, forces, atol=1e-12)

    def test_saturation_trades_collective_for_torque(self):
        wanted = np.array([.004, -.004, 0.])
        f = allocate(self.p.max_thrust_n, wanted, self.inv, self.cap)
        self.assertTrue(np.all((f >= 0) & (f <= self.cap)))
        self.assertLess(f.sum(), self.p.max_thrust_n)
        np.testing.assert_allclose((self.B @ f)[1:], wanted, atol=1e-12)
        # At the actual all-motors-full limit there is no differential moment.
        np.testing.assert_allclose((self.B @ np.full(4, self.cap))[1:], 0, atol=1e-12)

    def test_large_torque_preserves_direction_inside_box(self):
        wanted = np.array([1., -.5, .05])
        f = allocate(self.p.max_thrust_n, wanted, self.inv, self.cap)
        moment = (self.B @ f)[1:]
        self.assertTrue(np.all((f >= 0) & (f <= self.cap)))
        np.testing.assert_allclose(moment / wanted, np.full(3, moment[0]), atol=1e-12)

    def test_motor_step_matches_analytic_exponential(self):
        tau = self.cfg['motor_tau_up_s']
        speed = np.zeros(4)
        for _ in range(100):
            speed = motor_step(speed, np.ones(4), tau / 100, tau, 2*tau)
        np.testing.assert_allclose(speed, 1-np.exp(-1), atol=1e-12)
        np.testing.assert_allclose(speed**2, (1-np.exp(-1))**2, atol=1e-12)
        speed = motor_step(np.ones(4), np.zeros(4), 2*tau, tau, 2*tau)
        np.testing.assert_allclose(speed, np.exp(-1), atol=1e-12)

    def test_unpowered_fall_matches_closed_form(self):
        cfg = {**self.cfg, 'duration_s': .04}
        a, crashed = simulate(replace(self.p, drag_coefficient=0.), cfg)
        np.testing.assert_allclose(a['pos'][:, 2], -.5 * G * a['t']**2, atol=1e-12)
        np.testing.assert_allclose(a['vel'][:, 2], -G * a['t'], atol=1e-12)
        np.testing.assert_array_equal(a['motor_force'], 0.)
        self.assertFalse(crashed)

    def test_rate_feedback_matches_independent_linear_filter(self):
        cfg = {**self.cfg, 'duration_s': .8, 'gyro_filter_tau_s': .12}
        a, _ = simulate(self.p, cfg)
        decay = np.exp(-cfg['dt_s'] / cfg['gyro_filter_tau_s'])
        n = len(a['omega']) - 1
        kernel = (1-decay)*decay**np.arange(n)
        expected = np.column_stack([np.convolve(a['omega'][:-1, axis], kernel)[:n]
                                    for axis in range(3)])
        expected += decay**np.arange(1,n+1)[:,None]*a['omega'][0]
        np.testing.assert_allclose(a['omega_feedback'][1:], expected, atol=1e-12)
        self.assertGreater(np.max(abs(a['omega_feedback']-a['omega'])), .1)

    def test_temporary_settling_does_not_count_as_held_recovery(self):
        cfg = {**self.cfg, 'duration_s': 1.}
        a, _ = simulate(self.p, cfg)
        a['tilt'][:] = 0.; a['omega'][:] = 0.; a['vel'][:] = 0.; a['pos'][:] = 0.
        a['tilt'][-1] = np.radians(10)
        m = metrics(a, False, cfg, self.p)
        self.assertIsNotNone(m['attitude_vertical_settled_s'])
        self.assertIsNone(m['recovery_held_to_end_s'])

    def test_contact_is_reported_and_stops_integration(self):
        cfg = {**self.cfg, 'duration_s': 1.}
        a, crashed = simulate(replace(self.p, available_height_m=.01,
                                      detection_latency_s=2.), cfg)
        self.assertTrue(crashed)
        self.assertLess(a['t'][-1], cfg['duration_s'])
        self.assertLessEqual(a['pos'][-1, 2], -.01)


if __name__ == '__main__':
    unittest.main()
