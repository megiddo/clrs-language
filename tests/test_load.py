"""Loading .clrsa text: semantic instructions, resolved labels, round trips, and faults."""

import unittest
from pathlib import Path

from clrs import LoadError
from clrs import compile_driver
from clrs import compile_module
from clrs import load_program
from clrs.bytecode import BooleanConstant
from clrs.bytecode import DatatypeRecord
from clrs.bytecode import InfinityConstant
from clrs.bytecode import Instruction
from clrs.bytecode import IntegerConstant
from clrs.bytecode import NilConstant
from clrs.bytecode import Opcode
from clrs.bytecode import Program
from clrs.bytecode import Routine
from clrs.bytecode import Target
from tests.paths import SORTING

EXAMPLES = SORTING
COMPILABLE = sorted(EXAMPLES.glob("*.clrs"))
DRIVERS = [
    "A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A",
    "A ← [4, 1, 3, 2, 16, 9, 10, 14, 8, 7]; HeapSort(A); contains[A]",
    "A ← [5,]; MergeSort(A, 1, 1); A",
    "A ← [1, 2]; left[A, 1] = 3 and right[A, 1] = 4",
    "⌊-3/2⌋",
]


def op(opcode: Opcode, *operands: object) -> Instruction:
    return Instruction(opcode, operands)


def without_comments(text: str) -> str:
    return "".join(f"{line}\n" for line in text.splitlines() if not line.startswith("▷"))


class SemanticTest(unittest.TestCase):
    def test_while_procedure_loads_to_resolved_instructions(self) -> None:
        text = compile_module("Module M\nP(x)\n\twhile x > 0 do\n\t\tx ← x - 1\n\treturn x\n")
        expected = Routine(
            ".proc",
            "P",
            ("x",),
            (),
            (
                op(Opcode.LOAD, "x"),
                op(Opcode.CONST, IntegerConstant(0)),
                op(Opcode.CMP, "gt"),
                op(Opcode.JUMP_IF_FALSE, Target("L_while_end_1", 9)),
                op(Opcode.LOAD, "x"),
                op(Opcode.CONST, IntegerConstant(1)),
                op(Opcode.SUB),
                op(Opcode.STORE, "x"),
                op(Opcode.JUMP, Target("L_while_1", 0)),
                op(Opcode.LOAD, "x"),
                op(Opcode.RET),
                op(Opcode.CONST, NilConstant()),
                op(Opcode.RET),
            ),
            (("L_while_1", 0), ("L_while_end_1", 9)),
        )
        self.assertEqual(load_program(text), Program((expected,)))

    def test_driver_and_datatype_blocks_keep_file_order(self) -> None:
        heap = load_program(compile_module((EXAMPLES / "heap.clrs").read_text()))
        self.assertEqual(heap.blocks[0], DatatypeRecord("Heap", "Array", (("contains", IntegerConstant(0)),)))
        self.assertEqual([b.name for b in heap.blocks[1:]], ["left", "right"])
        program = load_program(compile_driver("A ← [5,]; A"))
        self.assertEqual(
            program,
            Program(
                (
                    Routine(
                        ".driver",
                        "",
                        (),
                        ("A",),
                        (
                            op(Opcode.CONST, IntegerConstant(5)),
                            op(Opcode.PACK, 1),
                            op(Opcode.STORE, "A"),
                            op(Opcode.LOAD, "A"),
                            op(Opcode.RET),
                        ),
                        (),
                    ),
                )
            ),
        )

    def test_for_back_jump_targets_the_end_reread(self) -> None:
        routine = load_program(compile_module((EXAMPLES / "insertion-sort.clrs").read_text())).blocks[0]
        back = [i for i in routine.instructions if i.opcode is Opcode.JUMP][-1]
        top = back.operands[0].index
        self.assertEqual(
            routine.instructions[top : top + 3],
            (op(Opcode.LOAD, "j"), op(Opcode.LOAD, "A"), op(Opcode.LOAD_ATTR, "length")),
        )
        exit_jump = routine.instructions[top + 4]
        self.assertEqual(exit_jump.opcode, Opcode.JUMP_IF_FALSE)
        self.assertIs(routine.instructions[exit_jump.operands[0].index - 1], back)

    def test_constants_are_typed(self) -> None:
        text = ".driver\nCONST -3\nCONST 1\nCONST True\nCONST False\nCONST NIL\nCONST ∞\n.end\n"
        operands = [i.operands[0] for i in load_program(text).blocks[0].instructions]
        self.assertEqual(
            operands,
            [
                IntegerConstant(-3),
                IntegerConstant(1),
                BooleanConstant(True),
                BooleanConstant(False),
                NilConstant(),
                InfinityConstant(),
            ],
        )
        self.assertNotEqual(operands[1], operands[2])

    def test_every_opcode_loads(self) -> None:
        text = (
            ".proc P\n.local x\nCONST 1\nLOAD x\nSTORE x\nLOAD_IDX\nSTORE_IDX\nLOAD_ATTR a\n"
            "STORE_ATTR a\nADD\nSUB\nMUL\nFLOORDIV\nCMP ne\nL:\nJUMP L\nJUMP_IF_FALSE L\n"
            "CALL F 2\nRET\nALLOC\nPACK 3\nPOP\n.end\n"
        )
        routine = load_program(text).blocks[0]
        self.assertEqual({i.opcode for i in routine.instructions}, set(Opcode))
        self.assertEqual(routine.instructions[14].operands, ("F", 2))
        self.assertEqual(routine.instructions[13].operands, (Target("L", 12),))
        self.assertEqual(routine.instructions[17].operands, (3,))


