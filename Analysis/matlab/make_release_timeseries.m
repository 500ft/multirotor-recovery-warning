function make_release_timeseries(dataDir, outDir, S)
%MAKE_RELEASE_TIMESERIES Four stacked tracks of the nominal-tier demo release.
%   Inputs: release_recovery_timeseries.csv (every fourth solver sample) and the
%   reference values in release_recovery_figure.json, both written by
%   python -m Analysis.run_release_recovery.

T = readtable(fullfile(dataDir, 'release_recovery_timeseries.csv'));
J = jsondecode(fileread(fullfile(dataDir, 'release_recovery_figure.json')));
M = J.timeseries;
c = S.tier.(M.tier);
off = M.motors_off_s;
tr = M.recovery_time_s;
tEnd = ceil(T.t_s(end));

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 17.0 14.5]);
tl = tiledlayout(fig, 4, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
tracks = {T.tilt_deg, 'Tilt $\theta$ ($^\circ$)';
          T.body_rate_rad_s, 'Body rate $|\omega|$ (rad/s)';
          T.height_change_m, 'Height change $\Delta z$ (m)';
          T.thrust_n, 'Thrust $T$ (N)'};
letters = 'abcd';
ax = gobjects(4, 1);
for k = 1:4
    ax(k) = nexttile(tl); hold(ax(k), 'on'); a = ax(k);
    y = tracks{k, 1};
    lim = [min(y) max(y)];
    if k == 3, lim(1) = -M.available_height_m; end
    if k == 4, lim(2) = M.max_thrust_n; end
    pad = 0.10 * diff(lim);
    lim = lim + [-pad pad];
    patch(a, [0 off off 0], lim([1 1 2 2]), S.c.stem, 'EdgeColor', 'none');
    if ~isempty(tr)
        plot(a, [tr tr], lim, '--', 'Color', c, 'LineWidth', 0.7);
    end
    plot(a, T.t_s, y, '-', 'Color', c, 'LineWidth', 1.3);
    set(a, 'YLim', lim, 'XLim', [0 tEnd], 'Box', 'off', 'Layer', 'top', 'TickDir', 'out');
    a.YAxis.TickLabelFormat = '$%g$';
    a.XAxis.TickLabelFormat = '$%g$';
    ylabel(a, tracks{k, 2});
    panel_letter(a, letters(k), S);
    if k < 4, a.XTickLabel = {}; end
end
linkaxes(ax, 'x');
xlabel(ax(4), 'Time after release $t$ (s)');

ref = {'LineStyle', ':', 'Color', S.c.grey, 'LineWidth', 0.8};
note = {'FontSize', S.size.note, 'Color', S.c.grey, 'HorizontalAlignment', 'right', ...
        'VerticalAlignment', 'bottom'};
yline(ax(1), M.upright_deg, ref{:});
text(ax(1), tEnd, M.upright_deg, sprintf('%g$^\\circ$ upright', M.upright_deg), note{:});
yline(ax(3), -M.available_height_m, ref{:});
text(ax(3), tEnd, -M.available_height_m, ...
    sprintf('ground, %g m below release', M.available_height_m), note{:});
yline(ax(4), M.max_thrust_n, ref{:});
text(ax(4), tEnd, M.max_thrust_n, sprintf('maximum %g N', M.max_thrust_n), ...
    note{1:4}, 'HorizontalAlignment', 'right', 'VerticalAlignment', 'top');
text(ax(3), off + 0.06, -0.55 * M.available_height_m, ...
    {'motors off', '(detect + spool)'}, 'FontSize', S.size.note, 'Color', S.c.grey, ...
    'VerticalAlignment', 'middle');
if ~isempty(tr)
    yl = ax(2).YLim;
    text(ax(2), tr + 0.06, yl(2) - 0.08 * diff(yl), sprintf('stabilized at %.2f s', tr), ...
        'FontSize', S.size.note, 'Color', c, 'VerticalAlignment', 'top');
end
export_pair(fig, fullfile(outDir, 'release_recovery_timeseries'));
end
