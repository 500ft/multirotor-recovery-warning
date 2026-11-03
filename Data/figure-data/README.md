# Plot data

Python writes these files; MATLAB draws the figures from them
([Analysis/matlab](../../Analysis/matlab/README.md)). They hold the plotted
values only. The results they come from stay in their own files, so a redraw
cannot change a result. Regenerate them instead of editing them.

| File | Written by | Drawn as |
| --- | --- | --- |
| `release_recovery_timeseries.csv`, `release_recovery_envelope.csv`, `release_recovery_figure.json` | `python -m Analysis.run_release_recovery` | `Figures/release_recovery_{timeseries,envelope}.png` |
| `survivable_set_{psafe,policy}{,_a2}.csv` | `python -m Analysis.run_survivable_set --figures-only` | `Figures/survivable_set_{psafe,policy}{,_a2}.png` |
| `nanobench-baseline.csv` | `python -m Analysis.plot_nanobench_baseline` | `Figures/nanobench-baseline.png` |
| `current-results-tables.json` | `python -m Analysis.export_results_tables` | `Figures/tables/*.png` in `Analysis/current-results.md` |

The QDrone2 traces are third-party observations and stay outside the repository
with the hash-pinned workbook; see `Analysis/matlab/README.md`.
