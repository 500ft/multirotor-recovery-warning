"""Sample exact physical states on one common video clock; no motion warping."""
from pathlib import Path
import json, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Analysis.recovery_video import CASES
SOURCE = ROOT / 'Data/recovery-video'
BUILD = ROOT / '.video-build'
BUILD.mkdir(exist_ok=True)
cfg = json.loads((SOURCE / 'settings.json').read_text())
keys = ['best', 'nominal', 'worst']
arrays = [np.load(SOURCE / f'{key}.npz') for key in keys]
duration = cfg['initial_hold_s'] + cfg['duration_s'] / cfg['playback_speed']
timeline = []
for frame in range(round(duration * cfg['fps']) + 1):
    t = min(cfg['duration_s'], max(0, frame/cfg['fps'] - cfg['initial_hold_s']) * cfg['playback_speed'])
    sample = {'t': t, 'indices': [], 'q': [], 'pos': [], 'phase': []}
    for key, a in zip(keys, arrays):
        j = min(len(a['t'])-1, round(t / cfg['dt_s']))
        sample['indices'].append(j)
        sample['q'].append(a['q'][j].tolist())
        sample['pos'].append((a['pos'][j] + [0, 0, CASES[key]().available_height_m]).tolist())
        sample['phase'].append(a['phase'][j].tolist())
    timeline.append(sample)
(BUILD / 'display.json').write_text(json.dumps({'fps': cfg['fps'], 'keys': keys, 'timeline': timeline}))
print(f'{len(timeline)} frames; positions and quaternions copied without amplification')
