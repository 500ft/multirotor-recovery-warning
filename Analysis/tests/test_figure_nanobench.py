"""The NanoBench plot table carries only stored values, and its words live in the caption.

MATLAB draws the figure from Data/figure-data/nanobench-baseline.csv
(Analysis/matlab/render_figures.m); these tests pin that table to the error CSV.
"""
import csv
import math
import unittest
from collections import defaultdict
from pathlib import Path

from Analysis import plot_nanobench_baseline as plot

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / 'Data/nanobench-baseline/development-errors.csv'
TABLE = ROOT / 'Data/figure-data/nanobench-baseline.csv'
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
        cls.table = plot.plot_table(cls.rows)

    def test_points_carry_stored_means(self):
        want = expected()
        panels = [(m, n) for m, _, _ in plot.METRICS for n in plot.MODELS]
        for k, (metric, model) in enumerate(panels):
            letter = plot.LETTERS[k]
            for name in (model, 'persistence'):
                got = [float(r['mean_error']) for r in self.table
                       if r['panel'] == letter and r['model'] == name]
                for g, ref in zip(got, want[metric, name], strict=True):
                    self.assertAlmostEqual(g, ref, places=12)

    def test_committed_table_matches(self):
        with TABLE.open() as f:
            self.assertEqual(list(csv.DictReader(f)), self.table)

    def test_caption_matches_file_and_report(self):
        text = plot.caption(self.rows)
        self.assertEqual(text, CAPTION.read_text().strip())
        squash = lambda s: ' '.join(s.split())  # noqa: E731
        self.assertIn(squash(text), squash((ROOT / 'docs/nanobench-baseline.md').read_text()))
        self.assertIn('nanobench-baseline.caption.md', (ROOT / 'docs/data-and-figures.md').read_text())

    def test_rendered_figure_is_committed(self):
        for ext in ('png', 'pdf'):
            self.assertTrue((ROOT / f'Figures/nanobench-baseline.{ext}').is_file())


if __name__ == '__main__':
    unittest.main()
