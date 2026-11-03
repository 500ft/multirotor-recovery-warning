# QDrone2 visual inventory and reproduction

The active scientific figure is the QDrone2 development response.
[plot_qdrone_response.py](../Analysis/plot_qdrone_response.py) and the MATLAB
[renderer](../Analysis/matlab/make_qdrone_response.m) read the existing
[result](../Data/qdrone-response/results.json) and pinned source workbook;
[reproduction commands](qdrone-response.md#reproduce) separate rendering from
calculation. The numerical result remains the single source for response metrics.

## Inventory and treatment

| Active entry point | Visual or table | Treatment and reason |
| :--- | :--- | :--- |
| README and QDrone2 report | Development response figure | Redrawn as aligned time traces and paired response-error panels; PNG for GitHub and vector PDF for export |
| QDrone2 report and result index | Event metrics | Generated chronological Markdown/CSV views; units, aligned numeric columns, consistent display precision and explicit incomplete window |
| Bench acquisition, C06 | Component observability contract | Split into channel/claim, timing/uncertainty and unavailable-output tables; original qualifications remain pending |
| README and reading/figure guides | Navigation/source tables | Retained as text; these carry links and scope rather than quantitative comparisons |
| Current-results historical sections and NanoBench report | Prior replay and designed-aircraft figures/tables | Retained unchanged with their configuration labels; frozen results are outside this visual task |
| Safety/CAD and historical reports | Explanatory diagrams and release artifacts | Retained unchanged; no new physical readiness or release claim |

## Reference and design choices

The owner supplied the enclosure study's actual
[thermal figure generator](https://github.com/500ft/sensor-enclosure-thermal-design/blob/bad572fc0902437445a5446bb5bc43098cc6211f/analysis/thermal_bias.py)
and its steady/transient figures at that revision. Their local source manifest
hashes were verified before use. This renderer uses the reference's white
background, blue/green/purple series, explicit units, restrained grids and
visible evidence status. The stacked voltage and altitude traces have an
identical time domain, without a dual axis. Command direction uses triangle
orientation as well as color; the reference altitude uses a dashed line.

RMSE panels share one axis that starts at the data floor with labelled
non-zero ticks. The zero-based axis of the first redesign left most of each
panel empty (figure-style rule 3.2). Panel titles state only comparisons that
hold for every event, and the table keeps the absolute values. Their points are the same stored
complete events; the chronological table preserves detail and the incomplete
ending. No smoothing, fit, interval, thrust headroom or recovery boundary is
introduced. Voltage and demand/time confounding, the original MPC and the
single-recording scope remain visible.

The component table remains accessible Markdown. Missing values are explicit,
and unknown calibration or capacity is not replaced with a numerical guess.
The historical force channel is aggregate; it is not relabeled as per-rotor thrust.

## Numerical preservation and visual review

The figure refresh leaves the result, protocol and source manifest byte-identical.
The original result's source-code hash remains its calculation provenance; the
new renderer changes presentation only. Independent artist-array comparisons
check each plotted trace and each complete-event coordinate against its source.
CSV rows retain every stored event and exact numeric values; Markdown precision
is display rounding, without a new uncertainty claim.

The figure is inspected at GitHub reading width for labels, overlap, clipping,
line/marker distinction and axis interpretation. The previous figure remains
available at the [pre-redesign revision](https://github.com/500ft/multirotor-recovery-dynamics/blob/d20c5295d133d9bf26abb6aee52e510ca630d8f7/Figures/qdrone-development-response.png).
No NanoBench final files or additional recordings are opened for this work.

## MATLAB redraw

MATLAB R2025b now draws the figure in the repository's LaTeX style. Observed
altitude, voltage and up steps are MATLAB blue; down steps are orange; the
reference is grey and dashed. Panel titles moved to the
[caption file](../Figures/qdrone-development-response.caption.md). The plotted
values are unchanged: traces from the pinned workbook, RMSE points from the
stored events.
