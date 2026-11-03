function make_survivable_policy(dataDir, outDir, suffix, S)
%MAKE_SURVIVABLE_POLICY Best design package per failure class and failure-state cell.
%   Input: survivable_set_policy<suffix>.csv, written from the committed results JSON by
%   python -m Analysis.run_survivable_set --figures-only. Marker shape and colour name the
%   best package (reallocation: blue circle, mechanism: orange square); filled = interval
%   clear of the others, hollow = within Monte Carlo uncertainty; no marker = every lower
%   bound 0. The number is the best lower bound. Outlined cells are primary cells.

stem = ['survivable_set_policy' suffix];
opts = detectImportOptions(fullfile(dataDir, [stem '.csv']), 'TextType', 'string');
opts = setvartype(opts, {'class', 'class_name', 'cell', 'best_action', 'marker', 'kind', 'label'}, 'string');
T = readtable(fullfile(dataDir, [stem '.csv']), opts);
T.marker(ismissing(T.marker)) = "";
nr = max(T.row); nc = max(T.column);
colour = struct('o', S.c.blue, 's', S.c.orange, 'x', S.c.ink);

fig = figure('Visible', 'off', 'Units', 'centimeters', 'Position', [2 2 15.5 19.5]);
ax = axes(fig); hold(ax, 'on');
for k = 1:height(T)
    x = T.column(k); y = T.row(k);
    m = char(T.marker(k));
    if ~isempty(m)
        c = colour.(m);
        face = 'w'; if T.kind(k) == "clear", face = c; end
        plot(ax, x - 0.2, y, m, 'MarkerSize', 5, 'LineWidth', 1.0, 'MarkerEdgeColor', c, ...
            'MarkerFaceColor', face);
    end
    text(ax, x + 0.12, y, char(T.label(k)), 'HorizontalAlignment', 'center', ...
        'FontSize', S.size.note, 'Color', S.c.ink);
    if T.primary(k)
        rectangle(ax, 'Position', [x - 0.42, y - 0.4, 0.84, 0.8], 'EdgeColor', S.c.ink, ...
            'LineWidth', 0.8);
    end
end
% rules between release heights
rows = sortrows(unique(T(:, {'row', 'release_height_m'}), 'rows'), 'row');
for k = 2:height(rows)
    if rows.release_height_m(k) ~= rows.release_height_m(k - 1)
        plot(ax, [0.5 nc + 0.5], (k - 0.5) * [1 1], '-', 'Color', S.c.grey, 'LineWidth', 0.5);
    end
end
for j = 1:nc
    nm = char(T.class_name(find(T.column == j, 1)));
    cut = regexp(nm, ' (?=rotors? out)| (?=\(60)', 'once');
    if isempty(cut), lines = {nm}; else, lines = {nm(1:cut - 1), nm(cut + 1:end)}; end
    text(ax, j, 0.3, cellfun(@tex_escape, lines, 'UniformOutput', false), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom', ...
        'FontSize', S.size.label, 'Color', S.c.ink, 'Clipping', 'off');
end
ticks = strings(nr, 1);
num = @(v) strrep(sprintf('%g', v), '-', '$-$');
for i = 1:nr
    r = T(find(T.row == i, 1), :);
    ticks(i) = strjoin({num(r.release_height_m), num(r.vertical_speed_m_s), ...
        num(r.tumble_rate_rad_s), num(r.delay_s)}, ', ');
end
set(ax, 'XLim', [0.5 nc + 0.5], 'YLim', [0.5 nr + 0.5], 'YDir', 'reverse', ...
    'XTick', [], 'YTick', 1:nr, 'YTickLabel', cellstr(ticks), 'TickLength', [0 0], 'Box', 'off');
ax.XAxis.Color = 'none';
ax.YAxis.Color = 'none'; ax.YAxis.TickLabelColor = S.c.ink;
ax.Position = [0.31 0.095 0.66 0.83];
ylabel(ax, ['Height $h$ (m), vertical speed $v_z$ (m/s), tumble rate $\omega_0$ (rad/s), ' ...
    'delay $t_d$ (s)'], 'Color', S.c.ink);

% marker key below the matrix, drawn with the same markers (two rows)
key = {'o', S.c.blue, true, 'reallocation', 0.55, nr + 1.05
       's', S.c.orange, true, 'mechanism', 1.75, nr + 1.05
       'o', S.c.ink, false, 'hollow: within uncertainty of another package', 0.55, nr + 1.75};
for k = 1:size(key, 1)
    face = 'w'; if key{k, 3}, face = key{k, 2}; end
    plot(ax, key{k, 5}, key{k, 6}, key{k, 1}, 'MarkerSize', 5, 'LineWidth', 1.0, ...
        'MarkerEdgeColor', key{k, 2}, 'MarkerFaceColor', face, 'Clipping', 'off');
    text(ax, key{k, 5} + 0.12, key{k, 6}, key{k, 4}, 'FontSize', S.size.note, 'Color', S.c.ink, ...
        'Clipping', 'off');
end
rectangle(ax, 'Position', [2.95, nr + 1.05 - 0.22, 0.2, 0.44], 'EdgeColor', S.c.ink, ...
    'LineWidth', 0.8, 'Clipping', 'off');
text(ax, 3.22, nr + 1.05, 'primary cell', 'FontSize', S.size.note, 'Color', S.c.ink, 'Clipping', 'off');
export_pair(fig, fullfile(outDir, stem));
end
