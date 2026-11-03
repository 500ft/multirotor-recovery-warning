"""Typeset the MATLAB-written table fragments as PDF and 300-dpi PNG.

Usage, from the repo root:  python Analysis/matlab/typeset_tables.py [Figures/tables]

Each <name>.tex fragment written by make_results_tables.m is wrapped in a standalone
page (booktabs, siunitx, Latin Modern through fontspec) and compiled with tectonic,
or with lualatex when tectonic is missing. pdftoppm (poppler) writes <name>.png.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PAGE = r"""\documentclass[border=6pt]{standalone}
\usepackage{fontspec}
\usepackage{booktabs}
\usepackage{siunitx}
\usepackage{xcolor}
\sisetup{group-separator={,}}
\begin{document}
\input{fragment.tex}
\end{document}
"""


def compile_page(work: Path) -> None:
    if shutil.which("tectonic"):
        cmd = ["tectonic", "--keep-logs", "table.tex"]
    elif shutil.which("lualatex"):
        cmd = ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "table.tex"]
    else:
        raise SystemExit("needs tectonic or lualatex on PATH")
    subprocess.run(cmd, cwd=work, check=True, capture_output=True)


def main(folder: Path) -> None:
    for frag in sorted(folder.glob("*.tex")):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shutil.copy(frag, work / "fragment.tex")
            (work / "table.tex").write_text(PAGE)
            compile_page(work)
            shutil.copy(work / "table.pdf", frag.with_suffix(".pdf"))
        stem = frag.with_suffix("")
        subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile",
                        str(frag.with_suffix(".pdf")), str(stem)], check=True)
        print(f"[written] {stem}.pdf, {stem}.png")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Figures/tables"))
