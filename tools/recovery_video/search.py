"""Re-execute every recorded candidate; keep outcome selection visible."""
from pathlib import Path
from dataclasses import replace
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Analysis.recovery_video import simulate, metrics
from Analysis.sim_release_recovery import worst_params


def main():
    record = json.loads((ROOT / 'Data/recovery-video/scenario-search.json').read_text())
    output = []
    for search in record['searches']:
        rows = []
        for candidate in search['candidates']:
            cfg = {**search['settings'],
                   'gyro_filter_tau_s': candidate.get('gyro_filter_tau_s', 0.)}
            p = replace(worst_params(), max_thrust_n=candidate.get('thrust_n', worst_params().max_thrust_n))
            a, hit = simulate(p, cfg, lag_multiplier=candidate['lag_multiplier'])
            result = metrics(a, hit, cfg, p)
            result.update({key: candidate[key] for key in ['gyro_filter_tau_s', 'thrust_n', 'lag_multiplier']
                           if key in candidate})
            peaks = np.flatnonzero((np.diff(a['tilt'])[:-1] > 0) & (np.diff(a['tilt'])[1:] < 0)) + 1
            result['tilt_peaks'] = [{'t': float(a['t'][j]), 'deg': float(np.degrees(a['tilt'][j]))}
                                    for j in peaks if a['t'][j] > .8]
            rows.append(result)
            print(result, flush=True)
        output.append({'settings': search['settings'], 'candidates': rows})
    destination = ROOT / '.video-build/scenario-search-rerun.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
