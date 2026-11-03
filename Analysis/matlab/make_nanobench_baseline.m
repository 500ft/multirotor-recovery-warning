function make_nanobench_baseline(dataDir, outDir, S)
%MAKE_NANOBENCH_BASELINE Open-loop rollout error of three motor models against persistence.
%   Input: nanobench-baseline.csv (per-horizon means written by
%   python -m Analysis.plot_nanobench_baseline). Rows: velocity error, body-rate error.
%   Columns: one motor model each (blue, solid), with persistence repeated in every panel
%   (orange diamonds, dashed) so each row shares one scale.

opts = detectImportOptions(fullfile(dataDir, 'nanobench-baseline.csv'), 'TextType', 'string');
opts = setvartype(opts, {'panel', 'metric', 'model', 'label', 'marker'}, 'string');
T = readtable(fullfile(dataDir, 'nanobench-baseline.csv'), opts);
metrics = ["velocity", "body_rate"];
ylab = {'Velocity error (m/s)', 'Body-rate error (rad/s)'};
panels = unique(T.panel, 'stable');
H = unique(T.horizon_s)';
markers = containers.Map({'o', 's', '^', 'D'}, {'o', 's', '^', 'd'});

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 17.0 9.6]);
tl = tiledlayout(fig, 2, 3, 'TileSpacing', 'compact', 'Padding', 'compact');
for p = 1:numel(panels)
    ax = nexttile(tl); hold(ax, 'on');
    r = T(T.panel == panels(p), :);
    i = find(metrics == r.metric(1));
    top = max(T.mean_error(T.metric == r.metric(1)));
    per = r(r.model == "persistence", :);
    mdl = r(r.model ~= "persistence", :);
    plot(ax, per.horizon_s, per.mean_error, '--', 'Color', S.c.orange, 'LineWidth', 1.0);
    plot(ax, per.horizon_s, per.mean_error, markers(char(per.marker(1))), 'MarkerSize', 4, ...
        'Color', S.c.orange, 'MarkerFaceColor', S.c.orange, 'LineStyle', 'none');
    plot(ax, mdl.horizon_s, mdl.mean_error, '-', 'Color', S.c.blue, 'LineWidth', 1.3);
    plot(ax, mdl.horizon_s, mdl.mean_error, markers(char(mdl.marker(1))), 'MarkerSize', 4.5, ...
        'Color', S.c.blue, 'MarkerFaceColor', S.c.blue, 'LineStyle', 'none');
    set(ax, 'XLim', [0 H(end) * 1.12], 'YLim', [0 top * 1.15], 'XTick', H, ...
        'XTickLabel', compose('%g', H), 'Box', 'off', 'TickDir', 'out');
    if i == 1
        panel_letter(ax, char(panels(p)), S, char(tex_escape(mdl.label(1))));
    else
        panel_letter(ax, char(panels(p)), S);
    end
    if mdl(1, :).panel == panels(1) || mdl(1, :).panel == panels(4)
        ylabel(ax, ylab{i});
        % persistence labelled once per row, in its own colour
        text(ax, H(end), per.mean_error(end) + 0.06 * top, 'persistence', 'Color', S.c.orange, ...
            'FontSize', S.size.note, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'bottom');
    else
        ax.YTickLabel = {};
    end
    if i == 1, ax.XTickLabel = {}; else, xlabel(ax, 'Open-loop horizon (s)'); end
end
export_pair(fig, fullfile(outDir, 'nanobench-baseline'));
end
