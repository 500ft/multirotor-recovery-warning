function s = tex_escape(s)
%TEX_ESCAPE Escape plain text for the LaTeX interpreter and for table files.
s = char(s);
s = strrep(s, '\', '\textbackslash{}');
s = strrep(s, '%', '\%');
s = strrep(s, '&', '\&');
s = strrep(s, '_', '\_');
s = strrep(s, '#', '\#');
end
