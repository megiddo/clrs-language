"""Find transcription mistakes that make a .clrs file illegal.

This checks structure only. A procedure that runs the wrong algorithm
but follows the block rules produces no diagnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

COMMENT_GLYPH = "\u25b7"
BACKTICK = "`"

HEADER_RE = re.compile(
    r"^(?:for|while|if|else|datatype)\b"
    r"|^(?:[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*:?\s*$"
    r"|^(?:[A-Za-z_][A-Za-z0-9_]*)\s*\[[^\]]*\]\s*:?\s*$"
)
FOR_RE = re.compile(r"^for\b")
FOR_BOUND_RE = re.compile(
    r"^for\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:←|<-)\s+\S.*\s+(?:to|downto)\s+\S"
)

BACKTICK_MESSAGE = (
    "Backtick is not a CLRS token. Comments start with ▷ (type |>). "
    "Ceiling brackets are |^ and ^| with a caret, not a backtick."
)
FOR_MESSAGE = 'A for loop needs "to" or "downto" and an end expression.'


@dataclass(frozen=True)
class Diagnostic:
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    message: str

    def to_json(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "endLine": self.end_line,
            "endColumn": self.end_column,
            "message": self.message,
        }


@dataclass(frozen=True)
class _OpenLine:
    level: int
    code: str
    is_header: bool


def lint_path(path: Path) -> list[Diagnostic]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [_diagnostic(str(path), 1, 1, 2, str(exc))]
    return lint_text(text, str(path))


def lint_text(text: str, filename: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    unit: str | None = None
    previous: _OpenLine | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        level, body, unit, indent_error = _measure_indent(line, unit)
        if indent_error is not None:
            start, end = _content_span(line)
            diagnostics.append(_diagnostic(filename, line_number, start, end, indent_error))
            continue
        code, comment_only = _code_of(body)
        diagnostics.extend(_backtick_diagnostics(filename, line, line_number, code))
        if comment_only or code == "":
            continue
        diagnostics.extend(
            _structure_diagnostics(filename, line, line_number, level, code, previous)
        )
        previous = _OpenLine(level, code, _is_header(code))

    return diagnostics


def _structure_diagnostics(
    filename: str,
    line: str,
    line_number: int,
    level: int,
    code: str,
    previous: _OpenLine | None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    start, end = _content_span(line)
    opened_under = _indent_problem(level, previous)
    if opened_under is not None:
        diagnostics.append(_diagnostic(filename, line_number, start, end, opened_under))
    if FOR_RE.match(code) and not FOR_BOUND_RE.match(code):
        diagnostics.append(_diagnostic(filename, line_number, start, end, FOR_MESSAGE))
    return diagnostics


def _indent_problem(level: int, previous: _OpenLine | None) -> str | None:
    previous_level = 0 if previous is None else previous.level
    if level <= previous_level:
        return None
    if previous is None:
        return "This line is indented, and nothing above it opens a block."
    if level > previous.level + 1:
        return "Indent increased by more than one level."
    if previous.is_header:
        return None
    shown = previous.code if len(previous.code) <= 80 else previous.code[:77] + "..."
    return (
        f'Indented under "{shown}", which does not open a block. '
        "Blocks open after for, while, if, else, datatype, a procedure, or a method."
    )


def _backtick_diagnostics(
    filename: str, line: str, line_number: int, code: str
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    indent_width = len(line) - len(line.lstrip(" \t"))
    start_at = 0
    while True:
        at = code.find(BACKTICK, start_at)
        if at == -1:
            return diagnostics
        column = indent_width + at + 1
        diagnostics.append(
            _diagnostic(filename, line_number, column, column + 1, BACKTICK_MESSAGE)
        )
        start_at = at + 1


def _is_header(code: str) -> bool:
    return HEADER_RE.match(code) is not None


def _code_of(body: str) -> tuple[str, bool]:
    comment_at = _comment_at(body)
    if comment_at == 0:
        return "", True
    if comment_at is None:
        return body.rstrip(), False
    return body[:comment_at].rstrip(), False


def _comment_at(body: str) -> int | None:
    positions = [body.find(marker) for marker in (COMMENT_GLYPH, "|>")]
    found = [position for position in positions if position != -1]
    if not found:
        return None
    return min(found)


def _content_span(line: str) -> tuple[int, int]:
    start = 0
    while start < len(line) and line[start] in " \t":
        start += 1
    if start == len(line):
        start = 0
    return start + 1, len(line) + 1


def _measure_indent(
    line: str, unit: str | None
) -> tuple[int, str, str | None, str | None]:
    if unit is None:
        return _detect_unit(line)
    level, index = _consume_unit(line, unit)
    body = line[index:]
    if body[:1] in " \t":
        return 0, body, unit, _mixed_indent_message(unit)
    return level, body, unit, None


def _detect_unit(line: str) -> tuple[int, str, str | None, str | None]:
    if line.startswith("\t"):
        return _measure_indent(line, "\t")
    if line.startswith("  "):
        return _measure_indent(line, "  ")
    if line[:1] == " ":
        return 0, line.lstrip(" "), "  ", "Indentation must be a tab or two spaces."
    return 0, line, None, None


def _consume_unit(line: str, unit: str) -> tuple[int, int]:
    level = 0
    index = 0
    while line.startswith(unit, index):
        level += 1
        index += len(unit)
    return level, index


def _mixed_indent_message(unit: str) -> str:
    if unit == "\t":
        return "This file indents with tabs. This line uses spaces."
    return "This file indents with two spaces. This line uses a tab or an odd number of spaces."


def _diagnostic(
    filename: str, line: int, column: int, end_column: int, message: str
) -> Diagnostic:
    return Diagnostic(filename, line, column, line, end_column, message)
