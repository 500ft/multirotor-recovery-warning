import unittest
import numpy as np
from Analysis.sim_release_recovery import (axis_angle_quat, nominal_params, worst_params, simulate,
    quat_to_rotmat, tilt_rotation_error, _control)


class TestLargeTiltCorrection(unittest.TestCase):
    def test_small_angle_and_large_angle_have_correct_axis_and_magnitude(self):
        for axis in [(1, 0, 0), (0, 1, 0), (1, 1, 0), (-1, 2, 0)]:
            for degrees in [.001, 60, 142.2387560927618, 179.99]:
                q = axis_angle_quat(np.asarray(axis), np.radians(degrees))
                e = tilt_rotation_error(q)
                self.assertAlmostEqual(np.linalg.norm(e), np.radians(degrees), places=10)
                # Apply the correction in body coordinates; body z then points up.
                correction = axis_angle_quat(e, np.linalg.norm(e))
                R = quat_to_rotmat(q) @ quat_to_rotmat(correction)
                np.testing.assert_allclose(R[:, 2], [0, 0, 1], atol=1e-10)

    def test_inverted_has_nonzero_correction_and_bounded_actuation(self):
        p = nominal_params()
        for axis in [(1, 0, 0), (0, 1, 0), (1, 1, 0)]:
            q = axis_angle_quat(np.asarray(axis), np.pi)
            self.assertAlmostEqual(np.linalg.norm(tilt_rotation_error(q)), np.pi)
            torque, thrust, _ = _control(q, np.zeros(3), np.zeros(3), np.zeros(3), p,
                                         attitude_controller='tilt_angle')
            self.assertGreater(np.linalg.norm(torque), 0)
            self.assertLessEqual(np.max(np.abs(torque)), p.max_torque_n_m)
            self.assertEqual(thrust, 0.0)

    def test_quaternion_sign_and_yaw_invariance(self):
        q = axis_angle_quat(np.array([0, 1, 0]), 2.5)
        np.testing.assert_array_equal(tilt_rotation_error(q), tilt_rotation_error(-q))
        self.assertEqual(tilt_rotation_error(axis_angle_quat(np.array([0, 0, 1]), 2.5)).tolist(), [0, 0, 0])

    def test_default_control_is_legacy_and_invalid_mode_rejected(self):
        p = nominal_params(); q = axis_angle_quat(np.array([0, 1, 0]), 1)
        args=(q,np.ones(3),np.zeros(3),np.zeros(3),p)
        a=_control(*args); b=_control(*args,attitude_controller='legacy')
        np.testing.assert_array_equal(a[0], b[0]); self.assertEqual(a[1], b[1])
        with self.assertRaises(ValueError): _control(*args,attitude_controller='unknown')


class TestInvertedAxisLatch(unittest.TestCase):
    def test_pessimistic_inversion_is_stable_under_step_refinement(self):
        from dataclasses import replace
        p = replace(worst_params(), available_height_m=15.0)
        results = [simulate(p, 0.0, np.pi, dt=dt, t_max=9.0,
                            attitude_controller='tilt_angle')
                   for dt in [.001, .0005]]
        self.assertTrue(all(r['success'] and not r['crashed'] for r in results))
        self.assertLess(abs(results[0]['max_descent_m'] - results[1]['max_descent_m']), .01)
