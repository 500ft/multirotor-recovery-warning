"""Compare historical and angle-error controllers without changing plant limits.

Development simulation only. Height changes the collision plane, not the target
altitude. Source video cases start at 60 degrees; its maximum logged angle is
also used as a new initial-condition stress test, not a measured flight input.
"""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import numpy as np

from Analysis.sim_release_recovery import nominal_params, worst_params, simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Data/large-tilt-recovery'
PROTOCOL = {
    'scope': 'historical estimated aircraft; release_startup; independent torque/thrust limits',
    'controllers': ['legacy', 'tilt_angle'],
    'antipodal_axis_latch_exit_deg_from_inversion': 5.0,
    'initial_tilt_deg': [60.0, 142.2387560927618, 180.0],
    'initial_rate_rad_s': [0.0, 4.0],
    'tiers': ['nominal', 'worst'],
    'dt_s': [0.0005, 0.00025],
    't_max_s': 12.0,
    'diagnostic_height_m': 1000.0,
    'height_step_m': 0.5,
    'illustrative_clearance_m': 0.25,
    'tumble_axis': [1.0, 1.0, 0.0],
    'tilt_axis': [0.0, 1.0, 0.0],
    'success': {'tilt_below_deg': 5.0, 'rate_below_rad_s': 0.3,
                'absolute_vz_below_m_s': 0.2, 'continuous_duration_s': 0.25},
    'interpretation': 'development grid, not a continuous envelope or physical release recommendation',
}


def independent_settle(log, dt):
    """Check simultaneous pre-step states independently of simulator bookkeeping."""
    ok = ((log['tilt'] < np.radians(5)) & (log['omega_mag'] < .3)
          & (np.abs(log['vz']) < .2))
    count = 0
    for k, valid in enumerate(ok):
        count = count + 1 if valid else 0
        if count * dt >= .25:
            return float(log['t'][k])
    return None


def metrics(result, dt):
    log = result['log']
    settled = independent_settle(log, dt)
    return {
        'simulator_success': result['success'],
        'logged_state_success': settled is not None,
        'settled_since_release_s': settled,
        'maximum_descent_m': result['max_descent_m'],
        'peak_tilt_deg': float(np.degrees(np.max(log['tilt']))),
        'peak_rate_rad_s': float(np.max(log['omega_mag'])),
        'peak_thrust_n': result['peak_thrust_n'],
        'final_tilt_deg': result['final_tilt_deg'],
        'last_time_s': float(log['t'][-1]),
        'crashed': result['crashed'],
    }


def run_case(job):
    tier, tilt, rate, controller = job
    factories = {'nominal': nominal_params, 'worst': worst_params}
    p = replace(factories[tier](), available_height_m=PROTOCOL['diagnostic_height_m'])
    runs = []
    trace = None
    for dt in PROTOCOL['dt_s']:
        result = simulate(p, rate, np.radians(tilt), dt=dt,
                          t_max=PROTOCOL['t_max_s'], attitude_controller=controller)
        runs.append(metrics(result, dt))
        if dt == PROTOCOL['dt_s'][0]:
            log = result['log']
            trace = {'tier': tier, 'initial_tilt_deg': tilt,
                     'rate_rad_s': rate, 'controller': controller,
                     't_s': log['t'][::40].tolist(),
                     'tilt_deg': np.degrees(log['tilt'][::40]).tolist(),
                     'descent_m': (-log['z'][::40]).tolist()}
    good = all(x['simulator_success'] and x['logged_state_success'] and not x['crashed'] for x in runs)
    height = None
    height_verification = None
    if good:
        drop = max(x['maximum_descent_m'] for x in runs)
        step = PROTOCOL['height_step_m']
        height = float(np.ceil((drop + PROTOCOL['illustrative_clearance_m']) / step) * step)
        dt = PROTOCOL['dt_s'][-1]
        target = replace(p, available_height_m=height)
        checked = simulate(target, rate, np.radians(tilt), dt=dt,
                           t_max=PROTOCOL['t_max_s'], attitude_controller=controller)
        height_verification = metrics(checked, dt)
        assert checked['success'] and not checked['crashed']
        assert height_verification['logged_state_success']
        assert height > height_verification['maximum_descent_m']
    row = {'tier': tier, 'initial_tilt_deg': tilt, 'initial_rate_rad_s': rate,
           'controller': controller, 'runs': runs,
           'same_outcome_on_halved_dt': runs[0]['logged_state_success'] == runs[1]['logged_state_success'],
           'descent_difference_m': abs(runs[0]['maximum_descent_m'] - runs[1]['maximum_descent_m']),
           'tested_release_height_m': height, 'height_verification': height_verification}
    return row, trace


def main():
    from concurrent.futures import ProcessPoolExecutor
    import os
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'protocol.json').write_text(json.dumps(PROTOCOL, indent=2) + '\n')
    jobs = [(tier, tilt, rate, controller)
            for tier in PROTOCOL['tiers'] for tilt in PROTOCOL['initial_tilt_deg']
            for rate in PROTOCOL['initial_rate_rad_s'] for controller in PROTOCOL['controllers']]
    rows, traces = [], []
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
        for row, trace in pool.map(run_case, jobs):
            rows.append(row); traces.append(trace)
            print(row['tier'], round(row['initial_tilt_deg'], 3), row['initial_rate_rad_s'],
                  row['controller'], 'height', row['tested_release_height_m'], flush=True)
    source = ROOT / 'Analysis/sim_release_recovery.py'
    output = {'protocol': 'protocol.json', 'model_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'parameters': {k: asdict(f()) for k, f in {'nominal': nominal_params, 'worst': worst_params}.items()},
              'cases': rows,
              'limits': ['Independent thrust/torque limits; estimated historical plant, not Crazyflie.',
                         'No horizontal-speed, clearance envelope, battery or sensor-estimator validation.',
                         'Exactly inverted uses a discontinuous deterministic body-x tie-break and axis latch.',
                         'No settling by the time limit is not proof that no height could work.',
                         'Illustrative clearance is a display-study choice, not an operational safety margin.']}
    (OUT / 'results.json').write_text(json.dumps(output, indent=2) + '\n')
    (OUT / 'plot-traces.json').write_text(json.dumps(traces) + '\n')


if __name__ == '__main__':
    main()
