function make_qdrone_response(root, tracesCsv, outDir, S)
%MAKE_QDRONE_RESPONSE QDrone2 altitude and voltage traces with the stored step errors.
%   Inputs: the trace CSV written by python -m Analysis.plot_qdrone_response (time,
%   reference, altitude and voltage from the hash-checked source workbook; kept outside
%   the repository) and the stored events in docs/qdrone-response.csv plus the horizon in
%   Data/qdrone-response/results.json. No metric is recalculated here.

assert(isfile(tracesCsv), ['QDrone2 trace CSV not found: ' tracesCsv ...
    '. Run python -m Analysis.plot_qdrone_response --cache <cache> --plot-data <csv> first.']);
D = readmatrix(tracesCsv, 'NumHeaderLines', 1);
t = D(:, 1); ref = D(:, 2); alt = D(:, 3); volt = D(:, 4);
opts = detectImportOptions(fullfile(root, 'docs', 'qdrone-response.csv'), 'TextType', 'string');
opts = setvartype(opts, {'direction', 'status', 'reason'}, 'string');
E = readtable(fullfile(root, 'docs', 'qdrone-response.csv'), opts);
R = jsondecode(fileread(fullfile(root, 'Data', 'qdrone-response', 'results.json')));
done = E(E.status == "complete", :);
cut = E(E.status ~= "complete", :);
up = done(done.direction == "up", :);
dn = done(done.direction == "down", :);

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 17.0 15.5]);
tl = tiledlayout(fig, 7, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

% ---- a: altitude --------------------------------------------------------------
a = nexttile(tl, 1, [2 2]); hold(a, 'on');
stairs(a, t, ref, '--', 'Color', S.c.grey, 'LineWidth', 0.8);
plot(a, t, alt, '-', 'Color', S.c.blue, 'LineWidth', 0.8);
for k = 1:height(cut)
    xline(a, cut.time_s(k), ':', 'Color', S.c.grey, 'LineWidth', 0.9);
end
set(a, 'XLim', [t(1) t(end)], 'Box', 'off', 'TickDir', 'out', 'XTickLabel', {}, 'YGrid', 'on', ...
    'GridColor', S.c.stem, 'GridAlpha', 1);
ylabel(a, 'Altitude $z$ (m)');
panel_letter(a, 'a', S);
yl = a.YLim;
a.YLim = [yl(1), yl(2) + 0.20 * diff(yl)];
text(a, t(end), a.YLim(2), 'observed', 'Color', S.c.blue, 'FontSize', S.size.note, ...
    'HorizontalAlignment', 'right', 'VerticalAlignment', 'top');
text(a, t(end) - 0.09 * (t(end) - t(1)), a.YLim(2), 'reference (dashed)', 'Color', S.c.grey, ...
    'FontSize', S.size.note, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'top');

% ---- b: voltage ---------------------------------------------------------------
b = nexttile(tl, 5, [2 2]); hold(b, 'on');
plot(b, t, volt, '-', 'Color', S.c.blue, 'LineWidth', 0.5);
for k = 1:height(cut)
    xline(b, cut.time_s(k), ':', 'Color', S.c.grey, 'LineWidth', 0.9);
end
set(b, 'XLim', [t(1) t(end)], 'Box', 'off', 'TickDir', 'out', 'YGrid', 'on', 'GridColor', S.c.stem, 'GridAlpha', 1);
ylabel(b, 'Voltage $V$ (V)');
xlabel(b, 'Recorded time $t$ (s)');
panel_letter(b, 'b', S);
linkaxes([a b], 'x');
if height(cut) > 0
    text(b, cut.time_s(1), b.YLim(2), 'incomplete window ', 'FontSize', S.size.note, ...
        'Color', S.c.grey, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'top');
end

% ---- c, d: stored RMSE per complete step ------------------------------------------
vals = done.rmse_m;
lo = floor((min(vals) - 0.004) * 100) / 100;
hi = ceil((max(vals) + 0.004) * 100) / 100;
c = nexttile(tl, 9, [3 1]); hold(c, 'on');
d = nexttile(tl, 10, [3 1]); hold(d, 'on');
for ax = [c d]
    if ax == c, key = 'time_s'; else, key = 'precommand_voltage_v'; end
    plot(ax, up.(key), up.rmse_m, '^', 'MarkerSize', 4.5, 'Color', S.c.blue, ...
        'MarkerFaceColor', S.c.blue, 'LineStyle', 'none');
    plot(ax, dn.(key), dn.rmse_m, 'v', 'MarkerSize', 4.5, 'Color', S.c.orange, ...
        'MarkerFaceColor', S.c.orange, 'LineStyle', 'none');
    set(ax, 'YLim', [lo hi], 'YTick', round(linspace(lo, hi, 3), 3), 'Box', 'off', 'TickDir', 'out', ...
        'YGrid', 'on', 'GridColor', S.c.stem, 'GridAlpha', 1);
end
c.XLim = [t(1) t(end)];
xlabel(c, 'Command time (s)');
ylabel(c, sprintf('%g s altitude RMSE (m)', R.protocol_horizon_s));
xlabel(d, 'Precommand voltage $V$ (V)');
d.YTickLabel = {};
xr = d.XLim;
d.XLim = [xr(1), xr(2) + 0.18 * diff(xr)];
text(d, d.XLim(2), mean(dn.rmse_m), 'down', 'Color', S.c.orange, 'FontSize', S.size.label, ...
    'HorizontalAlignment', 'right', 'VerticalAlignment', 'middle');
text(d, d.XLim(2), mean(up.rmse_m), 'up', 'Color', S.c.blue, 'FontSize', S.size.label, ...
    'HorizontalAlignment', 'right', 'VerticalAlignment', 'middle');
panel_letter(c, 'c', S);
panel_letter(d, 'd', S);
export_pair(fig, fullfile(outDir, 'qdrone-development-response'));
end