class TextTest(unittest.TestCase):
    def test_comments_blank_lines_and_indent_are_ignored(self) -> None:
        text = "▷ head\n\n.driver ▷ open\n   CONST 1 ▷ one\n\t\nRET\n.end\n"
        self.assertEqual(load_program(text).text(), ".driver\nCONST 1\nRET\n.end\n")

    def test_params_then_locals_round_trip(self) -> None:
        text = ".proc P\n.param a\n.param b\n.local c\nLOAD a\nLOAD b\nSTORE c\nLOAD c\nRET\n.end\n"
        routine = load_program(text).blocks[0]
        self.assertEqual((routine.parameters, routine.locals), (("a", "b"), ("c",)))
        self.assertEqual(routine.slots(), ("a", "b", "c"))
        self.assertEqual(load_program(text).text(), text)

    def test_labels_at_one_index_and_at_the_end(self) -> None:
        text = ".proc P\nA:\nB:\nJUMP B\nC:\n.end\n"
        routine = load_program(text).blocks[0]
        self.assertEqual(routine.labels, (("A", 0), ("B", 0), ("C", 1)))
        self.assertEqual(routine.instructions, (op(Opcode.JUMP, Target("B", 0)),))
        self.assertEqual(load_program(text).text(), text)

    def test_examples_round_trip(self) -> None:
        for path in COMPILABLE:
            with self.subTest(path=path.name):
                text = compile_module(path.read_text())
                program = load_program(text)
                self.assertEqual(program.text(), without_comments(text))
                self.assertEqual(load_program(program.text()), program)

    def test_drivers_round_trip(self) -> None:
        for source in DRIVERS:
            with self.subTest(source=source):
                text = compile_driver(source)
                program = load_program(text)
                self.assertEqual(program.text(), without_comments(text))
                self.assertEqual(load_program(program.text()), program)


