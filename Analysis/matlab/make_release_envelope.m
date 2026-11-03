function make_release_envelope(root, dataDir, outDir, S)
%MAKE_RELEASE_ENVELOPE Tumble-rate scan per parameter tier and the envelope edge.
%   Inputs: release_recovery_envelope.csv and release_recovery_figure.json (written by
%   python -m Analysis.run_release_recovery) and Data/release_recovery_results.json.
%   Panel a: failed rates (crosses) above the altitude lost on recovered releases.
%   Panel b: highest recovered rate before the first failure, log scale. Filled
%   marker = dynamic failure edge, hollow marker = no failure up to the gyro range.

T = readtable(fullfile(dataDir, 'release_recovery_envelope.csv'), 'TextType', 'string');
J = jsondecode(fileread(fullfile(dataDir, 'release_recovery_figure.json')));
M = J.envelope;
R = jsondecode(fileread(fullfile(root, 'Data', 'release_recovery_results.json')));
names = string(M.tiers(:))';
n = numel(names);
budget = M.available_height_m;
gyro = M.gyro_limit_rad_s;
step = M.rates_step_rad_s;
rates = unique(T.initial_rate_rad_s)';

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 17.0 10.0]);
tl = tiledlayout(fig, 5, 8, 'TileSpacing', 'compact', 'Padding', 'compact');

% ---- a, top strip: tumble rates with no recovery ------------------------------
strip = nexttile(tl, 1, [1 5]); hold(strip, 'on');
lost = nexttile(tl, 9, [4 5]); hold(lost, 'on');
for i = 1:n
    r = T(T.tier == names(i), :);
    c = S.tier.(char(names(i)));
    bad = r.recovered == 0;
    plot(strip, r.initial_rate_rad_s(bad), i * ones(sum(bad), 1), 'x', 'Color', c, ...
        'MarkerSize', 5, 'LineWidth', 1.0);
    y = r.altitude_lost_m; y(bad) = NaN;
    plot(lost, r.initial_rate_rad_s, y, '-o', 'Color', c, 'MarkerSize', 2.6, ...
        'MarkerFaceColor', c, 'LineWidth', 1.2);
    % direct label at the last recovered rate before the first failure,
    % or two thirds along the scan for a tier that never fails
    if any(bad)
        j = find(bad, 1) - 1;
        text(lost, r.initial_rate_rad_s(j) + 0.2, y(j) + 0.05, char(names(i)), 'Color', c, ...
            'FontSize', S.size.label, 'VerticalAlignment', 'bottom');
    else
        j = round(2 * numel(y) / 3);
        text(lost, r.initial_rate_rad_s(j) - 0.25, y(j) + 0.12, char(names(i)), 'Color', c, ...
            'FontSize', S.size.label, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'bottom');
    end
end
xl = [rates(1) - 0.4, rates(end) + 0.4];
set(strip, 'YLim', [0.4 n + 0.6], 'YDir', 'reverse', 'YTick', 1:n, 'YTickLabel', cellstr(names), ...
    'XLim', xl, 'XTickLabel', {}, 'TickLength', [0 0], 'Box', 'off', 'XGrid', 'on', ...
    'GridColor', S.c.stem, 'GridAlpha', 1);
strip.XAxis.Color = 'none';
strip.YAxis.Color = 'none';
strip.YAxis.TickLabelColor = S.c.ink;
panel_letter(strip, 'a', S);
yline(lost, budget, ':', 'Color', S.c.grey, 'LineWidth', 0.8);
text(lost, 4.25, budget, sprintf('%g m height budget', budget), 'FontSize', S.size.note, ...
    'Color', S.c.grey, 'VerticalAlignment', 'bottom');
set(lost, 'XLim', xl, 'YLim', [0 budget * 1.12], 'Box', 'off', 'TickDir', 'out');
linkaxes([strip lost], 'x');
xlabel(lost, 'Initial tumble rate $\omega_0$ (rad/s)');
ylabel(lost, {'Altitude lost when', 'recovered (m)'});

% ---- b: envelope edge per tier --------------------------------------------------
edge = nexttile(tl, 6, [5 3]); hold(edge, 'on');
for i = 1:n
    s = R.envelope_by_tier.(char(names(i)));
    c = S.tier.(char(names(i)));
    plot(edge, [0.3 70], [i i], '-', 'Color', S.c.stem, 'LineWidth', 0.5);
    rate = s.max_recoverable_rate_rad_s;
    gyroEdge = strcmp(s.envelope_edge, 'gyro_limit');
    if gyroEdge
        plot(edge, rate, i, 'o', 'MarkerSize', 6, 'LineWidth', 1.3, 'Color', c, ...
            'MarkerFaceColor', 'w');
        text(edge, rate / 1.25, i, {sprintf('%g rad/s', rate), 'no failure up to', 'the gyro range'}, ...
            'Color', c, 'FontSize', S.size.note, 'HorizontalAlignment', 'right', ...
            'VerticalAlignment', 'middle');
    else
        r = T(T.tier == names(i), :);
        firstFail = min(r.initial_rate_rad_s(r.recovered == 0));
        assert(abs(firstFail - (rate + step)) < 1e-9, 'scan and results JSON disagree on the edge');
        plot(edge, rate, i, 'o', 'MarkerSize', 6, 'Color', c, 'MarkerFaceColor', c);
        text(edge, rate, i + 0.18, {sprintf('%g rad/s', rate), sprintf('fails at %g rad/s', firstFail)}, ...
            'Color', c, 'FontSize', S.size.note, 'HorizontalAlignment', 'center', ...
            'VerticalAlignment', 'top');
    end
end
xline(edge, gyro, ':', 'Color', S.c.grey, 'LineWidth', 0.8);
text(edge, gyro / 1.15, n + 0.55, {'gyro range', sprintf('%.0f$^\\circ$/s', rad2deg(gyro))}, ...
    'FontSize', S.size.note, 'Color', S.c.grey, 'HorizontalAlignment', 'right', ...
    'VerticalAlignment', 'middle');
set(edge, 'XScale', 'log', 'XLim', [0.3 70], 'XTick', [1 3 10 30], ...
    'XTickLabel', {'1', '3', '10', '30'}, 'XMinorTick', 'off', 'YLim', [0.4 n + 0.9], ...
    'YDir', 'reverse', 'YTick', 1:n, 'YTickLabel', cellstr(names), 'Box', 'off', 'TickDir', 'out');
edge.YAxis.Color = 'none';
edge.YAxis.TickLabelColor = S.c.ink;
xlabel(edge, {'Highest rate recovered before', 'first failure (rad/s)'});
panel_letter(edge, 'b', S);
export_pair(fig, fullfile(outDir, 'release_recovery_envelope'));
end
