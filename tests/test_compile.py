"""Lowering proofs read off the .clrsa text itself."""

import unittest
from pathlib import Path

from clrs import CompileError
from clrs import compile_driver
from clrs import compile_module
from clrs.errors import DEFAULT_MESSAGE

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

INSERTION_SORT = """\
▷ Module Clrs.Sorting
.proc InsertionSort
.local A
.local j
.local key
.local i
▷ for j ← 2 to length[A] do
CONST 2
STORE j
L_for_1:
LOAD j
LOAD A
LOAD_ATTR length
CMP le
JUMP_IF_FALSE L_for_end_1
▷ key ← A[j]
LOAD A
LOAD j
LOAD_IDX
STORE key
▷ i ← j - 1
LOAD j
CONST 1
SUB
STORE i
▷ while i > 0 and A[i] > key do
L_while_2:
LOAD i
CONST 0
CMP gt
JUMP_IF_FALSE L_while_end_2
LOAD A
LOAD i
LOAD_IDX
LOAD key
CMP gt
JUMP_IF_FALSE L_while_end_2
▷ A[i + 1] ← A[i]
LOAD A
LOAD i
CONST 1
ADD
LOAD A
LOAD i
LOAD_IDX
STORE_IDX
▷ i ← i - 1
LOAD i
CONST 1
SUB
STORE i
JUMP L_while_2
L_while_end_2:
▷ A[i + 1] ← key
LOAD A
LOAD i
CONST 1
ADD
LOAD key
STORE_IDX
LOAD j
CONST 1
ADD
STORE j
JUMP L_for_1
L_for_end_1:
CONST NIL
RET
.end
"""

HEAP = """\
▷ Module Clrs.Sorting
.datatype Heap Array
.default contains 0
.end
.proc left
.local A
.local i
▷ return ((i + 1) * 2) - 1
LOAD i
CONST 1
ADD
CONST 2
MUL
CONST 1
SUB
RET
CONST NIL
RET
.end
.proc right
.local A
.local i
▷ return ((i + 1) * 2)
LOAD i
CONST 1
ADD
CONST 2
MUL
RET
CONST NIL
RET
.end
"""


def example(name: str) -> str:
    return compile_module((EXAMPLES / name).read_text())


def code(text: str) -> list[str]:
    """Instruction and label lines, without comments or directives."""
    return [line for line in text.splitlines() if not line.startswith(("▷", "."))]


def driver(source: str) -> list[str]:
    return code(compile_driver(source))


def procedure(body: str, parameters: str = "A, x, y") -> list[str]:
    lines = "".join(f"\t{line}\n" for line in body.splitlines())
    return code(compile_module(f"Module M\nP({parameters})\n{lines}"))


def window(lines: list[str], start: str, stop: str) -> list[str]:
    first = lines.index(start)
    return lines[first + 1 : lines.index(stop, first)]


class SnapshotTest(unittest.TestCase):
    def test_insertion_sort(self) -> None:
        self.assertEqual(example("insertion-sort.clrs"), INSERTION_SORT)

    def test_heap_records_default_and_methods_become_procedures(self) -> None:
        self.assertEqual(example("heap.clrs"), HEAP)

    def test_driver_has_no_trailing_nil(self) -> None:
        self.assertEqual(
            compile_driver("A ← []; A"),
            ".driver\n.local A\n▷ A ← []; A\nPACK 0\nSTORE A\nLOAD A\nRET\n.end\n",
        )


class AndTest(unittest.TestCase):
    def test_condition_is_two_jumps_and_right_operand_after_first(self) -> None:
        lines = example("insertion-sort.clrs").splitlines()
        test = window(lines, "L_while_2:", "▷ A[i + 1] ← A[i]")
        self.assertEqual(
            test,
            [
                "LOAD i",
                "CONST 0",
                "CMP gt",
                "JUMP_IF_FALSE L_while_end_2",
                "LOAD A",
                "LOAD i",
                "LOAD_IDX",
                "LOAD key",
                "CMP gt",
                "JUMP_IF_FALSE L_while_end_2",
            ],
        )

    def test_value_is_two_jumps_then_true_or_false(self) -> None:
        lines = driver("a ← True; b ← F(a) and G(a); b")
        jumps = [i for i, line in enumerate(lines) if line.startswith("JUMP_IF_FALSE")]
        self.assertEqual(len(jumps), 2)
        self.assertLess(jumps[0], lines.index("CALL G 1"))
        self.assertLess(lines.index("CALL F 1"), jumps[0])
        self.assertEqual(
            lines[jumps[1] :],
            [
                "JUMP_IF_FALSE L_and_false_1",
                "CONST True",
                "JUMP L_and_end_1",
                "L_and_false_1:",
                "CONST False",
                "L_and_end_1:",
                "STORE b",
                "LOAD b",
                "RET",
            ],
        )

    def test_chained_and_is_one_jump_per_operand(self) -> None:
        lines = procedure("if x > 0 and y > 0 and x < y then\n\tx ← 1")
        self.assertEqual(lines.count("JUMP_IF_FALSE L_endif_1"), 3)


