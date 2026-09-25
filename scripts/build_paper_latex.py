#!/usr/bin/env python3
"""Convert the current English DOCX manuscript into an arXiv LaTeX draft."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = REPO_ROOT / "paper"
DOCX_PATH = PAPER_DIR / "composable_privacy_preserving_deck_reconstruction.docx"
TEX_PATH = PAPER_DIR / "composable_privacy_preserving_deck_reconstruction.tex"
FIGURE_DIR = PAPER_DIR / "figures"


LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
}

MATH_SUBSCRIPTS = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "₊": "+",
    "₋": "-",
    "₍": "(",
    "₎": ")",
    "ₙ": "n",
    "ₚ": "p",
    "ₓ": "x",
    "ₖ": "k",
    "ᵢ": "i",
    "ⱼ": "j",
}

MATH_SYMBOLS = {
    "Σ": r"\sum ",
    "∈": r"\in ",
    "ε": r"\epsilon ",
    "χ": r"\chi ",
    "λ": r"\lambda ",
    "≤": r"\le ",
    "≥": r"\ge ",
    "−": "-",
}


def latex_escape(value: str) -> str:
    escaped = "".join(LATEX_REPLACEMENTS.get(char, char) for char in value)
    # U+2032 is a prime in mathematical prose.  Keep it as a text superscript
    # so ordinary paragraphs never inherit unicode-math's active math behavior.
    return escaped.replace("′", r"\textsuperscript{*}")


def citation_latex(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        keys: list[str] = []
        for part in match.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            if "\u2013" in part:
                start_text, end_text = part.split("\u2013", 1)
                start, end = int(start_text), int(end_text)
                keys.extend(f"ref{number}" for number in range(start, end + 1))
            else:
                keys.append(f"ref{int(part)}")
        return rf"\cite{{{','.join(keys)}}}"

    return re.sub(r"\[(\d+(?:\s*[,\u2013]\s*\d+)*)\]", replace, value)


def break_hex(value: str) -> str:
    chunks = [value[:2]]
    rest = value[2:]
    chunks.extend(rest[index : index + 8] for index in range(0, len(rest), 8))
    return r"\texttt{" + r"\allowbreak{}".join(chunks) + "}"


def text_latex(value: str) -> str:
    """Escape text while making URLs, paths, filenames, and hex strings breakable."""
    protected: list[tuple[str, str]] = []

    def protect(token: str, rendering: str) -> str:
        key = f"\x00FORMAT{len(protected)}\x00"
        protected.append((key, rendering))
        return key

    def protect_url(match: re.Match[str]) -> str:
        token = match.group(0)
        punctuation = ""
        while token and token[-1] in ".,;)":
            punctuation = token[-1] + punctuation
            token = token[:-1]
        return protect(token, rf"\url{{{token}}}") + punctuation

    def protect_path(match: re.Match[str]) -> str:
        token = match.group(0)
        punctuation = ""
        while token and token[-1] in ".,;)":
            punctuation = token[-1] + punctuation
            token = token[:-1]
        return protect(token, rf"\path{{{token}}}") + punctuation

    value = re.sub(r"https?://[^\s]+", protect_url, value)
    value = re.sub(
        r"(?<![A-Za-z0-9])0x[0-9A-Fa-f]{24,}",
        lambda match: protect(match.group(0), break_hex(match.group(0))),
        value,
    )
    value = re.sub(
        r"(?<![A-Za-z0-9_])(?:paper|scripts|\.repro)(?:/[A-Za-z0-9_.-]+)+",
        protect_path,
        value,
    )
    value = re.sub(
        r"(?<![A-Za-z0-9_])[A-Za-z0-9.-]{12,}(?:_[A-Za-z0-9.-]+)+(?![A-Za-z0-9_])",
        protect_path,
        value,
    )

    escaped = citation_latex(latex_escape(value))
    for key, rendering in protected:
        escaped = escaped.replace(key, rendering)
    return escaped


def iter_blocks(document: DocumentObject) -> Iterable[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def paragraph_image(paragraph: Paragraph) -> str | None:
    blips = paragraph._p.xpath(".//a:blip")
    if not blips:
        return None
    relationship_id = blips[0].get(qn("r:embed"))
    if not relationship_id:
        return None
    image_part = paragraph.part.related_parts[relationship_id]
    digest = hashlib.sha256(image_part.blob).hexdigest()
    for source in sorted(FIGURE_DIR.glob("*.png")):
        if hashlib.sha256(source.read_bytes()).hexdigest() == digest:
            return f"figures/{source.name}"
    return None


def strip_number_prefix(text: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", text)


def caption_text(text: str, kind: "table" | "figure") -> str:
    pattern = r"^TABLE\s+[IVXLC]+\.?\s*" if kind == "table" else r"^Figure\s+\d+\.?\s*"
    return re.sub(pattern, "", text, flags=re.IGNORECASE)


def table_latex(table: Table, caption: str | None) -> str:
    rows = [[text_latex(cell.text.strip()) for cell in row.cells] for row in table.rows]
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    rows = [row + [""] * (column_count - len(row)) for row in rows]
    font_size = r"\footnotesize" if column_count >= 3 else r"\small"
    spec = " ".join([r">{\RaggedRight}X"] * column_count)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        font_size,
    ]
    if caption:
        lines.append(rf"\caption{{{text_latex(caption)}}}")
    lines.extend([
        r"\begin{tabularx}{\textwidth}{" + spec + "}",
        r"\toprule",
        " & ".join(rows[0]) + r" \\",
        r"\midrule",
    ])
    for row in rows[1:]:
        lines.append(" & ".join(row) + r" \\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
        "",
    ])
    return "\n".join(lines)


def heading_latex(text: str, level: int) -> str:
    clean = strip_number_prefix(text)
    if level == 1:
        return rf"\section{{{latex_escape(clean)}}}"
    if level == 2:
        starred = bool(re.match(r"^(Theorem\s+\d+|Simulator and hybrids)", clean))
        command = "subsection*" if starred else "subsection"
        return rf"\{command}{{{latex_escape(clean)}}}"
    if level == 3:
        return rf"\subsubsection{{{latex_escape(clean)}}}"
    return rf"\paragraph{{{latex_escape(clean)}}}"


def math_body(value: str) -> str:
    output: list[str] = []
    subscript_run: list[str] = []

    def flush_subscript() -> None:
        if subscript_run:
            output.append("_{" + "".join(subscript_run) + "}")
            subscript_run.clear()

    index = 0
    while index < len(value):
        char = value[index]
        if char in MATH_SUBSCRIPTS:
            subscript_run.append(MATH_SUBSCRIPTS[char])
            index += 1
            continue
        flush_subscript()
        if char == "B" and index + 1 < len(value) and value[index + 1] == "\u0303":
            output.append(r"\tilde{B}")
            index += 2
            continue
        if char == "′":
            output.append(r"^{\prime}")
            index += 1
            continue
        output.append(MATH_SYMBOLS.get(char, char))
        index += 1
    flush_subscript()

    body = "".join(output)
    body = re.sub(
        r"\b(Enc|Dec|sk|pk)\b",
        lambda match: rf"\mathrm{{{match.group(1)}}}",
        body,
    )
    body = re.sub(
        r"\b(and|if|for)\b",
        lambda match: rf"\text{{{match.group(1)}}}",
        body,
    )
    return body


def equation_latex(text: str) -> str:
    if text.startswith("./"):
        rendered = r"\\ ".join(
            rf"\texttt{{{latex_escape(line.strip())}}}" for line in text.splitlines() if line.strip()
        )
        return rf"\begin{{displaymath}}{rendered}\end{{displaymath}}"
    return rf"\begin{{displaymath}}{math_body(text)}\end{{displaymath}}"


def document_metadata(document: DocumentObject) -> dict[str, str]:
    values = [paragraph.text.strip() for paragraph in document.paragraphs[:7]]
    return {
        "title": values[0],
        "subtitle": values[1],
        "date": values[2],
        "author": values[3],
        "contact": values[4],
        "repository": values[5],
        "license": values[6],
    }


def build_preamble(metadata: dict[str, str]) -> str:
    preamble = r"""% !TeX program = xelatex
