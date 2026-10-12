"""Pattern: Strategy. Tab and two-space indentation for a CLRS file."""

from dataclasses import dataclass

from clrs.errors import ONE_SPACE_MESSAGE
from clrs.errors import SPACE_MIX_MESSAGE
from clrs.errors import TAB_MIX_MESSAGE


@dataclass(frozen=True)
class LineMeasure:
    """Pattern: Value Object. The indent level and body of one source line."""

    level: int
    body: str
    width: int
    problem: str


class IndentStrategy:
    """Pattern: Strategy. Tab and two-space indentation for a CLRS file."""

    def __init__(self) -> None:
        self._unit = ""

    def unit(self) -> str:
        if self._unit == "\t":
            return "tab"
        if self._unit == "  ":
            return "spaces"
        return ""

    def measure(self, line: str) -> LineMeasure:
        if self._unit == "":
            return self._detect(line)
        return self._apply(line)

    def _detect(self, line: str) -> LineMeasure:
        if line.startswith("\t"):
            self._unit = "\t"
            return self._apply(line)
        if line.startswith("  "):
            self._unit = "  "
            return self._apply(line)
        if line.startswith(" "):
            return LineMeasure(0, line.lstrip(" "), 1, ONE_SPACE_MESSAGE)
        return LineMeasure(0, line, 0, "")

    def _apply(self, line: str) -> LineMeasure:
        body = line
        level = 0
        while body.startswith(self._unit):
            body = body[len(self._unit) :]
            level = level + 1
        width = len(line) - len(body)
        if body[:1] in " \t":
            return LineMeasure(0, body, width, self._mixed_message())
        return LineMeasure(level, body, width, "")

    def _mixed_message(self) -> str:
        if self._unit == "\t":
            return TAB_MIX_MESSAGE
        return SPACE_MIX_MESSAGE