class ForTest(unittest.TestCase):
    def test_end_expression_is_read_after_the_loop_label(self) -> None:
        lines = code(example("insertion-sort.clrs"))
        test = window(lines, "L_for_1:", "JUMP_IF_FALSE L_for_end_1")
        self.assertEqual(test, ["LOAD j", "LOAD A", "LOAD_ATTR length", "CMP le"])
        self.assertEqual(lines.count("LOAD_ATTR length"), 1)

    def test_step_follows_the_body_and_jumps_back_to_the_test(self) -> None:
        lines = code(example("insertion-sort.clrs"))
        end = lines.index("L_for_end_1:")
        self.assertEqual(
            lines[end - 6 : end],
            ["STORE_IDX", "LOAD j", "CONST 1", "ADD", "STORE j", "JUMP L_for_1"],
        )

    def test_downto_compares_ge_and_subtracts(self) -> None:
        lines = code(example("build-max-heap.clrs"))
        test = window(lines, "L_for_1:", "JUMP_IF_FALSE L_for_end_1")
        self.assertEqual(test, ["LOAD i", "CONST 1", "CMP ge"])
        self.assertEqual(
            window(lines, "POP", "L_for_end_1:"),
            ["LOAD i", "CONST 1", "SUB", "STORE i", "JUMP L_for_1"],
        )

    def test_start_is_stored_once_before_the_label(self) -> None:
        lines = code(example("build-max-heap.clrs"))
        self.assertEqual(
            lines[: lines.index("L_for_1:")],
            [
                "LOAD A",
                "LOAD A",
                "LOAD_ATTR length",
                "STORE_ATTR contains",
                "LOAD A",
                "LOAD_ATTR length",
                "CONST 2",
                "FLOORDIV",
                "STORE i",
            ],
        )


class ArrayTest(unittest.TestCase):
    def test_size_expression_is_alloc(self) -> None:
        lines = code(example("merge.clrs"))
        self.assertEqual(
            window(lines, "STORE n_2", "STORE L"),
            ["LOAD n_1", "CONST 1", "ADD", "ALLOC"],
        )

    def test_literal_is_consts_then_pack(self) -> None:
        self.assertEqual(
            driver("[5, 2, 4, 6, 1, 3]"),
            ["CONST 5", "CONST 2", "CONST 4", "CONST 6", "CONST 1", "CONST 3", "PACK 6", "RET"],
        )

    def test_single_element_forms(self) -> None:
        self.assertEqual(driver("[5]"), ["CONST 5", "ALLOC", "RET"])
        self.assertEqual(driver("[5,]"), ["CONST 5", "PACK 1", "RET"])
        self.assertEqual(driver("[]"), ["PACK 0", "RET"])


class ExchangeTest(unittest.TestCase):
    def test_each_address_expression_is_evaluated_once(self) -> None:
        lines = procedure("A[F(x)] ↔ A[G(y)]")
        self.assertEqual(lines.count("CALL F 1"), 1)
        self.assertEqual(lines.count("CALL G 1"), 1)
        self.assertEqual(lines.count("LOAD A"), 2)

    def test_index_exchange_spills_then_swaps(self) -> None:
        self.assertEqual(
            procedure("A[x] ↔ A[y]"),
            [
                "LOAD A",
                "STORE $1",
                "LOAD x",
                "STORE $2",
                "LOAD A",
                "STORE $3",
                "LOAD y",
                "STORE $4",
                "LOAD $1",
                "LOAD $2",
                "LOAD_IDX",
                "STORE $5",
                "LOAD $1",
                "LOAD $2",
                "LOAD $3",
                "LOAD $4",
                "LOAD_IDX",
                "STORE_IDX",
                "LOAD $3",
                "LOAD $4",
                "LOAD $5",
                "STORE_IDX",
                "CONST NIL",
                "RET",
            ],
        )

    def test_name_exchange(self) -> None:
        self.assertEqual(
            procedure("x ↔ y")[:6],
            ["LOAD x", "STORE $1", "LOAD y", "STORE x", "LOAD $1", "STORE y"],
        )

    def test_attribute_exchange_evaluates_owner_once(self) -> None:
        self.assertEqual(
            procedure("contains[A] ↔ contains[x]")[:12],
            [
                "LOAD A",
                "STORE $1",
                "LOAD x",
                "STORE $2",
                "LOAD $1",
                "LOAD_ATTR contains",
                "STORE $3",
                "LOAD $1",
                "LOAD $2",
                "LOAD_ATTR contains",
                "STORE_ATTR contains",
                "LOAD $2",
            ],
        )

    def test_temporaries_are_reused_and_declared_after_locals(self) -> None:
        text = compile_module("Module M\nP(A, x)\n\tA[1] ↔ A[x]\n\tA[x] ↔ A[1]\n\tk ← 1\n")
        declared = [line for line in text.splitlines() if line.startswith(".local")]
        self.assertEqual(
            declared,
            [".local A", ".local x", ".local k", *[f".local ${n}" for n in range(1, 6)]],
        )


