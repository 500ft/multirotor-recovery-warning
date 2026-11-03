# MATLAB figures and tables

MATLAB R2025b draws every data figure in `Figures/` and writes the calculated
tables of [current results](../current-results.md). Python does all the
computation and writes the plotted values to [`Data/figure-data/`](../../Data/figure-data/).
MATLAB reads only those files and the committed results JSON, so a redraw
cannot change a result.

## Regenerate

From the repository root:

```bash
# 1. Plot data and captions (Python). Only the first command runs a simulation (~90 s).
python -m Analysis.run_release_recovery
python -m Analysis.run_survivable_set --figures-only
python -m Analysis.plot_nanobench_baseline --results Data/nanobench-baseline/development-errors.csv --output Data/figure-data/nanobench-baseline.csv
python -m Analysis.plot_qdrone_response --cache /tmp/multirotor-qdrone-source --plot-data /tmp/multirotor-qdrone-source/qdrone-traces.csv --tables docs
python -m Analysis.export_results_tables

# 2. Figures (PNG at 300 dpi and vector PDF) and table fragments (MATLAB)
QDRONE_TRACES=/tmp/multirotor-qdrone-source/qdrone-traces.csv \
  matlab -batch "addpath('Analysis/matlab'); render_figures"

# 3. Typeset tables (tectonic or lualatex, plus poppler's pdftoppm)
python Analysis/matlab/typeset_tables.py Figures/tables
```

The QDrone2 command needs the hash-pinned source workbook in the cache folder;
[the QDrone2 report](../../docs/qdrone-response.md#reproduce) gives the fetch
command. The trace CSV stays outside the repository with the workbook.

## Files

| File | Draws or writes | Reads |
| --- | --- | --- |
| `render_figures.m` | Runs every job below, one `try`/`catch` each | |
| `make_release_timeseries.m` | `Figures/release_recovery_timeseries.{png,pdf}` | `release_recovery_timeseries.csv`, `release_recovery_figure.json` |
| `make_release_envelope.m` | `Figures/release_recovery_envelope.{png,pdf}` | `release_recovery_envelope.csv`, `release_recovery_figure.json`, `Data/release_recovery_results.json` |
| `make_survivable_psafe.m` | `Figures/survivable_set_psafe{,_a2}.{png,pdf}` | `survivable_set_psafe{,_a2}.csv` |
| `make_survivable_policy.m` | `Figures/survivable_set_policy{,_a2}.{png,pdf}` | `survivable_set_policy{,_a2}.csv` |
| `make_nanobench_baseline.m` | `Figures/nanobench-baseline.{png,pdf}` | `nanobench-baseline.csv` |
| `make_qdrone_response.m` | `Figures/qdrone-development-response.{png,pdf}` | trace CSV, `docs/qdrone-response.csv`, `Data/qdrone-response/results.json` |
| `make_results_tables.m` | `Figures/tables/*.tex` | `current-results-tables.json`, `Data/release_recovery_results.json`, `Data/monte_carlo_results.json` |
| `fig_style.m`, `export_pair.m`, `panel_letter.m`, `tex_escape.m` | Shared style and export | |

## Style

- LaTeX interpreter for all text, Computer Modern. Sizes: 9 pt axis labels,
  8 pt notes, 7 pt ticks, 10 pt bold panel letters set as left-aligned titles.
- MATLAB default colours: blue `[0 0.4470 0.7410]` first, orange
  `[0.8500 0.3250 0.0980]` second, ink `[0.15 0.15 0.15]` for text. The three
  parameter tiers need a third colour; the best tier uses MATLAB default colour 4
  (purple), because colour 3 (yellow) is too light for text.
- No titles on the canvas. The finding and the panel key live in the caption
  file next to each figure (`Figures/*.caption.md`), written by the Python step.
- Lines are labelled in their own colour. Filled and hollow markers carry
  status. Reference lines are grey and dotted, labelled once.
