function make_survivable_psafe(dataDir, outDir, suffix, S)
%MAKE_SURVIVABLE_PSAFE Exact 95% lower bound on survival, 4 failure classes x 3 actions.
%   Input: survivable_set_psafe<suffix>.csv, written from the committed results JSON by
%   python -m Analysis.run_survivable_set --figures-only. One panel per (class, action),
%   cells over release height and tumble rate; outlined cells are primary cells.

stem = ['survivable_set_psafe' suffix];
opts = detectImportOptions(fullfile(dataDir, [stem '.csv']), 'TextType', 'string');
opts = setvartype(opts, {'panel', 'class', 'class_name', 'action', 'action_name', 'label'}, 'string');
T = readtable(fullfile(dataDir, [stem '.csv']), opts);

classes = unique(T.class, 'stable');
actions = unique(T.action, 'stable');
H = unique(T.release_height_m)';
W = unique(T.tumble_rate_rad_s)';
% white to a light MATLAB blue, so ink numbers stay legible on every cell
top = 0.45 * S.c.blue + 0.55 * [1 1 1];
cmap = [linspace(1, top(1), 256)' linspace(1, top(2), 256)' linspace(1, top(3), 256)'];

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 17.0 17.5]);
tl = tiledlayout(fig, numel(classes), numel(actions), 'TileSpacing', 'compact', 'Padding', 'compact');
for i = 1:numel(classes)
    for j = 1:numel(actions)
        ax = nexttile(tl); hold(ax, 'on');
        r = T(T.class == classes(i) & T.action == actions(j), :);
        G = nan(numel(W), numel(H));
        for k = 1:height(r)
            G(W == r.tumble_rate_rad_s(k), H == r.release_height_m(k)) = r.p_safe_95_lower(k);
        end
        imagesc(ax, 1:numel(H), 1:numel(W), G, [0 1]);
        colormap(ax, cmap);
        for k = 1:height(r)
            x = find(H == r.release_height_m(k)); y = find(W == r.tumble_rate_rad_s(k));
            text(ax, x, y, char(r.label(k)), 'HorizontalAlignment', 'center', ...
                'FontSize', S.size.note, 'Color', S.c.ink);
            if r.primary(k)
                rectangle(ax, 'Position', [x - 0.44, y - 0.42, 0.88, 0.84], ...
                    'EdgeColor', S.c.ink, 'LineWidth', 0.9);
            end
        end
        set(ax, 'XLim', [0.5 numel(H) + 0.5], 'YLim', [0.5 numel(W) + 0.5], 'YDir', 'normal', ...
            'XTick', 1:numel(H), 'XTickLabel', compose('%g', H), 'YTick', 1:numel(W), ...
            'YTickLabel', compose('%g', W), 'Box', 'off', 'Layer', 'top', 'TickLength', [0.02 0.02], 'TickDir', 'out');
        if i < numel(classes), ax.XTickLabel = {}; end
        if j > 1, ax.YTickLabel = {}; end
        if j == 1
            ylabel(ax, {char(tex_escape(r.class_name(1))), '$\omega_0$ (rad/s)'});
        end
        if i == 1
            panel_letter(ax, char(r.panel(1)), S, char(tex_escape(r.action_name(1))));
        else
            panel_letter(ax, char(r.panel(1)), S);
        end
    end
end
xlabel(tl, 'Release height $h$ (m)', 'Interpreter', 'latex', 'FontSize', S.size.label, ...
    'Color', S.c.ink);
cb = colorbar(ax, 'eastoutside');
cb.Layout.Tile = 'east';
cb.TickLabelInterpreter = 'latex';
cb.FontSize = S.size.tick;
cb.TickDirection = 'out';
cb.Label.Interpreter = 'latex';
cb.Label.String = 'Survival probability, exact 95\% lower bound';
cb.Label.FontSize = S.size.label;
cb.Ticks = 0:0.2:1;
cb.Box = 'off';
export_pair(fig, fullfile(outDir, stem));
end
