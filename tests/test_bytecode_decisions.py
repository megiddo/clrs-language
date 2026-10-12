"""Compile and load decision logs only. These tests do not assert any bytecode."""

import contextlib
import logging
import unittest
from pathlib import Path

from clrs import CompileError
from clrs import LoadError
from clrs import compile_driver
from clrs import compile_module
from clrs import load_program

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
LOWERING = {"compile", "routine", "datatype", "condition", "and", "if", "address", "reject"}
LOADING = {"load", "label", "refuse"}


class BytecodeDecisionLogTest(unittest.TestCase):
    def decisions(self, run: object, text: str, kinds: set[str]) -> list[str]:
        with self.assertLogs("clrs", level="INFO") as captured:
            with contextlib.suppress(CompileError, LoadError):
                run(text)  # type: ignore[operator]
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        messages = [record.getMessage() for record in captured.records]
        return [m for m in messages if m.split()[0] in kinds]

    def driver(self, source: str) -> list[str]:
        return self.decisions(compile_driver, source, LOWERING)

    def module(self, source: str) -> list[str]:
        return self.decisions(compile_module, source, LOWERING)

    def load(self, text: str) -> list[str]:
        return self.decisions(load_program, text, LOADING)

    def test_compile_kind_and_routines(self) -> None:
        self.assertEqual(self.driver("1"), ["compile driver"])
        heap = self.module((EXAMPLES / "heap.clrs").read_text())
        self.assertEqual(
            heap,
            ["compile module", "datatype default", "routine method", "routine method"],
        )
        self.assertEqual(self.module("Module M\nP()\n\treturn 1\n")[1:], ["routine procedure"])

    def test_condition(self) -> None:
        self.assertEqual(
            self.driver("a ← 1; a and a"),
            ["compile driver", "address name", "and value", "condition and"]
            + ["condition value", "condition value"],
        )
        self.assertEqual(
            self.module("Module M\nP(x)\n\twhile x do\n\t\tF(x)\n"),
            ["compile module", "routine procedure", "condition value"],
        )

    def test_if(self) -> None:
        bare = self.module("Module M\nP(x)\n\tif x then\n\t\tF(x)\n")
        self.assertEqual(bare[2:], ["if bare", "condition value"])
        both = self.module("Module M\nP(x)\n\tif x then\n\t\tF(x)\n\telse\n\t\tF(x)\n")
        self.assertEqual(both[2:], ["if else", "condition value"])

    def test_address(self) -> None:
        self.assertEqual(
            self.module("Module M\nP(A, x)\n\tA[1] ↔ x\n\tcontains[A] ← 1\n")[2:],
            ["address index", "address name", "address attribute"],
        )

    def test_compile_rejections(self) -> None:
        self.assertEqual(self.driver("y")[-1], "reject name")
        default = "Module M\ndatatype H extends Array:\n\tc ← 1 + 1\n"
        self.assertEqual(self.module(default)[-1], "reject default")

    def test_load_blocks(self) -> None:
        self.assertEqual(
            self.load(".datatype H Array\n.end\n.proc P\n.end\n.driver\n.end\n"),
            ["load datatype", "load procedure", "load driver"],
        )

    def test_load_comment_and_labels(self) -> None:
        self.assertEqual(
            self.load("▷ c\n.proc P\nL: ▷ top\nJUMP L\n.end\n"),
            ["load comment", "load procedure", "load comment", "load label", "label resolve"],
        )

    def test_load_refusals(self) -> None:
        cases = [
            ("RET\n", "refuse block"),
            (".proc P\n", "refuse block"),
            (".x\n", "refuse directive"),
            (".end 1\n", "refuse directive"),
            (".proc P\nRET\n.local x\n", "refuse local"),
            (".proc P\n.local x\n.local x\n", "refuse local"),
            (".proc P\nL:\nL:\n", "refuse label"),
            (".proc P\nX\n", "refuse opcode"),
            (".proc P\nRET 1\n", "refuse operands"),
            (".proc P\nCONST x\n", "refuse constant"),
            (".proc P\nLOAD x\n", "refuse local"),
            (".proc P\nPACK x\n", "refuse count"),
            (".proc P\nCMP x\n", "refuse comparison"),
            (".proc P\nJUMP L\n.end\n", "refuse label"),
        ]
        for text, outcome in cases:
            with self.subTest(text=text):
                self.assertEqual(self.load(text)[-1], outcome)


if __name__ == "__main__":
    unittest.main()
