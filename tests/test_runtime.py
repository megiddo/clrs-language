"""Loaded .clrsa text the compiler never emits, value types, and module merging faults."""

import unittest
from pathlib import Path

from clrs import Engine
from clrs import LinkError
from clrs import RuntimeFault
from clrs import load_program
from clrs.bytecode import BooleanConstant
from clrs.bytecode import InfinityConstant
from clrs.bytecode import IntegerConstant
from clrs.bytecode import NilConstant
from clrs.bytecode import Routine
from clrs.common.decisions import DecisionLog
from clrs.vm.machine import COMMANDS
from clrs.vm.machine import Machine
from clrs.vm.values import INFINITY
from clrs.vm.values import NIL
from clrs.vm.values import UNASSIGNED
from clrs.vm.values import ClrsArray
from clrs.vm.values import constant_value
from clrs.vm.values import kind
from tests.paths import SORTING

EXAMPLES = SORTING


def execute(text: str) -> object:
    blocks = load_program(text).blocks
    routines = {b.name: b for b in blocks if isinstance(b, Routine) and b.directive == ".proc"}
    driver = next(b for b in blocks if isinstance(b, Routine) and b.directive == ".driver")
    return Machine(routines, DecisionLog()).run(driver)


class LoadedTextTest(unittest.TestCase):
    def fault(self, text: str) -> str:
        with self.assertRaises(RuntimeFault) as caught:
            execute(text)
        return caught.exception.message

    def test_every_opcode_has_a_command(self) -> None:
        from clrs.bytecode import Opcode

        self.assertEqual(set(COMMANDS), set(Opcode))

    def test_driver_returns_its_value(self) -> None:
        self.assertEqual(execute(".driver\nCONST 4\nRET\n.end\n"), 4)

    def test_running_past_the_end(self) -> None:
        self.assertEqual(self.fault(".driver\nCONST 1\n.end\n"), "the driver ran past its last instruction.")
        text = ".driver\nCALL P 0\nRET\n.end\n.proc P\nCONST 1\n.end\n"
        self.assertEqual(self.fault(text), "P ran past its last instruction.")

    def test_operand_underflow(self) -> None:
        self.assertEqual(self.fault(".driver\nPOP\nRET\n.end\n"), "The operand stack of the driver is empty.")

    def test_length_cannot_be_stored(self) -> None:
        text = ".driver\nCONST 1\nALLOC\nCONST 2\nSTORE_ATTR length\nCONST 0\nRET\n.end\n"
        self.assertEqual(self.fault(text), "length cannot be stored.")

    def test_call_pops_its_arguments_and_pushes_the_result(self) -> None:
        text = (
            ".driver\nCONST 7\nCONST 10\nCONST 3\nCALL Minus 2\nSUB\nRET\n.end\n"
            ".proc Minus\n.param a\n.param b\nLOAD a\nLOAD b\nSUB\nRET\n.end\n"
        )
        self.assertEqual(execute(text), 0)

    def test_unlinked_text_still_faults_on_arity_at_run(self) -> None:
        proc = ".proc Two\n.param a\n.param b\n.local c\nCONST 0\nRET\n.end\n"
        cases = {
            ".driver\nCONST 1\nCALL Two 1\nRET\n.end\n": "Two takes 2 argument(s), not 1.",
            ".driver\nCONST 1\nCONST 2\nCONST 3\nCALL Two 3\nRET\n.end\n": "Two takes 2 argument(s), not 3.",
        }
        for driver, message in cases.items():
            with self.subTest(driver=driver):
                self.assertEqual(self.fault(driver + proc), message)
        self.assertEqual(execute(".driver\nCONST 1\nCONST 2\nCALL Two 2\nRET\n.end\n" + proc), 0)

    def test_arguments_bind_parameters_and_leave_locals_unassigned(self) -> None:
        proc = ".proc P\n.param a\n.local b\nLOAD b\nRET\n.end\n"
        self.assertEqual(self.fault(".driver\nCONST 1\nCALL P 1\nRET\n.end\n" + proc), "b is read before it is assigned.")

    def test_pop_discards_only_the_top(self) -> None:
        self.assertEqual(execute(".driver\nCONST 1\nCONST 2\nPOP\nRET\n.end\n"), 1)

    def test_jump_skips(self) -> None:
        self.assertEqual(execute(".driver\nCONST 1\nJUMP L\nCONST 2\nL:\nRET\n.end\n"), 1)


