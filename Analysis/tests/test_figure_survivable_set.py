"""The survivable-set plot tables carry only stored values, and their words live in the captions.

MATLAB draws the figures from Data/figure-data/survivable_set_*.csv
(Analysis/matlab/render_figures.m); these tests pin those tables to the results JSON.
"""
import csv
import json
import unittest
from pathlib import Path

from Analysis import run_survivable_set as run
from Analysis import survivable_set as ss
from Analysis.failure_allocation import FAILURE_CLASSES

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {'a': '', 'a2': '_a2'}


def load(suffix):
    return json.loads((ROOT / f'Data/survivable_set_results{suffix}.json').read_text())


def committed(name):
    with (ROOT / 'Data/figure-data' / f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def as_text(rows):
    return [{k: str(v) for k, v in r.items()} for r in rows]


class PsafeFigure(unittest.TestCase):
    def test_plot_table_carries_stored_bounds(self):
        for variant, suffix in VARIANTS.items():
            rows = load(suffix)['exploratory']
            by_key = {(r['class'], r['cell'], r['action']): r['p_safe_95_lower'] for r in rows}
            table = run.psafe_table(rows)
            self.assertEqual(len(table), len(FAILURE_CLASSES) * len(ss.ACTIONS)
                             * len(run.PSAFE_H) * len(run.PSAFE_W))
            for r in table:
                cell = ss.Cell(r['release_height_m'], 0.0, r['tumble_rate_rad_s'], 0.11).label()
                self.assertEqual(r['p_safe_95_lower'], by_key[r['class'], cell, r['action']])
                self.assertEqual(r['label'], run._bound(r['p_safe_95_lower']))
            self.assertEqual(committed(f'survivable_set_psafe{suffix}'), as_text(table))

    def test_caption_matches_file(self):
        for variant, suffix in VARIANTS.items():
            text = run.psafe_caption(load(suffix)['exploratory'], variant)
            self.assertEqual(text, (ROOT / f'Figures/survivable_set_psafe{suffix}.caption.md')
                             .read_text().strip())


class PolicyFigure(unittest.TestCase):
    def test_plot_table_carries_stored_best_package_and_state(self):
        for variant, suffix in VARIANTS.items():
            policy = load(suffix)['policy']
            cells, rows = run._policy_rows(policy)
            table = run.policy_table(policy)
            self.assertEqual(len(table), len(rows))
            for t in table:
                r = rows[t['class'], t['cell']]
                self.assertEqual(t['best_p_safe_95_lower'], r['best_p_safe_95_lower'])
                self.assertEqual(t['kind'], run._policy_kind(r))
                self.assertEqual(t['marker'] != '', r['best_p_safe_95_lower'] > 0)
                self.assertEqual(t['row'], cells.index(t['cell']) + 1)
            self.assertEqual(committed(f'survivable_set_policy{suffix}'), as_text(table))

    def test_caption_matches_file_and_docs_link_captions(self):
        for variant, suffix in VARIANTS.items():
            text = run.policy_caption(load(suffix)['policy'], variant)
            self.assertEqual(text, (ROOT / f'Figures/survivable_set_policy{suffix}.caption.md')
                             .read_text().strip())
        self.assertIn('survivable_set_{psafe,policy}{,_a2}.caption.md',
                      (ROOT / 'docs/data-and-figures.md').read_text())

    def test_rendered_figures_are_committed(self):
        for name in ('psafe', 'policy'):
            for suffix in VARIANTS.values():
                for ext in ('png', 'pdf'):
                    self.assertTrue((ROOT / f'Figures/survivable_set_{name}{suffix}.{ext}').is_file())


if __name__ == '__main__':
    unittest.main()
