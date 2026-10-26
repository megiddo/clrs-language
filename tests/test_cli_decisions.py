"""Command-line and printer decision logs only. These tests do not assert any printed text."""

import io
import logging
import unittest
from pathlib import Path

from clrs.cli import CompileCommand
from clrs.cli import RunCommand
from clrs.common.decisions import DecisionLog
from tests.paths import FIXTURES, SORTING

EXAMPLES = SORTING
KINDS = {"cli", "print"}


class CliDecisionLogTest(unittest.TestCase):
    def decisions(self, *argv: str) -> list[str]:
        command = RunCommand(io.StringIO(), io.StringIO(), DecisionLog())
        with self.assertLogs("clrs", level="INFO") as captured:
            command.execute(list(argv))
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        messages = [record.getMessage() for record in captured.records]
        return [m for m in messages if m.split()[0] in KINDS]

    def printing(self, driver: str) -> list[str]:
        return self.decisions("run", "--", driver)[1:]

    def test_usage_and_run(self) -> None:
        self.assertEqual(self.decisions("run"), ["cli usage"])
        self.assertEqual(self.decisions("run", "--", "1")[0], "cli run")

    def test_compile_records_compile_outcome(self) -> None:
        sort = str(EXAMPLES / "insertion-sort.clrs")
        command = CompileCommand(io.StringIO(), io.StringIO(), DecisionLog())
        with self.assertLogs("clrs", level="INFO") as captured:
            command.execute(["compile", sort])
        outcomes = [record.getMessage() for record in captured.records]
        self.assertIn("cli compile", outcomes)

    def test_compile_records_the_fault_outcome(self) -> None:
        missing = str(EXAMPLES / "missing.clrs")
        command = CompileCommand(io.StringIO(), io.StringIO(), DecisionLog())
        with self.assertLogs("clrs", level="INFO") as captured:
            command.execute(["compile", missing])
        outcomes = [record.getMessage() for record in captured.records]
        self.assertEqual([m for m in outcomes if m.startswith("cli ")], ["cli compile", "cli file"])

    def test_scalar_renderings(self) -> None:
        cases = {
            "1": ["print integer"],
            "True": ["print boolean"],
            "∞": ["print infinity"],
            "NIL": ["print nil"],
        }
        for driver, outcome in cases.items():
            self.assertEqual(self.printing(driver), outcome, driver)

    def test_array_renderings(self) -> None:
        self.assertEqual(self.printing("[]"), ["print array"])
        self.assertEqual(self.printing("[1,]"), ["print array", "print integer", "print single"])
        self.assertEqual(self.printing("[1, 2]"), ["print array", "print integer", "print integer"])

    def test_faults(self) -> None:
        sort = str(EXAMPLES / "insertion-sort.clrs")
        cases = {
            ("run", str(FIXTURES / "broken-for.clrs"), "--", "1"): "cli compile",
            ("run", sort, sort, "--", "1"): "cli link",
            ("run", "--", "⌊1/0⌋"): "cli runtime",
            ("run", str(EXAMPLES / "missing.clrs"), "--", "1"): "cli file",
        }
        for argv, outcome in cases.items():
            self.assertEqual(self.decisions(*argv)[-1], outcome, argv)


if __name__ == "__main__":
    unittest.main()
