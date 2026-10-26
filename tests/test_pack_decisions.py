"""Packed-file decision logs only. These tests do not assert any program result or printed text."""

import contextlib
import io
import logging
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from clrs import Engine
from clrs import LinkError
from clrs import LoadError
from clrs import load_program
from clrs.cli import PackCommand
from clrs.cli import RunCommand
from clrs.cli import main
from clrs.common.decisions import DecisionLog
from tests.paths import SORTING

SORT = str(SORTING / "insertion-sort.clrs")
PROC = ".proc P\nRET\n.end\n"
DRIVER = ".driver\nCONST 1\nRET\n.end\n"
KINDS = {"load", "refuse", "pack", "unlinked", "cli"}
IGNORED = {"load comment", "load procedure", "load driver", "load label"}


class PackDecisionLogTest(unittest.TestCase):
    def decisions(self, action: Callable[[], object]) -> list[str]:
        with self.assertLogs("clrs", level="INFO") as captured:
            with contextlib.suppress(LoadError, LinkError):
                action()
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        messages = [record.getMessage() for record in captured.records]
        return [m for m in messages if m.split()[0] in KINDS and m not in IGNORED]

    def test_load_packed_module_and_entry(self) -> None:
        outcomes = self.decisions(lambda: load_program(f"▷ clrsa 1\n.module M\n{PROC}.entry main\n{DRIVER}"))
        self.assertEqual(outcomes, ["load packed", "load module", "load entry"])
        self.assertEqual(self.decisions(lambda: load_program(PROC)), [])

    def test_refuse_version_and_entry(self) -> None:
        self.assertEqual(self.decisions(lambda: load_program("▷ clrsa 9\n")), ["refuse version"])
        self.assertEqual(self.decisions(lambda: load_program(f".entry P\n{PROC}")), ["refuse entry"])
        missing = self.decisions(lambda: load_program(f"▷ clrsa 1\n.entry Q\n{PROC}"))
        self.assertEqual(missing, ["load packed", "refuse entry"])
        twice = self.decisions(lambda: load_program("▷ clrsa 1\n.entry P\n.entry P\n"))
        self.assertEqual(twice, ["load packed", "refuse entry"])

    def pack(self, entry: str, driver: str) -> str:
        engine = Engine()
        engine.load_file(SORT)
        if driver != "":
            engine.compile_driver(driver)
        return engine.packed_text(entry)

    def test_pack_driver_procedure_and_unlinked_entry(self) -> None:
        self.assertIn("pack driver", self.decisions(lambda: self.pack("main", "1")))
        self.assertEqual(self.decisions(lambda: self.pack("main", ""))[-1], "unlinked entry")
        self.assertEqual(self.decisions(lambda: self.pack("InsertionSort", ""))[-2:], ["pack procedure", "unlinked entry"])
        no_entry = self.decisions(lambda: Engine().run_entry(load_program(PROC)))
        self.assertEqual(no_entry, ["unlinked entry"])

    def test_cli_pack_and_packed_run(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        app = str(Path(holder.name) / "app.clrsa")
        pack = PackCommand(io.StringIO(), io.StringIO(), DecisionLog())
        cli = [m for m in self.decisions(lambda: pack.execute(["pack", SORT, "--", "1", "-o", app])) if m.startswith("cli")]
        self.assertEqual(cli, ["cli pack"])
        run = RunCommand(io.StringIO(), io.StringIO(), DecisionLog())
        self.assertEqual(self.decisions(lambda: run.execute(["run", app]))[0], "cli packed")
        self.assertEqual(self.decisions(lambda: pack.execute(["pack"])), ["cli usage"])
        fault = [m for m in self.decisions(lambda: pack.execute(["pack", SORT])) if m.startswith("cli")]
        self.assertEqual(fault, ["cli pack", "cli link"])

    def test_main_records_usage(self) -> None:
        with mock.patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(self.decisions(lambda: main(["bogus"])), ["cli usage"])


if __name__ == "__main__":
    unittest.main()
