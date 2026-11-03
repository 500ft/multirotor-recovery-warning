"""Prepare the NanoBench replay figure from the executed development CSV.

No data acquisition or scoring. ``plot_table()`` writes the per-horizon means
that the figure shows to Data/figure-data/nanobench-baseline.csv, and
``caption()`` writes the words to a file beside the image; the report copies
the caption under the figure. Analysis/matlab/render_figures.m draws the PNG
and PDF from the plot table.
"""
import argparse
import csv
from pathlib import Path

import numpy as np

# One marker per model; the shape carries the distinction in every panel.
MODELS = {'cf21plus_firmware': {'label': '2.1+ curve', 'marker': 'o'},
          'thrust_upgrade_firmware': {'label': 'Thrust-upgrade curve', 'marker': 's'},
          'legacy_propellers_firmware': {'label': 'Legacy-propeller curve', 'marker': '^'}}
PERSISTENCE = {'label': 'Persistence (hold state)', 'marker': 'D'}
NAMES = [*MODELS, 'persistence']
METRICS = [('velocity', 'Velocity error [m/s]', 'world velocity'),
           ('body_rate', 'Body rate error [rad/s]', 'body angular rate')]
LETTERS = 'abcdef'

def summarize(rows):
    """Within-flight vector RMSE, then unweighted mean over flights."""
    horizons = sorted({float(r['horizon_s']) for r in rows if float(r['horizon_s']) > 0})
    values, flights = {}, set()
    for metric, _, _ in METRICS:
        for name in NAMES:
            series = []
            for horizon in horizons:
                selected = [r for r in rows if r['model'] == name and r['metric'] == metric
                            and float(r['horizon_s']) == horizon]
                per = sorted({r['flight'] for r in selected})
                flights.add(len(per))
                per_flight = [np.sqrt(sum(float(r['rmse'])**2 for r in selected
                                         if r['flight'] == flight)) for flight in per]
                series.append(np.mean(per_flight))
            values[metric, name] = np.array(series)
    return horizons, values, flights


def findings(horizons, values):
    """Sentences that hold for every plotted point, derived from the data."""
    out = []
    if all(np.all(values[m, 'persistence'] < values[m, n]) for m, _, _ in METRICS for n in MODELS):
        out.append('Persistence has the lowest error at every horizon for both quantities.')
    ends = {n: values['velocity', n][-1] for n in MODELS}
    if max(ends.values()) - min(ends.values()) < .05 * max(ends.values()):
        out.append(f'The three motor-curve velocity errors meet by {horizons[-1]:g} s.')
    worst = max(MODELS, key=lambda n: values['body_rate', n].max())
    if all(np.all(values['body_rate', worst] >= values['body_rate', n]) for n in MODELS):
        out.append(f'The {MODELS[worst]["label"].lower()} has the largest body rate error '
                   'at every horizon.')
    return out


def caption(rows) -> str:
    horizons, values, flights = summarize(rows)
    n_note = (f'{flights.pop()} development flights per point'
              if len(flights) == 1 else 'flight count varies by point; see the CSV')
    panels = ', '.join(f'({LETTERS[j]}) {MODELS[n]["label"]}' for j, n in enumerate(MODELS))
    rate = ', '.join(f'({LETTERS[3 + j]})' for j in range(len(MODELS)))
    return (
        'NanoBench development replay: open-loop rollout error of the documented motor '
        'models against the persistence comparator. Panels (a) to (c): mean world velocity '
        f'error [m/s] for {panels}. Panels {rate}: mean body angular rate error [rad/s] '
        'for the same models in the same order. Each panel repeats persistence (hold state, '
        'orange diamonds, dashed line) so the panels share one scale per row. Horizons '
        f'{", ".join(f"{h:g}" for h in horizons)} s; same starts for all models; '
        f'{n_note}; mean of within-flight vector RMSE with equal flight weighting; no '
        f'uncertainty interval. {" ".join(findings(horizons, values))} '
        'NanoBench observations collected by Ullah and Baca. Per-axis and per-flight '
        'values: Data/nanobench-baseline/development-errors.csv.'
    )


PLOT_FIELDS = ['panel', 'metric', 'model', 'label', 'marker', 'horizon_s', 'mean_error']


def plot_table(rows):
    """One row per plotted point: each model panel carries its curve and persistence."""
    horizons, values, _ = summarize(rows)
    out = []
    for i, (metric, _, _) in enumerate(METRICS):
        for j, name in enumerate(MODELS):
            for series, meta in ((name, MODELS[name]), ('persistence', PERSISTENCE)):
                for h, v in zip(horizons, values[metric, series]):
                    out.append({'panel': LETTERS[i * len(MODELS) + j], 'metric': metric,
                                'model': series, 'label': meta['label'],
                                'marker': meta['marker'], 'horizon_s': f'{h:g}',
                                'mean_error': repr(float(v))})
    return out


def read_rows(results: Path):
    with results.open() as f:
        return list(csv.DictReader(f))


def plot(results: Path, output: Path, caption_path: Path):
    rows = read_rows(results)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=PLOT_FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(plot_table(rows))
    caption_path.write_text(caption(rows) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path, help='plot table CSV')
    p.add_argument('--caption', type=Path, default=Path('Figures/nanobench-baseline.caption.md'))
    a = p.parse_args(); plot(a.results, a.output, a.caption)