\documentclass[11pt]{article}

\usepackage{geometry}
\geometry{letterpaper,margin=1in}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{ragged2e}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{fontspec}
\usepackage{unicode-math}
\usepackage[hidelinks]{hyperref}
\usepackage{newunicodechar}
\usepackage{xurl}
\usepackage{textcomp}
\newunicodechar{₀}{\textsubscript{0}}
\newunicodechar{₁}{\textsubscript{1}}
\newunicodechar{₂}{\textsubscript{2}}
\newunicodechar{₃}{\textsubscript{3}}
\newunicodechar{₄}{\textsubscript{4}}
\newunicodechar{₅}{\textsubscript{5}}
\newunicodechar{₆}{\textsubscript{6}}
\newunicodechar{₇}{\textsubscript{7}}
\newunicodechar{₈}{\textsubscript{8}}
\newunicodechar{₉}{\textsubscript{9}}
\newunicodechar{₊}{\textsubscript{+}}
\newunicodechar{₋}{\textsubscript{-}}
\newunicodechar{₍}{\textsubscript{(}}
\newunicodechar{₎}{\textsubscript{)}}
\newunicodechar{ₙ}{\textsubscript{n}}
\newunicodechar{ₚ}{\textsubscript{p}}
\newunicodechar{ₓ}{\textsubscript{x}}
\newunicodechar{ₖ}{\textsubscript{k}}
\newunicodechar{ᵢ}{\textsubscript{i}}
\newunicodechar{ⱼ}{\textsubscript{j}}
\newunicodechar{′}{\textsuperscript{*}}
\newunicodechar{ε}{\ensuremath{\epsilon}}
\newunicodechar{χ}{\ensuremath{\chi}}
\newunicodechar{λ}{\ensuremath{\lambda}}
\newunicodechar{∈}{\ensuremath{\in}}
\newunicodechar{≤}{\ensuremath{\le}}
\newunicodechar{≥}{\ensuremath{\ge}}
\newunicodechar{Σ}{\ensuremath{\Sigma}}
\newunicodechar{−}{\ensuremath{-}}