class FaultTest(unittest.TestCase):
    CASES = [
        ("CONST 1\n", 1, "An instruction cannot appear outside a block."),
        ("L:\n", 1, "A label cannot appear outside a block."),
        (".end\n", 1, ".end cannot appear outside a block."),
        (".local x\n", 1, ".local cannot appear outside a block."),
        (".default c 0\n", 1, ".default cannot appear outside a block."),
        (".bogus\n", 1, ".bogus is not a directive."),
        (".proc\n", 1, ".proc takes 1 operand(s)."),
        (".driver x\n", 1, ".driver takes 0 operand(s)."),
        (".datatype H\n", 1, ".datatype takes 2 operand(s)."),
        (".proc P\n.end x\n", 2, ".end takes 0 operand(s)."),
        (".proc P\n", 1, "Missing .end inside .proc P."),
        ("\n.driver\n\n", 3, "Missing .end inside .driver."),
        (".datatype H Array\n", 1, "Missing .end inside .datatype H."),
        (".proc P\n.proc Q\n", 2, ".proc cannot appear inside .proc P."),
        (".proc P\n.default c 0\n", 2, ".default cannot appear inside .proc P."),
        (".datatype H Array\n.driver\n", 2, ".driver cannot appear inside .datatype H."),
        (".datatype H Array\n.local x\n", 2, ".local cannot appear inside .datatype H."),
        (".datatype H Array\nRET\n", 2, "An instruction cannot appear inside .datatype H."),
        (".datatype H Array\nL:\n", 2, "A label cannot appear inside .datatype H."),
        (".datatype H Array\n.default c x\n", 2, "x is not a constant."),
        (".proc P\nFOO\n.end\n", 2, "FOO is not an opcode."),
        (".proc P\nCONST\n.end\n", 2, "CONST takes 1 operand(s)."),
        (".proc P\nRET 1\n.end\n", 2, "RET takes 0 operand(s)."),
        (".proc P\nCALL F\n.end\n", 2, "CALL takes 2 operand(s)."),
        (".proc P\nCONST x\n.end\n", 2, "x is not a constant."),
        (".proc P\nCONST 1x\n.end\n", 2, "1x is not a constant."),
        (".proc P\nLOAD x\n.end\n", 2, "x is not a declared local."),
        (".proc P\nSTORE x\n.end\n", 2, "x is not a declared local."),
        (".proc P\nPACK -1\n.end\n", 2, "-1 is not a count."),
        (".proc P\nCALL F 2a\n.end\n", 2, "2a is not a count."),
        (".proc P\nCMP lte\n.end\n", 2, "lte is not a comparison."),
        (".proc P\nRET\nJUMP L\n.end\n", 3, "L is not defined."),
        (".proc P\nL:\nL:\n.end\n", 3, "L is defined twice."),
        (".proc P\nRET\n.local x\n.end\n", 3, ".local must come before the first instruction."),
        (".proc P\nL:\n.local x\n.end\n", 3, ".local must come before the first instruction."),
        (".proc P\n.local x\n.local x\n.end\n", 3, "x is declared twice."),
        (".param x\n", 1, ".param cannot appear outside a block."),
        (".param\n", 1, ".param takes 1 operand(s)."),
        (".datatype H Array\n.param x\n", 2, ".param cannot appear inside .datatype H."),
        (".driver\n.param x\n.end\n", 2, ".param cannot appear inside .driver."),
        (".proc P\n.local y\n.param x\n.end\n", 3, ".param must come before .local and the first instruction."),
        (".proc P\nRET\n.param x\n.end\n", 3, ".param must come before .local and the first instruction."),
        (".proc P\nL:\n.param x\n.end\n", 3, ".param must come before .local and the first instruction."),
        (".proc P\n.param x\n.param x\n.end\n", 3, "x is declared twice."),
        (".proc P\n.param x\n.local x\n.end\n", 3, "x is declared twice."),
    ]

    def test_faults(self) -> None:
        for text, line, message in self.CASES:
            with self.subTest(text=text):
                with self.assertRaises(LoadError) as caught:
                    load_program(text)
                self.assertEqual((caught.exception.line, caught.exception.message), (line, message))
                self.assertEqual(str(caught.exception), f"{line}: {message}")


if __name__ == "__main__":
    unittest.main()
