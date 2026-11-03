"""Prepare the stored QDrone2 development result for plotting without recalculating metrics.

``plot()`` writes the source time traces (time, reference, altitude, voltage) from the
hash-checked workbook to a CSV outside the repository; Analysis/matlab/render_figures.m
draws Figures/qdrone-development-response.{png,pdf} from that CSV and the stored events
in docs/qdrone-response.csv. ``caption()`` writes the words beside the figure.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTION = ROOT/'Figures/qdrone-development-response.caption.md'
TRACE_FIELDS = ['time_s', 'reference_m', 'altitude_m', 'voltage_v']


def write_traces(data, path):
    """Source samples only; the third-party workbook stays outside the repository."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(TRACE_FIELDS)
        writer.writerows([repr(float(v)) for v in row[:4]] for row in data)


def caption(result) -> str:
    complete = [e for e in result['events'] if e['status'] == 'complete']
    incomplete = [e for e in result['events'] if e['status'] != 'complete']
    rmse = {d: [e['rmse_m'] for e in complete if e['direction'] == d] for d in ('up', 'down')}
    split = bool(rmse['up'] and rmse['down']) and min(rmse['down']) > max(rmse['up'])
    found = ('Every down step has a higher RMSE than every up step, and the gap holds across '
             'the precommand voltage range.' if split else
             'Up and down step errors overlap.')
    return (
        f"QDrone2 tracked {result['complete_steps']} complete altitude steps during one "
        'recorded discharge. Development observations under the original MPC; no '
        f"recovery-failure labels. {result['complete_steps']} complete response windows; "
        f"{len(incomplete)} incomplete (grey dotted line). (a) Observed altitude [m] (blue) "
        'follows the recorded reference steps (grey dashed). (b) Battery voltage [V] declines '
        'across the recording and swings at each command. (c) and (d) '
        f"{result['protocol_horizon_s']:g} s altitude RMSE [m] of each complete step against "
        'command time [s] and precommand voltage [V]; up steps blue triangles, down steps '
        f'orange inverted triangles. {found} Repeated commands share one recording. Demand, '
        'voltage and elapsed time co-vary. Observations: Borbolla-Burillo et al., '
        'Zenodo 19464105, CC BY 4.0. Values: Data/qdrone-response/results.json and '
        'docs/qdrone-response.csv.'
    )


def plot(data, result, path):
    """Write the plotted traces to ``path`` with a .csv suffix, for the MATLAB renderer.

    Keeps the ``--figure`` option of Analysis.qdrone_response working; that command
    writes outside the checkout, so the caption is left to ``main()``.
    """
    write_traces(data, Path(path).with_suffix('.csv'))


def write_tables(result, output):
    """Display precision only; CSV keeps the stored floats and every event."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fields = ['step', 'direction', 'time_s', 'precommand_voltage_v',
              'bias_m', 'mae_m', 'rmse_m', 'status', 'reason']
    with (output/'qdrone-response.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: e.get(key, '') for key in fields} for e in result['events'])
    lines = ['# QDrone2 response table', '',
             'Generated from [results.json](../Data/qdrone-response/results.json).',
             '[Download CSV](qdrone-response.csv) for stored precision; display rounding is not measurement uncertainty.',
             'Rows follow command time. Missing metrics mean an incomplete window, never zero.', '',
             '| Step | Direction | Time [s] | Precommand [V] | Bias [m] | MAE [m] | RMSE [m] | Window |',
             '| ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |']
    for e in result['events']:
        value = lambda key, digits: f"{e[key]:.{digits}f}" if e.get(key) is not None else 'N/A'
        status = 'Complete' if e['status'] == 'complete' else 'Incomplete: ' + e['reason'].replace('_', ' ')
        lines.append(f"| {e['step']} | {e['direction'].capitalize()} | {value('time_s', 3)} | "
                     f"{value('precommand_voltage_v', 3)} | {value('bias_m', 4)} | {value('mae_m', 4)} | "
                     f"{value('rmse_m', 4)} | {status} |")
    lines += ['', 'Original MPC; one development discharge. Repeated steps do not identify independent packs.',
              'Observations: Borbolla-Burillo et al., [Zenodo 19464105](https://doi.org/10.5281/zenodo.19464105), CC BY 4.0.',
              'Table derived here. [Method and limits](qdrone-response.md).', '']
    (output/'qdrone-response-table.md').write_text('\n'.join(lines))


def main():
    from Analysis.qdrone_response import digest, read_recording
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--plot-data', type=Path, required=True,
                        help='trace CSV for the MATLAB renderer, outside the repository')
    parser.add_argument('--tables', type=Path, help='Output directory for Markdown and CSV views')
    args = parser.parse_args()
    record = ROOT/'Data/qdrone-response'
    result = json.loads((record/'results.json').read_text())
    sources = json.loads((record/'sources.json').read_text())
    protocol = json.loads((record/'protocol.json').read_text())
    for item in sources['files']:
        if digest(args.cache/item['name']) != item['sha256']:
            raise ValueError(f"input hash mismatch: {item['name']}")
    plot(read_recording(args.cache/protocol['selected_file']), result, args.plot_data)
    CAPTION.write_text(caption(result) + '\n')
    if args.tables:
        write_tables(result, args.tables)


if __name__ == '__main__':
    main()