\emergencystretch=3em

\renewcommand{\arraystretch}{1.16}
\setlength{\tabcolsep}{4pt}
\captionsetup{font=small,labelfont=bf}
\hypersetup{
  pdftitle={@@TITLE@@},
  pdfauthor={@@AUTHOR@@},
  pdfsubject={Cryptography preprint prepared for arXiv},
  pdfkeywords={Mental Poker, zero knowledge, non-interactive zero knowledge, formal verification}
}

\begin{document}

\title{\textbf{@@TITLE@@}\\\large @@SUBTITLE@@}
\author{@@AUTHOR@@\\\small @@CONTACT@@}
\date{@@DATE@@}
\maketitle
\thispagestyle{empty}

\begin{center}
\small @@REPOSITORY@@\\
\small @@LICENSE@@
\end{center}

\vspace{0.5em}
"""
    replacements = {
        "@@TITLE@@": latex_escape(metadata["title"]),
        "@@SUBTITLE@@": latex_escape(metadata["subtitle"]),
        "@@AUTHOR@@": latex_escape(metadata["author"]),
        "@@CONTACT@@": latex_escape(metadata["contact"]),
        "@@DATE@@": latex_escape(metadata["date"]),
        "@@REPOSITORY@@": latex_escape(metadata["repository"]),
        "@@LICENSE@@": latex_escape(metadata["license"]),
    }
    for marker, value in replacements.items():
        preamble = preamble.replace(marker, value)
    return preamble


def convert() -> None:
    from docx import Document

    document = Document(DOCX_PATH)
    output = [build_preamble(document_metadata(document))]
    list_mode: str | None = None
    in_abstract = False
    in_references = False
    pending_table_caption: str | None = None
    pending_figure_image: str | None = None
    reference_index = 0
    reached_abstract = False

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            output.append(rf"\end{{{list_mode}}}")
            list_mode = None

    for block in iter_blocks(document):
        if isinstance(block, Table):
            close_list()
            output.append(table_latex(block, pending_table_caption))
            pending_table_caption = None
            continue

        text = block.text.strip()
        style = block.style.name
        image = paragraph_image(block)

        if not reached_abstract:
            if style.startswith("Heading") and text == "Abstract":
                reached_abstract = True
            else:
                continue

        if in_references and style.startswith("Normal") and text:
            reference_index += 1
            text = re.sub(r"^\[\d+\]\s*", "", text)
            output.append(rf"\bibitem{{ref{reference_index}}} {latex_escape(text)}")
            continue

        if image:
            close_list()
            pending_figure_image = image
            continue

        if style.startswith("Heading"):
            close_list()
            level = int(style.rsplit(" ", 1)[-1])
            if in_abstract:
                output.append(r"\end{abstract}")
                output.append("")
                in_abstract = False
            if text == "Abstract":
                output.append(r"\begin{abstract}")
                in_abstract = True
            elif text == "References":
                output.append(r"\begin{thebibliography}{99}")
                in_references = True
            else:
                output.append(heading_latex(text, level))
            output.append("")
            continue

        if style == "Equation" and text:
            close_list()
            output.append(equation_latex(text))
            output.append("")
            continue

        if style.startswith("Caption") and text:
            close_list()
            if pending_figure_image:
                caption = caption_text(text, "figure")
                output.extend([
                    r"\begin{figure}[htbp]",
                    r"\centering",
                    rf"\includegraphics[width=0.88\textwidth]{{{pending_figure_image}}}",
                    rf"\caption{{{latex_escape(caption)}}}",
                    r"\end{figure}",
                    "",
                ])
                pending_figure_image = None
            else:
                pending_table_caption = caption_text(text, "table")
            continue

        if style.startswith("List"):
            mode = "itemize" if style == "List Bullet" else "enumerate"
            if list_mode != mode:
                close_list()
                output.append(rf"\begin{{{mode}}}")
                list_mode = mode
            output.append(rf"\item {text_latex(text)}")
            continue

        if not text:
            continue

        close_list()
        if in_abstract and text.startswith("Keywords."):
            output.append(r"\end{abstract}")
            output.append("")
            in_abstract = False
            keywords = text.removeprefix("Keywords.").strip()
            output.append(rf"\noindent\textbf{{Keywords.}} {latex_escape(keywords)}")
            output.append("")
        else:
            output.append(text_latex(text))
            output.append("")

    close_list()
    if in_abstract:
        output.append(r"\end{abstract}")
    if in_references:
        output.append(r"\end{thebibliography}")
    output.extend([
        "",
        r"\end{document}",
        "",
    ])

    manuscript = "\n".join(output)
    validate(manuscript)
    TEX_PATH.write_text(manuscript, encoding="utf-8")
    print(TEX_PATH)


def validate(manuscript: str) -> None:
    begin_counts: dict[str, int] = {}
    end_counts: dict[str, int] = {}
    for match in re.finditer(r"\\begin\{([^}]+)\}", manuscript):
        environment = match.group(1)
        begin_counts[environment] = begin_counts.get(environment, 0) + 1
    for match in re.finditer(r"\\end\{([^}]+)\}", manuscript):
        environment = match.group(1)
        end_counts[environment] = end_counts.get(environment, 0) + 1
    if begin_counts != end_counts:
        raise RuntimeError(f"LaTeX environments are unbalanced: {begin_counts=} {end_counts=}")

    expected = {
        "table": 12,
        "tabularx": 12,
        "figure": 4,
        "displaymath": 12,
    }
    for environment, count in expected.items():
        actual = begin_counts.get(environment, 0)
        if actual != count:
            raise RuntimeError(f"expected {count} {environment} environments, generated {actual}")

    bibitems = len(re.findall(r"^\\bibitem\{ref\d+\}", manuscript, flags=re.MULTILINE))
    if bibitems != 49:
        raise RuntimeError(f"expected 49 bibliography items, generated {bibitems}")
    if "@@" in manuscript:
        raise RuntimeError("unresolved LaTeX preamble marker remains")
    for image in re.findall(r"\\includegraphics\[[^]]+\]\{([^}]+)\}", manuscript):
        if not (PAPER_DIR / image).is_file():
            raise RuntimeError(f"referenced figure is missing: {image}")


if __name__ == "__main__":
    convert()
