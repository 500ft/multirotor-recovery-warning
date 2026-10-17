"""Plot the executed development CSV; no data acquisition or scoring.

The canvas shows only the stored per-horizon means. Everything in words is
written by ``caption()`` to a file beside the image and copied into the report
under it.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np

from Analysis import figure_style as fs

# One marker per model; the shape carries the distinction in every panel.
MODELS = {'cf21plus_firmware': {'label': '2.1+ curve', 'marker': 'o'},
          'thrust_upgrade_firmware': {'label': 'Thrust-upgrade curve', 'marker': 's'},
          'legacy_propellers_firmware': {'label': 'Legacy-propeller curve', 'marker': '^'}}
PERSISTENCE = {'label': 'Persistence (hold state)', 'marker': 'D'}
NAMES = [*MODELS, 'persistence']
METRICS = [('velocity', 'Velocity error [m/s]', 'world velocity'),
           ('body_rate', 'Body rate error [rad/s]', 'body angular rate')]
LETTERS = 'abcdef'

# Layout in inches: 178 mm wide like the other repo figures, two rows of three panels, legend above.
WIDTH, HEIGHT = 7.0, 4.4
MARGINS = {'left': .085, 'right': .99, 'top': .87, 'bottom': .11, 'wspace': .45, 'hspace': .42}


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
        'diamonds, dashed line) so the panels share one scale per row. Horizons '
        f'{", ".join(f"{h:g}" for h in horizons)} s; same starts for all models; '
        f'{n_note}; mean of within-flight vector RMSE with equal flight weighting; no '
        f'uncertainty interval. {" ".join(findings(horizons, values))} '
        'NanoBench observations collected by Ullah and Baca. Per-axis and per-flight '
        'values: Data/nanobench-baseline/development-errors.csv.'
    )


def figure(rows):
    horizons, values, _ = summarize(rows)
    fs.apply()
    fig, axes = plt.subplots(len(METRICS), len(MODELS), figsize=(WIDTH, HEIGHT))
    fig.subplots_adjust(**MARGINS)
    for i, (metric, label, _) in enumerate(METRICS):
        top = max(values[metric, n].max() for n in NAMES)
        for j, name in enumerate(MODELS):
            ax = axes[i, j]
            ax.plot(horizons, values[metric, 'persistence'], marker=PERSISTENCE['marker'],
                    ls=fs.DASHED, zorder=2, **fs.MARKER, lw=fs.LINE['lw'])
            ax.plot(horizons, values[metric, name], marker=MODELS[name]['marker'],
                    ls='-', zorder=3, **fs.MARKER, lw=fs.LINE['lw'])
            ax.set(xlim=(0, horizons[-1] * 1.12), ylim=(0, top * 1.15))
            ax.set_xticks(horizons, [f'{h:g}' for h in horizons])
            ax.tick_params(axis='x', labelbottom=i == len(METRICS) - 1, length=3)
            ax.tick_params(axis='y', labelleft=j == 0, length=3)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
            if j == 0:
                ax.set_ylabel(label)
            if i == len(METRICS) - 1:
                ax.set_xlabel('Open-loop horizon [s]')
            fs.letter(ax, f'({LETTERS[i * len(MODELS) + j]})')
    handles = [Line2D([], [], marker=m['marker'], ls='-', label=m['label'], **fs.MARKER,
                      lw=fs.LINE['lw']) for m in MODELS.values()]
    handles.append(Line2D([], [], marker=PERSISTENCE['marker'], ls=fs.DASHED,
                          label=PERSISTENCE['label'], **fs.MARKER, lw=fs.LINE['lw']))
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .995), ncol=len(handles),
               columnspacing=1.4, handletextpad=.5, borderaxespad=0)
    return fig


def read_rows(results: Path):
    with results.open() as f:
        return list(csv.DictReader(f))


def plot(results: Path, output: Path):
    rows = read_rows(results)
    fig = figure(rows)
    fs.save_audited(fig, output)
    plt.close(fig)
    output.with_suffix('.caption.md').write_text(caption(rows) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(); plot(a.results, a.output)
