"""The NanoBench replay figure shows only stored values, and its words live in the caption."""
import csv
import math
import unittest
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Text  # noqa: E402

from Analysis import figure_style as fs  # noqa: E402
from Analysis import plot_nanobench_baseline as plot  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / 'Data/nanobench-baseline/development-errors.csv'
CAPTION = ROOT / 'Figures/nanobench-baseline.caption.md'


def expected():
    """(metric, model) -> per-horizon means, recomputed here with the stdlib only."""
    axes = defaultdict(list)
    with CSV.open() as f:
        for r in csv.DictReader(f):
            if float(r['horizon_s']) > 0 and r['metric'] in ('velocity', 'body_rate'):
                axes[r['metric'], r['model'], float(r['horizon_s']), r['flight']].append(float(r['rmse']))
    out = defaultdict(dict)
    for (metric, model, horizon, _), rmse in axes.items():
        out[metric, model].setdefault(horizon, []).append(math.sqrt(sum(v * v for v in rmse)))
    return {k: [sum(v[h]) / len(v[h]) for h in sorted(v)] for k, v in out.items()}


class NanoBenchFigure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = plot.read_rows(CSV)
        cls.fig = plot.figure(cls.rows)

    @classmethod
    def tearDownClass(cls):
        plt.close(cls.fig)

    def test_lines_carry_stored_means(self):
        want = expected()
        panels = [(m, n) for m, _, _ in plot.METRICS for n in plot.MODELS]
        self.assertEqual(len(self.fig.axes), len(panels))
        for ax, (metric, model) in zip(self.fig.axes, panels):
            persistence, curve = ax.lines
            self.assertEqual(curve.get_marker(), plot.MODELS[model]['marker'])
            self.assertEqual(persistence.get_marker(), plot.PERSISTENCE['marker'])
            for line, name in ((curve, model), (persistence, 'persistence')):
                for got, ref in zip(line.get_ydata(), want[metric, name], strict=True):
                    self.assertAlmostEqual(got, ref, places=12)

    def test_canvas_holds_only_axes_text_letters_and_legend(self):
        printed = {t.get_text() for t in self.fig.findobj(Text) if t.get_visible() and t.get_text().strip()}
        allowed = {f'({c})' for c in plot.LETTERS} | {label for _, label, _ in plot.METRICS}
        allowed |= {'Open-loop horizon [s]'}
        allowed |= {t.get_text() for leg in self.fig.legends for t in leg.get_texts()}
        allowed |= {t.get_text() for ax in self.fig.axes for t in ax.get_xticklabels() + ax.get_yticklabels()}
        self.assertLessEqual(printed, allowed, printed - allowed)

    def test_nothing_printed_touches_anything(self):
        self.assertEqual(fs.audit(self.fig), [])

    def test_caption_matches_file_and_report(self):
        text = plot.caption(self.rows)
        self.assertEqual(text, CAPTION.read_text().strip())
        squash = lambda s: ' '.join(s.split())  # noqa: E731
        self.assertIn(squash(text), squash((ROOT / 'docs/nanobench-baseline.md').read_text()))
        self.assertIn('nanobench-baseline.caption.md', (ROOT / 'docs/data-and-figures.md').read_text())


if __name__ == '__main__':
    unittest.main()
