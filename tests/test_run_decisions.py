"""Run and link decision logs only. These tests do not assert any program result."""

import contextlib
import logging
import unittest
from collections.abc import Callable
from pathlib import Path

from clrs import Engine
from clrs import LinkError
from clrs import RuntimeFault
from clrs import load_program
from clrs.common.decisions import DecisionLog
from clrs.vm.machine import Machine
from tests.paths import SORTING

EXAMPLES = SORTING
RUNNING = {"run", "call", "branch", "compare", "attribute", "fault"}
LINKING = {"module", "unlinked"}


class RunDecisionLogTest(unittest.TestCase):
    def decisions(self, action: Callable[[], object], kinds: set[str]) -> list[str]:
        with self.assertLogs("clrs", level="INFO") as captured:
            with contextlib.suppress(RuntimeFault, LinkError):
                action()
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        messages = [record.getMessage() for record in captured.records]
        return [m for m in messages if m.split()[0] in kinds]

    def run_driver(self, driver: str, *sources: str) -> list[str]:
        engine = Engine()
        for source in sources:
            engine.load_source(source)
        return self.decisions(lambda: engine.run(driver), RUNNING)

    def test_run_and_call(self) -> None:
        self.assertEqual(self.run_driver("1"), ["run driver"])
        source = "Module M\nP()\n\treturn 1\n"
        self.assertEqual(self.run_driver("P()", source), ["run driver", "call procedure"])

    def test_branches(self) -> None:
        source = "Module M\nP(x)\n\tif x then\n\t\treturn 1\n\treturn 0\n"
        self.assertEqual(self.run_driver("P(True)", source)[2:], ["branch through"])
        self.assertEqual(self.run_driver("P(False)", source)[2:], ["branch taken"])

    def test_comparisons(self) -> None:
        self.assertEqual(self.run_driver("1 < 2")[1:], ["compare integer"])
        self.assertEqual(self.run_driver("1 < ∞")[1:], ["compare infinity"])
        self.assertEqual(self.run_driver("∞ = 1")[1:], ["compare infinity"])
        self.assertEqual(self.run_driver("True = False")[1:], ["compare boolean"])
        self.assertEqual(self.run_driver("A ← [1,]; A = A")[1:], ["compare identity"])

    def test_attributes(self) -> None:
        self.assertEqual(self.run_driver("A ← [1,]; length[A]")[1:], ["attribute length"])
        driver = "A ← [1,]; contains[A] ← 1; contains[A]"
        self.assertEqual(self.run_driver(driver)[1:], ["attribute stored"])

    def test_faults(self) -> None:
        cases = {
            "NIL < 1": "fault nil",
            "True < 1": "fault order",
            "True = 1": "fault mixed",
            "1 + True": "fault arithmetic",
            "⌊1/0⌋": "fault zero",
            "x ← 1; x[1]": "fault array",
            "A ← [1,]; A[True]": "fault index",
            "A ← [1,]; A[2]": "fault bounds",
            "[-1]": "fault size",
            "A ← [1,]; contains[A]": "fault attribute",
            "Nope()": "fault procedure",
        }
        for driver, outcome in cases.items():
            self.assertEqual(self.run_driver(driver)[-1], outcome, driver)

    def test_frame_faults(self) -> None:
        unset = "Module M\nP()\n\tif False then\n\t\tx ← 1\n\treturn x\n"
        self.assertEqual(self.run_driver("P()", unset)[-1], "fault unassigned")
        condition = "Module M\nP()\n\tif 1 then\n\t\treturn 1\n\treturn 0\n"
        self.assertEqual(self.run_driver("P()", condition)[-1], "fault condition")
        down = "Module M\nDown(n)\n\tif n > 0 then\n\t\treturn Down(n - 1)\n\treturn 0\n"
        self.assertEqual(self.run_driver("Down(10000)", down)[-1], "fault depth")

    def test_arity_fault_on_unlinked_text(self) -> None:
        text = ".driver\nCALL P 1\nRET\n.end\n.proc P\nRET\n.end\n"
        blocks = load_program(text).blocks
        machine = Machine({"P": blocks[1]}, DecisionLog())
        self.assertEqual(self.decisions(lambda: machine.run(blocks[0]), RUNNING)[-1], "fault arity")

    def test_loaded_text_faults(self) -> None:
        cases = {
            ".driver\nCONST 1\n.end\n": "fault fall",
            ".driver\nPOP\nRET\n.end\n": "fault underflow",
            ".driver\nCONST 1\nALLOC\nCONST 2\nSTORE_ATTR length\nRET\n.end\n": "fault length",
        }
        for text, outcome in cases.items():
            driver = load_program(text).blocks[0]
            machine = Machine({}, DecisionLog())
            self.assertEqual(self.decisions(lambda: machine.run(driver), RUNNING)[-1], outcome)

    def link(self, *sources: str) -> list[str]:
        engine = Engine()

        def load() -> None:
            for source in sources:
                engine.load_source(source)

        return self.decisions(load, LINKING)

    def test_module_merge(self) -> None:
        heap = (EXAMPLES / "heap.clrs").read_text()
        sort = (EXAMPLES / "insertion-sort.clrs").read_text()
        self.assertEqual(self.link(heap, sort), ["module open", "module datatype", "module merge"])
        self.assertEqual(self.link(sort, sort), ["module open", "module merge", "unlinked duplicate"])

    def linked(self, driver: str, *sources: str) -> list[str]:
        engine = Engine()
        for source in sources:
            engine.load_source(source)
        return self.decisions(lambda: engine.run(driver), {"link", "unlinked"})

    def test_link_calls(self) -> None:
        self.assertEqual(self.linked("1"), [])
        source = "Module M\nP(a)\n\treturn a\n"
        self.assertEqual(self.linked("P(1)", source), ["link call"])
        self.assertEqual(self.linked("Nope()", source), ["link deferred"])
        self.assertEqual(self.linked("P()", source), ["unlinked arity"])
        self.assertEqual(self.linked("P(1, 2)", source), ["unlinked arity"])

    def test_unknown_lookups(self) -> None:
        engine = Engine()
        self.assertEqual(self.decisions(lambda: engine.listing("M"), LINKING), ["unlinked module"])
        self.assertEqual(self.decisions(lambda: engine.datatype("H"), LINKING), ["unlinked datatype"])


if __name__ == "__main__":
    unittest.main()
