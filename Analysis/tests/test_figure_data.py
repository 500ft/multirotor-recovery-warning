"""Plot data, captions and table sources for the MATLAB figures agree with the stored results.

None of these tests runs a simulation; they read the committed files.
"""
import csv
import json
import unittest
from pathlib import Path

from Analysis import export_results_tables as tables
from Analysis import plot_qdrone_response as qdrone
from Analysis import run_release_recovery as rr

ROOT = Path(__file__).resolve().parents[2]
PLOT = ROOT / 'Data/figure-data'
RESULTS = json.loads((ROOT / 'Data/release_recovery_results.json').read_text())
META = json.loads((PLOT / 'release_recovery_figure.json').read_text())
TABLES = ('mass_budget', 'recovery_envelope_first_order', 'guard_check', 'classifier_bounds',
          'closed_loop_envelope', 'monte_carlo_dispersion', 'cg_offset_budget', 'mixer_authority')


class ReleaseRecoveryData(unittest.TestCase):
    def test_timeseries_matches_demo_case(self):
        ts, demo = META['timeseries'], RESULTS['demo_case']
        self.assertEqual(ts['recovery_time_s'], demo['recovery_time_s'])
        self.assertEqual(ts['altitude_lost_m'], demo['altitude_lost_m'])
        with (PLOT / 'release_recovery_timeseries.csv').open() as f:
            rows = list(csv.DictReader(f))
        lost = -min(float(r['height_change_m']) for r in rows)
        # every fourth solver sample is stored, so the plotted minimum may sit just above it
        self.assertLessEqual(lost, demo['altitude_lost_m'] + 1e-9)
        self.assertGreater(lost, demo['altitude_lost_m'] - 1e-3)
        self.assertAlmostEqual(max(float(r['thrust_n']) for r in rows), demo['peak_thrust_n'])

    def test_envelope_scan_matches_edges(self):
        rows = rr.read_envelope_csv()
        step = META['envelope']['rates_step_rad_s']
        for tier, s in RESULTS['envelope_by_tier'].items():
            failed = [float(r['initial_rate_rad_s']) for r in rows
                      if r['tier'] == tier and r['recovered'] == '0']
            if s['envelope_edge'] == 'failure':
                self.assertAlmostEqual(min(failed) - step, s['max_recoverable_rate_rad_s'])
            else:
                self.assertEqual(failed, [])

    def test_captions_match_files(self):
        self.assertEqual(rr.timeseries_caption(META['timeseries']),
                         (ROOT / 'Figures/release_recovery_timeseries.caption.md').read_text().strip())
        self.assertEqual(rr.envelope_caption(rr.read_envelope_csv(), META['envelope'],
                                             RESULTS['envelope_by_tier']),
                         (ROOT / 'Figures/release_recovery_envelope.caption.md').read_text().strip())


class QDroneCaption(unittest.TestCase):
    def test_caption_matches_file(self):
        result = json.loads((ROOT / 'Data/qdrone-response/results.json').read_text())
        self.assertEqual(qdrone.caption(result), qdrone.CAPTION.read_text().strip())


class ResultTables(unittest.TestCase):
    def test_export_matches_analysis_scripts(self):
        stored = json.loads(tables.OUTPUT.read_text())
        self.assertEqual(stored, json.loads(json.dumps(tables.tables())))

    def test_typeset_tables_are_committed_and_shown(self):
        text = (ROOT / 'Analysis/current-results.md').read_text()
        for name in TABLES:
            for ext in ('tex', 'pdf', 'png'):
                self.assertTrue((ROOT / f'Figures/tables/{name}.{ext}').is_file(), name)
            self.assertIn(f'../Figures/tables/{name}.png', text)


class RenderedFigures(unittest.TestCase):
    def test_png_and_pdf_are_committed(self):
        for name in ('release_recovery_timeseries', 'release_recovery_envelope',
                     'qdrone-development-response'):
            for ext in ('png', 'pdf'):
                self.assertTrue((ROOT / f'Figures/{name}.{ext}').is_file(), name)


if __name__ == '__main__':
    unittest.main()
