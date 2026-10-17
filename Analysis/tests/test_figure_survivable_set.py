"""The survivable-set figures show only stored values, and their words live in the captions."""
import json
import unittest
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Text  # noqa: E402

from Analysis import figure_style as fs  # noqa: E402
from Analysis import run_survivable_set as run  # noqa: E402
from Analysis import survivable_set as ss  # noqa: E402
from Analysis.failure_allocation import FAILURE_CLASSES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {'a': '', 'a2': '_a2'}


def load(suffix):
    return json.loads((ROOT / f'Data/survivable_set_results{suffix}.json').read_text())


def printed(fig):
    return {t.get_text() for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()}


def ticks(fig):
    return {t.get_text() for ax in fig.axes for t in ax.get_xticklabels() + ax.get_yticklabels()}


class PsafeFigure(unittest.TestCase):
    def test_fields_carry_stored_bounds_and_canvas_is_clean(self):
        for variant, suffix in VARIANTS.items():
            rows = load(suffix)['exploratory']
            by_key = {(r['class'], r['cell'], r['action']): r['p_safe_95_lower'] for r in rows}
            fig = run.make_psafe_figure(rows)
            try:
                panels = [(c, a) for c in sorted(FAILURE_CLASSES) for a in ss.ACTIONS]
                for ax, (cls, action) in zip(fig.axes, panels):
                    grid = ax.images[0].get_array()
                    for a, h in enumerate(run.PSAFE_H):
                        for b, w in enumerate(run.PSAFE_W):
                            self.assertEqual(grid[b, a],
                                             by_key[cls, ss.Cell(h, 0.0, w, 0.11).label(), action])
                allowed = {f'({c})' for c in run.LETTERS} | ticks(fig)
                allowed |= {'Release height [m]', 'Tumble rate at failure [rad/s]',
                            'Survival probability, exact 95% lower bound'}
                allowed |= {t.get_text() for leg in fig.legends for t in leg.get_texts()}
                allowed |= {run._bound(v) for v in by_key.values()}
                self.assertLessEqual(printed(fig), allowed, printed(fig) - allowed)
                self.assertEqual(fs.audit(fig), [])
            finally:
                plt.close(fig)

    def test_caption_matches_file(self):
        for variant, suffix in VARIANTS.items():
            text = run.psafe_caption(load(suffix)['exploratory'], variant)
            self.assertEqual(text, (ROOT / f'Figures/survivable_set_psafe{suffix}.caption.md')
                             .read_text().strip())


class PolicyFigure(unittest.TestCase):
    def test_markers_carry_stored_best_package_and_state(self):
        for variant, suffix in VARIANTS.items():
            policy = load(suffix)['policy']
            fig = run.make_policy_figure(policy)
            try:
                cells, rows = run._policy_rows(policy)
                want = [(j + .3, i + .5, run.PACKAGE[r['best_action']]['marker'],
                         fs.FILL[run._policy_kind(r) == 'clear'])
                        for j, cls in enumerate(sorted(FAILURE_CLASSES))
                        for i, cell in enumerate(cells)
                        for r in [rows[cls, cell]] if r['best_p_safe_95_lower'] > 0]
                ax = fig.axes[0]
                got = [(line.get_xdata()[0], line.get_ydata()[0], line.get_marker(),
                        line.get_markerfacecolor()) for line in ax.lines if len(line.get_xdata()) == 1]
                self.assertEqual(got, want)
                numbers = sorted(t.get_text() for t in ax.texts)
                self.assertEqual(numbers, sorted(run._bound(r['best_p_safe_95_lower'])
                                                 for r in rows.values()))
                allowed = ticks(fig) | set(numbers)
                allowed.add('Height [m], vertical speed [m/s], tumble rate [rad/s], delay [s]')
                allowed |= {t.get_text() for leg in fig.legends for t in leg.get_texts()}
                self.assertLessEqual(printed(fig), allowed, printed(fig) - allowed)
                self.assertEqual(fs.audit(fig), [])
            finally:
                plt.close(fig)

    def test_caption_matches_file_and_docs_link_captions(self):
        for variant, suffix in VARIANTS.items():
            text = run.policy_caption(load(suffix)['policy'], variant)
            self.assertEqual(text, (ROOT / f'Figures/survivable_set_policy{suffix}.caption.md')
                             .read_text().strip())
        self.assertIn('survivable_set_{psafe,policy}{,_a2}.caption.md',
                      (ROOT / 'docs/data-and-figures.md').read_text())


if __name__ == '__main__':
    unittest.main()