class ExpressionTest(unittest.TestCase):
    def test_minus_then_plus_is_left_associative(self) -> None:
        self.assertEqual(
            procedure("x ← A - x + 1")[:5],
            ["LOAD A", "LOAD x", "SUB", "CONST 1", "ADD"],
        )

    def test_times_binds_tighter_than_plus(self) -> None:
        self.assertEqual(
            procedure("x ← x + 1 * 2")[:5],
            ["LOAD x", "CONST 1", "CONST 2", "MUL", "ADD"],
        )

    def test_floor_of_negative_quotient(self) -> None:
        self.assertEqual(
            driver("⌊-3/2⌋"),
            ["CONST 0", "CONST 3", "SUB", "CONST 2", "FLOORDIV", "RET"],
        )

    def test_constants(self) -> None:
        self.assertEqual(driver("NIL"), ["CONST NIL", "RET"])
        self.assertEqual(driver("∞"), ["CONST ∞", "RET"])
        self.assertEqual(driver("False"), ["CONST False", "RET"])

    def test_comparisons(self) -> None:
        cases = {"<": "lt", ">": "gt", "≤": "le", "≥": "ge", "=": "eq", "≠": "ne"}
        for glyph, name in cases.items():
            with self.subTest(glyph=glyph):
                self.assertEqual(
                    driver(f"a ← 1; a {glyph} 2"),
                    ["CONST 1", "STORE a", "LOAD a", "CONST 2", f"CMP {name}", "RET"],
                )

    def test_bracket_call_and_attribute(self) -> None:
        self.assertEqual(
            driver("A ← [1]; left[A, 1] + contains[A]")[3:],
            ["LOAD A", "CONST 1", "CALL left 2", "LOAD A", "LOAD_ATTR contains", "ADD", "RET"],
        )

    def test_unknown_name_is_a_compile_error(self) -> None:
        with self.assertRaises(CompileError) as caught:
            compile_module("Module M\nP()\n\tF(x)\n")
        error = caught.exception
        self.assertEqual((error.message, error.line, error.column), ('"x" is not a local.', 3, 4))


class StatementTest(unittest.TestCase):
    def test_if_else_jumps_over_the_alternate(self) -> None:
        self.assertEqual(
            procedure("if x then\n\ty ← 1\nelse\n\ty ← 2")[:10],
            [
                "LOAD x",
                "JUMP_IF_FALSE L_else_1",
                "CONST 1",
                "STORE y",
                "JUMP L_endif_1",
                "L_else_1:",
                "CONST 2",
                "STORE y",
                "L_endif_1:",
                "CONST NIL",
            ],
        )

    def test_call_statement_pops_and_return_rets(self) -> None:
        self.assertEqual(
            procedure("F(x)\nreturn y"),
            ["LOAD x", "CALL F 1", "POP", "LOAD y", "RET", "CONST NIL", "RET"],
        )

    def test_mergesort_calls_are_siblings_inside_the_if(self) -> None:
        lines = code(example("mergesort.clrs"))
        body = window(lines, "JUMP_IF_FALSE L_endif_1", "L_endif_1:")
        self.assertEqual([line for line in body if line.startswith("CALL")], [
            "CALL MergeSort 3",
            "CALL MergeSort 3",
            "CALL Merge 4",
        ])

    def test_each_source_line_is_commented_once(self) -> None:
        text = compile_driver("a ← 1; b ← 2; a")
        self.assertEqual(text.count("▷ a ← 1; b ← 2; a"), 1)
        merge = example("merge.clrs").splitlines()
        self.assertEqual(merge.count("▷ L[i] ← A[p + i - 1]"), 1)
        self.assertLess(merge.index("▷ i ← 1"), merge.index("▷ j ← 1"))

    def test_default_must_be_a_literal(self) -> None:
        with self.assertRaises(CompileError) as caught:
            compile_module("Module M\ndatatype H extends Array:\n\tcontains ← 1 + 1\n")
        error = caught.exception
        self.assertEqual((error.message, error.line, error.column), (DEFAULT_MESSAGE, 3, 2))

    def test_default_constants(self) -> None:
        text = compile_module(
            "Module M\ndatatype H extends Array:\n\ta ← True\n\tb ← NIL\n\tc ← ∞\n"
        )
        self.assertIn(".default a True\n.default b NIL\n.default c ∞\n.end\n", text)


if __name__ == "__main__":
    unittest.main()
