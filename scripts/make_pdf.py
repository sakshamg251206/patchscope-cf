"""Build the arXiv-ready PDF from the Markdown paper, so the two cannot drift apart.

The Kaggle Writeup is authored in Markdown (`paper/KAGGLE_WRITEUP.md`). This script is the
only thing that produces `paper/patchscope_cf.pdf`, so every number in the PDF comes from
the same file `scripts/check_paper.py` validates against the result artifacts.

Requires pdflatex on PATH. Usage: python scripts/make_pdf.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PAPER = Path('paper/KAGGLE_WRITEUP.md')
TEX = Path('paper/patchscope_cf.tex')

PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=2.3cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{graphicx}
\graphicspath{{../}}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{caption}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\titleformat{\section}{\normalfont\large\bfseries}{\thesection}{0.6em}{}
\captionsetup{font=small,labelfont=bf}
\setlength{\parskip}{0.4em}
\setlength{\parindent}{0pt}
\emergencystretch=3em
\sloppy

\title{\textbf{@@TITLE@@}\\[0.3em]\large @@SUB@@}
\author{}
\date{November 2026}

\begin{document}
\maketitle
\vspace{-2.5em}
"""

SPECIALS = [('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('_', r'\_')]
SYMBOLS = [('−', '$-$'), ('×', r'$\times$'), ('⌊', r'$\lfloor$'), ('⌋', r'$\rfloor$'),
           ('Σ', r'$\Sigma$'), ('→', r'$\rightarrow$'), ('α', r'$\alpha$'),
           ('—', '---'), ('’', "'"), ('“', '``'), ('”', "''"), ('≤', r'$\leq$')]


def escape(text: str) -> str:
    """Escape TeX specials that are not already escaped."""
    for raw, escaped in SPECIALS:
        text = re.sub(r'(?<!\\)' + re.escape(raw), escaped.replace('\\', '\\\\'), text)
    for raw, escaped in SYMBOLS:
        text = text.replace(raw, escaped)
    return text


def breakable(code: str, every: int = 18) -> str:
    """Let a long unbroken token (a commit hash, a path) wrap instead of running off the page."""
    if ' ' in code or len(code) <= every * 1.5:
        return code
    return r'\allowbreak{}'.join(code[i:i + every] for i in range(0, len(code), every))


def inline(text: str) -> str:
    """Markdown inline markup to LaTeX. Verbatim spans are protected from escaping."""
    protected: list[str] = []

    def stash(value: str) -> str:
        protected.append(value)
        return f'\x00{len(protected) - 1}\x00'

    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  lambda m: stash(r'\href{' + m.group(2).replace('%', r'\%').replace('#', r'\#')
                                  + '}{' + escape(m.group(1)) + '}'), text)
    text = re.sub(r'`([^`]+)`',
                  lambda m: stash(r'\texttt{' + breakable(escape(m.group(1))) + '}'), text)
    text = escape(text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\\textit{\1}', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: protected[int(m.group(1))], text)


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip('|').split('|')]


def table(rows: list[str]) -> str:
    header = cells(rows[0])
    spec = 'l' + 'r' * (len(header) - 1)
    out = [r'\begin{center}\footnotesize\begin{tabular}{' + spec + '}', r'\toprule',
           ' & '.join(inline(h) for h in header) + r' \\', r'\midrule']
    out += [' & '.join(inline(c) for c in cells(row)) + r' \\' for row in rows[2:]]
    out += [r'\bottomrule', r'\end{tabular}\end{center}']
    return '\n'.join(out)


def convert(text: str) -> str:
    out: list[str] = []
    pending_table: list[str] = []
    in_list = False

    def flush_table() -> None:
        nonlocal pending_table
        if pending_table:
            out.append(table(pending_table))
            pending_table = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(r'\end{itemize}')
            in_list = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|'):
            close_list()
            pending_table.append(line)
            continue
        flush_table()

        image = re.match(r'!\[(.*?)\]\((.*?)\)', stripped)
        if image:
            close_list()
            path = image.group(2).replace('../', '')
            out.append(r'\begin{figure}[tb]\centering' '\n'
                       rf'\includegraphics[width=0.96\linewidth]{{{path}}}' '\n'
                       rf'\caption{{{inline(image.group(1))}}}' '\n' r'\end{figure}')
            continue

        bullet = re.match(r'^[-*]\s+(.*)', stripped)
        if bullet:
            if not in_list:
                out.append(r'\begin{itemize}\setlength{\itemsep}{2pt}')
                in_list = True
            out.append(r'\item ' + inline(bullet.group(1)))
            continue

        close_list()
        out.append(inline(line))
    close_list()
    flush_table()
    return '\n'.join(out)


def main() -> int:
    if shutil.which('pdflatex') is None:
        print('pdflatex not found on PATH; skipping PDF build')
        return 1
    markdown = PAPER.read_text()

    title = re.search(r'^# (.*)$', markdown, re.M).group(1)
    subtitle = re.search(r'^\*\*Subtitle:\*\*\s*(.*)$', markdown, re.M).group(1).rstrip('.')

    sections: dict[str, str] = {}
    for chunk in re.split(r'\n## ', markdown)[1:]:
        head, _, rest = chunk.partition('\n')
        sections[head.strip()] = rest.strip()

    document = [PREAMBLE.replace('@@TITLE@@', inline(title)).replace('@@SUB@@', inline(subtitle))]
    for name, text in sections.items():
        if name == 'References':
            items = [re.sub(r'^\d+\.\s*', '', line).strip()
                     for line in text.splitlines() if re.match(r'^\d+\.', line.strip())]
            document.append(r'\begin{thebibliography}{9}')
            document += [r'\bibitem{r%d} %s' % (i + 1, inline(item)) for i, item in enumerate(items)]
            document.append(r'\end{thebibliography}')
            continue
        if name == 'Abstract':
            document.append(r'\begin{abstract}' '\n' r'\noindent ' + convert(text) + '\n' r'\end{abstract}')
            continue
        heading = re.sub(r'^\d+\.\s*', '', name)
        document.append(rf'\section{{{inline(heading)}}}' '\n' + convert(text))
    document.append(r'\end{document}')
    TEX.write_text('\n\n'.join(document) + '\n')

    for _ in range(2):  # second pass resolves references and float placement
        result = subprocess.run(['pdflatex', '-interaction=nonstopmode', TEX.name],
                                cwd=TEX.parent, capture_output=True, text=True)
    pdf = TEX.with_suffix('.pdf')
    if not pdf.exists():
        print(result.stdout[-3000:])
        return 1
    for suffix in ('.aux', '.log', '.out'):
        TEX.with_suffix(suffix).unlink(missing_ok=True)
    print(f'wrote {pdf} ({pdf.stat().st_size // 1024} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
