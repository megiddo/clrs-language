"""Decision logs only. These tests do not assert any parse result."""

import contextlib
import logging
import unittest
from pathlib import Path

from clrs import CompileError
from clrs import parse_driver
from clrs import parse_module

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class DecisionLogTest(unittest.TestCase):
    def decisions(self, parse: object, source: str) -> list[str]:
        with self.assertLogs("clrs", level="INFO") as captured:
            with contextlib.suppress(CompileError):
                parse(source)  # type: ignore[operator]
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        return [record.getMessage() for record in captured.records]

    def driver(self, source: str) -> list[str]:
        return self.decisions(parse_driver, source)

    def module(self, source: str) -> list[str]:
        return self.decisions(parse_module, source)

    def test_parse_kind(self) -> None:
        self.assertEqual(self.driver("1"), ["parse driver"])
        self.assertEqual(self.module("Module M\n"), ["parse module"])

    def test_indent_unit_is_logged_once(self) -> None:
        tab = self.module((EXAMPLES / "insertion-sort.clrs").read_text())
        self.assertEqual(tab.count("indent tab"), 1)
        self.assertNotIn("indent spaces", tab)
        spaces = self.module((EXAMPLES / "bubblesort.clrs").read_text())
        self.assertEqual(spaces.count("indent spaces"), 1)
        self.assertNotIn("indent tab", spaces)

    def test_comment(self) -> None:
        self.assertEqual(self.driver("1 ▷ one"), ["parse driver", "comment keep"])
        self.assertIn("comment keep", self.module((EXAMPLES / "linear-search.clrs").read_text()))

    def test_array(self) -> None:
        self.assertEqual(self.driver("[5]"), ["parse driver", "array allocate"])
        self.assertEqual(self.driver("[5,]"), ["parse driver", "array literal"])
        self.assertEqual(self.driver("[]"), ["parse driver", "array literal"])

    def test_bracket(self) -> None:
        self.assertEqual(self.driver("left[A, 1]"), ["parse driver", "bracket call"])
        self.assertEqual(self.driver("contains[A]"), ["parse driver", "bracket attribute"])
        self.assertEqual(
            self.driver("A ← [1]; A[1]"),
            ["parse driver", "array allocate", "bracket index"],
        )

    def test_floor(self) -> None:
        self.assertEqual(self.driver("⌊7/2⌋"), ["parse driver", "floor division"])

    def test_for_direction(self) -> None:
        up = self.module((EXAMPLES / "insertion-sort.clrs").read_text())
        self.assertIn("for up", up)
        down = self.module((EXAMPLES / "build-max-heap.clrs").read_text())
        self.assertIn("for down", down)
        self.assertNotIn("for up", down)

    def test_rejections(self) -> None:
        cases = [
            (self.driver, "a or b", "reject or"),
            (self.driver, "a < b < c", "reject chain"),
            (self.driver, "⌈a/2⌉", "reject ceiling"),
            (self.driver, "⌊a⌋", "reject floor"),
            (self.driver, "a / 2", "reject slash"),
            (self.driver, "length ← 1; 1", "reject length"),
            (self.driver, "F(a) ← 1; 1", "reject target"),
            (self.module, "Module M\nP(length)\n\treturn 1\n", "reject length"),
            (self.module, (EXAMPLES / "linear-search.clrs").read_text(), "reject for"),
            (self.module, "Module M\nP()\n\tfor i ← 1\n\t\tF(i)\n", "reject for"),
            (self.module, "Module M\nP()\n\t\tx ← 1\n", "reject indent"),
            (self.module, "Module M\nP()\n x ← 1\n", "reject indent"),
            (self.module, "Module M\nP()\n\tx ← 1\n\t\ty ← 1\n", "reject indent"),
            (self.module, "Module M\ndatatype H extends Array:\n\tlength ← 0\n", "reject length"),
        ]
        for parse, source, outcome in cases:
            with self.subTest(source=source):
                self.assertEqual(parse(source)[-1], outcome)


if __name__ == "__main__":
    unittest.main()
