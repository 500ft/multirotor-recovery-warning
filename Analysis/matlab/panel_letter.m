function panel_letter(ax, L, S, name)
%PANEL_LETTER Bold panel letter as a left-aligned axes title, optionally with a name.
%   The letter is the axes title, so tiledlayout reserves space for it and
%   exportgraphics does not crop it.
if nargin < 4 || isempty(name)
    str = ['\textbf{' L '}'];
else
    str = ['\textbf{' L '}\enspace{\fontsize{' num2str(S.size.label) '}{10}\selectfont ' name '}'];
end
title(ax, str, 'FontSize', S.size.letter, 'FontWeight', 'normal', 'Color', S.c.ink);
ax.TitleHorizontalAlignment = 'left';
end