class ValueTest(unittest.TestCase):
    def test_singletons_print(self) -> None:
        self.assertEqual((repr(INFINITY), repr(NIL), repr(UNASSIGNED)), ("∞", "NIL", "unassigned"))
        self.assertEqual(repr(ClrsArray([1, NIL])), "ClrsArray([1, NIL])")

    def test_constants_become_values(self) -> None:
        self.assertIs(constant_value(NilConstant()), NIL)
        self.assertIs(constant_value(InfinityConstant()), INFINITY)
        self.assertIs(constant_value(BooleanConstant(True)), True)
        self.assertEqual(constant_value(IntegerConstant(-3)), -3)
        self.assertIs(type(constant_value(IntegerConstant(1))), int)

    def test_kind_names(self) -> None:
        self.assertEqual(kind(3), "an integer")
        self.assertEqual(kind(False), "a boolean")
        self.assertEqual(kind(ClrsArray([])), "an array")
        self.assertEqual(kind(UNASSIGNED), "unassigned")

    def test_array_entity(self) -> None:
        array = ClrsArray([NIL, NIL])
        array.put(2, 5)
        self.assertEqual((array.length(), array.get(2), array.items()), (2, 5, (NIL, 5)))
        self.assertEqual([array.holds(i) for i in (0, 1, 2, 3)], [False, True, True, False])
        self.assertFalse(array.has("contains"))
        array.set_attribute("contains", 1)
        self.assertEqual((array.has("contains"), array.attribute("contains")), (True, 1))


class EngineTest(unittest.TestCase):
    def test_files_by_string_or_path(self) -> None:
        by_string = Engine.of(str(EXAMPLES / "heap.clrs"))
        by_path = Engine.of(EXAMPLES / "heap.clrs")
        self.assertEqual(by_string.listing("Clrs.Sorting"), by_path.listing("Clrs.Sorting"))

    def test_listing_concatenates_merged_files(self) -> None:
        engine = Engine.of(EXAMPLES / "heap.clrs", EXAMPLES / "max-heapify.clrs")
        listing = engine.listing("Clrs.Sorting")
        self.assertLess(listing.index(".proc left\n"), listing.index(".proc MaxHeapify\n"))
        heap = Engine.of(EXAMPLES / "heap.clrs").listing("Clrs.Sorting")
        heapify = Engine.of(EXAMPLES / "max-heapify.clrs").listing("Clrs.Sorting")
        self.assertEqual(listing, heap + heapify)

    def test_faults_print_their_message(self) -> None:
        self.assertEqual(str(RuntimeFault("NIL cannot be compared.")), "NIL cannot be compared.")
        self.assertEqual(str(LinkError("P is defined.")), "P is defined.")

    def test_modules_keep_load_order(self) -> None:
        engine = Engine()
        engine.load_source("Module B\nP()\n\treturn 1\n")
        engine.load_source("Module A\nQ()\n\treturn P() + 1\n")
        self.assertEqual(engine.modules(), ("B", "A"))
        self.assertEqual(engine.run("Q()"), 2)

    def test_compile_driver_is_text(self) -> None:
        text = Engine().compile_driver("1 + 2")
        self.assertEqual(text, ".driver\n▷ 1 + 2\nCONST 1\nCONST 2\nADD\nRET\n.end\n")

    def link(self, *sources: str) -> str:
        engine = Engine()
        with self.assertRaises(LinkError) as caught:
            for source in sources:
                engine.load_source(source)
        return caught.exception.message

    def test_duplicates_do_not_merge(self) -> None:
        sort = (EXAMPLES / "insertion-sort.clrs").read_text()
        heap = (EXAMPLES / "heap.clrs").read_text()
        clash = "Module Other\nHeap()\n\treturn 1\n"
        self.assertEqual(self.link(sort, sort), "InsertionSort in Clrs.Sorting is already defined.")
        self.assertEqual(self.link(heap, heap), "Heap in Clrs.Sorting is already defined.")
        self.assertEqual(self.link(heap, clash), "Heap in Other is already defined.")

    def test_unknown_callee_is_left_to_the_machine(self) -> None:
        engine = Engine()
        engine.load_source("Module M\nP()\n\treturn Gone(1)\n")
        self.assertEqual(engine.run("2"), 2)
        with self.assertRaises(RuntimeFault) as caught:
            engine.run("P()")
        self.assertEqual(caught.exception.message, "Gone is not a loaded procedure.")

    def test_unknown_module_and_datatype(self) -> None:
        engine = Engine()
        with self.assertRaises(LinkError) as caught:
            engine.listing("Nope")
        self.assertEqual(caught.exception.message, "Nope is not a loaded module.")
        with self.assertRaises(LinkError) as caught:
            engine.datatype("Heap")
        self.assertEqual(caught.exception.message, "Heap is not a loaded datatype.")


if __name__ == "__main__":
    unittest.main()
