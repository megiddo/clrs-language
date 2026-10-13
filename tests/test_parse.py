import dataclasses
import unittest
from pathlib import Path

import clrs.front.ast as ast
from clrs import CompileError
from clrs import parse_driver
from clrs import parse_module
from clrs.common.errors import CEILING_MESSAGE
from clrs.common.errors import CHAIN_MESSAGE
from clrs.common.errors import FLOOR_MESSAGE
from clrs.common.errors import FOR_DIRECTION_MESSAGE
from clrs.common.errors import FOR_END_MESSAGE
from clrs.common.errors import LENGTH_MESSAGE
from clrs.common.errors import OR_MESSAGE
from clrs.common.errors import SLASH_MESSAGE
from clrs.common.errors import TARGET_MESSAGE

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def shape(node: object) -> object:
    """Reduce a syntax tree to nested tuples without source positions."""
    if isinstance(node, tuple):
        return tuple(shape(item) for item in node)
    if dataclasses.is_dataclass(node) and dataclasses.fields(node) == ():
        return type(node).__name__
    if dataclasses.is_dataclass(node):
        fields = [f.name for f in dataclasses.fields(node) if f.name not in ("line", "column")]
        return (type(node).__name__, *[shape(getattr(node, name)) for name in fields])
    return node


def N(text: str) -> tuple:
    return ("Name", text)


def I(value: int) -> tuple:
    return ("IntegerLiteral", value)


def Ix(target: str, index: object) -> tuple:
    return ("Index", N(target), index)


def B(operator: str, left: object, right: object) -> tuple:
    return ("Binary", operator, left, right)


def C(operator: str, left: object, right: object) -> tuple:
    return ("Comparison", operator, left, right)


def expr(source: str) -> object:
    return shape(parse_driver(source).result)


def body(name: str) -> tuple:
    module = parse_module((EXAMPLES / name).read_text())
    return shape(module.definitions[0])


def procedure(text: str) -> tuple:
    return shape(parse_module("Module M\n" + text).definitions[0])


class CompileErrorCase(unittest.TestCase):
    def assertModuleError(self, source: str, message: str, line: int, column: int) -> None:
        with self.assertRaises(CompileError) as caught:
            parse_module(source)
        self.assertEqual(caught.exception.message, message)
        self.assertEqual((caught.exception.line, caught.exception.column), (line, column))

    def assertDriverError(self, source: str, message: str, line: int, column: int) -> None:
        with self.assertRaises(CompileError) as caught:
            parse_driver(source)
        self.assertEqual(caught.exception.message, message)
        self.assertEqual((caught.exception.line, caught.exception.column), (line, column))


class ExampleFilesTest(CompileErrorCase):
    def test_insertion_sort_while_test_is_and_of_two_comparisons(self) -> None:
        proc = body("insertion-sort.clrs")
        self.assertEqual(proc[:3], ("Procedure", "InsertionSort", ("A",)))
        loop = proc[3][0]
        self.assertEqual(loop[:3], ("ForLoop", "j", I(2)))
        self.assertEqual(loop[3:5], ("CountUp", ("Attribute", "length", N("A"))))
        self.assertEqual(loop[5][0], ("Assign", N("key"), Ix("A", N("j"))))
        self.assertEqual(loop[5][1], ("Assign", N("i"), B("-", N("j"), I(1))))
        inner = loop[5][2]
        self.assertEqual(
            inner[1],
            ("And", C(">", N("i"), I(0)), C(">", Ix("A", N("i")), N("key"))),
        )
        self.assertEqual(inner[2][0], ("Assign", Ix("A", B("+", N("i"), I(1))), Ix("A", N("i"))))
        self.assertEqual(loop[5][3], ("Assign", Ix("A", B("+", N("i"), I(1))), N("key")))

    def test_mergesort_calls_are_siblings_of_the_floor_assignment(self) -> None:
        proc = body("mergesort.clrs")
        guard = proc[3][0]
        self.assertEqual(guard[:2], ("If", C("<", N("p"), N("r"))))
        self.assertEqual(guard[3], ())
        self.assertEqual(
            guard[2],
            (
                ("Assign", N("q"), ("FloorDiv", B("+", N("p"), N("r")), I(2))),
                ("ExprStmt", ("Call", "MergeSort", (N("A"), N("p"), N("q")), "paren")),
                ("ExprStmt", ("Call", "MergeSort", (N("A"), B("+", N("q"), I(1)), N("r")), "paren")),
                ("ExprStmt", ("Call", "Merge", (N("A"), N("p"), N("q"), N("r")), "paren")),
            ),
        )

    def test_original_mergesort_indents_under_an_assignment(self) -> None:
        source = (
            "Module Clrs.Sorting\n\nMergeSort(A, p, r)\n\tif p < r then\n"
            "\t\tq ← ⌊(p + r)/2⌋ ▷ midpoint\n\t\t\tMergeSort(A, p, q)\n"
        )
        self.assertModuleError(
            source,
            'Indented under "q ← ⌊(p + r)/2⌋", which does not open a block.',
            6,
            4,
        )

    def test_linear_search_fails_on_line_five(self) -> None:
        self.assertModuleError(
            (EXAMPLES / "linear-search.clrs").read_text(), FOR_END_MESSAGE, 5, 22
        )

    def test_linear_search_without_direction_fails_on_line_five(self) -> None:
        source = (EXAMPLES / "linear-search.clrs").read_text().replace("length[A] to", "length[A]")
        self.assertModuleError(source, FOR_DIRECTION_MESSAGE, 5, 19)

    def test_merge_allocates_and_stores_infinity(self) -> None:
        proc = body("merge.clrs")
        self.assertEqual(proc[2], ("A", "p", "q", "r"))
        steps = proc[3]
        self.assertEqual(steps[0], ("Assign", N("n_1"), B("+", B("-", N("q"), N("p")), I(1))))
        self.assertEqual(steps[2], ("Assign", N("L"), ("Alloc", B("+", N("n_1"), I(1)))))
        self.assertEqual(steps[6], ("Assign", Ix("L", B("+", N("n_1"), I(1))), ("InfinityLiteral",)))
        self.assertEqual(
            steps[4][5][0],
            ("Assign", Ix("L", N("i")), Ix("A", B("-", B("+", N("p"), N("i")), I(1)))),
        )
        merge_loop = steps[10]
        self.assertEqual(merge_loop[:5], ("ForLoop", "k", N("p"), "CountUp", N("r")))
        branch = merge_loop[5][0]
        self.assertEqual(branch[1], C("<", Ix("L", N("i")), Ix("R", N("i"))))
        self.assertEqual(branch[3][1], ("Assign", N("j"), B("+", N("j"), I(1))))

    def test_bubblesort_exchanges_two_indexes_and_counts_down(self) -> None:
        proc = body("bubblesort.clrs")
        outer = proc[3][0]
        inner = outer[5][0]
        self.assertEqual(inner[:5], ("ForLoop", "j", ("Attribute", "length", N("A")), "CountDown", B("+", N("i"), I(1))))
        self.assertEqual(
            inner[5][0][2][0],
            ("Exchange", Ix("A", N("j")), Ix("A", B("-", N("j"), I(1)))),
        )

    def test_heap_datatype(self) -> None:
        heap = body("heap.clrs")
        self.assertEqual(heap[:3], ("Datatype", "Heap", "Array"))
        default, left, right = heap[3]
        self.assertEqual(default, ("AttributeDefault", "contains", I(0)))
        twice = B("*", B("+", N("i"), I(1)), I(2))
        self.assertEqual(left, ("Method", "left", ("A", "i"), (("Return", B("-", twice, I(1))),)))
        self.assertEqual(right, ("Method", "right", ("A", "i"), (("Return", twice),)))

    def test_max_heapify_calls_attributes_and_indexes(self) -> None:
        steps = body("max-heapify.clrs")[3]
        self.assertEqual(steps[0], ("Assign", N("l"), ("Call", "left", (N("A"), N("i")), "bracket")))
        self.assertEqual(
            steps[2][1],
            ("And", C("<=", N("l"), ("Attribute", "contains", N("A"))), C(">", Ix("A", N("l")), Ix("A", N("i")))),
        )
        self.assertEqual(steps[2][3], (("Assign", N("largest"), N("i")),))
        self.assertEqual(steps[4][1], C("!=", N("largest"), N("i")))

    def test_build_max_heap_stores_an_attribute_and_floors(self) -> None:
        steps = body("build-max-heap.clrs")[3]
        self.assertEqual(
            steps[0],
            ("Assign", ("Attribute", "contains", N("A")), ("Attribute", "length", N("A"))),
        )
        self.assertEqual(
            steps[1][:5],
            ("ForLoop", "i", ("FloorDiv", ("Attribute", "length", N("A")), I(2)), "CountDown", I(1)),
        )

    def test_heapsort(self) -> None:
        steps = body("heapsort.clrs")[3]
        self.assertEqual(steps[0], ("ExprStmt", ("Call", "BuildMaxHeap", (N("A"),), "paren")))
        contains = ("Attribute", "contains", N("A"))
        self.assertEqual(steps[1][5][1], ("Assign", contains, B("-", contains, I(1))))

    def test_module_name_and_positions(self) -> None:
        module = parse_module((EXAMPLES / "insertion-sort.clrs").read_text())
        self.assertEqual((module.name, module.line, module.column), ("Clrs.Sorting", 1, 1))
        proc = module.definitions[0]
        self.assertEqual((proc.line, proc.column), (3, 1))
        loop = proc.body[0]
        self.assertEqual((loop.line, loop.column), (4, 2))
        self.assertEqual((loop.body[0].line, loop.body[0].column), (5, 3))


class PrecedenceTest(unittest.TestCase):
    def test_minus_then_plus_is_left_associative(self) -> None:
        self.assertEqual(expr("q - p + 1"), B("+", B("-", N("q"), N("p")), I(1)))
        self.assertEqual(expr("a - b - c"), B("-", B("-", N("a"), N("b")), N("c")))

    def test_times_binds_tighter_than_plus(self) -> None:
        self.assertEqual(expr("i + 1 * 2"), B("+", N("i"), B("*", I(1), I(2))))
        self.assertEqual(expr("a * b * c"), B("*", B("*", N("a"), N("b")), N("c")))
        self.assertEqual(expr("a * b - c"), B("-", B("*", N("a"), N("b")), N("c")))

    def test_parentheses_override(self) -> None:
        self.assertEqual(expr("(i + 1) * 2"), B("*", B("+", N("i"), I(1)), I(2)))

    def test_unary_minus_binds_tightest(self) -> None:
        self.assertEqual(expr("-x * y"), B("*", ("UnaryMinus", N("x")), N("y")))
        self.assertEqual(expr("--x"), ("UnaryMinus", ("UnaryMinus", N("x"))))
        self.assertEqual(expr("a - -1"), B("-", N("a"), ("UnaryMinus", I(1))))

    def test_and_is_looser_than_comparison(self) -> None:
        self.assertEqual(
            expr("i > 0 and A[i] > key"),
            ("And", C(">", N("i"), I(0)), C(">", ("Attribute", "A", N("i")), N("key"))),
        )

    def test_and_is_left_associative(self) -> None:
        self.assertEqual(expr("a and b and c"), ("And", ("And", N("a"), N("b")), N("c")))

    def test_comparison_is_looser_than_arithmetic(self) -> None:
        self.assertEqual(expr("a + 1 <= b * 2"), C("<=", B("+", N("a"), I(1)), B("*", N("b"), I(2))))

    def test_every_comparison_operator(self) -> None:
        for source, operator in (
            ("a < b", "<"), ("a > b", ">"), ("a <= b", "<="), ("a ≤ b", "<="),
            ("a >= b", ">="), ("a ≥ b", ">="), ("a = b", "="), ("a != b", "!="), ("a ≠ b", "!="),
        ):
            with self.subTest(source=source):
                self.assertEqual(expr(source), C(operator, N("a"), N("b")))

    def test_floor_of_a_division(self) -> None:
        self.assertEqual(expr("⌊(p + r)/2⌋"), ("FloorDiv", B("+", N("p"), N("r")), I(2)))
        self.assertEqual(expr("|.-3/2.|"), ("FloorDiv", ("UnaryMinus", I(3)), I(2)))
        self.assertEqual(expr("⌊a * b/c + 1⌋"), ("FloorDiv", B("*", N("a"), N("b")), B("+", N("c"), I(1))))
        self.assertEqual(expr("⌊a/2⌋ + 1"), B("+", ("FloorDiv", N("a"), I(2)), I(1)))

    def test_literals(self) -> None:
        self.assertEqual(expr("True"), ("BooleanLiteral", True))
        self.assertEqual(expr("False"), ("BooleanLiteral", False))
        self.assertEqual(expr("nil"), ("NilLiteral",))
        self.assertEqual(expr("NIL"), ("NilLiteral",))
        self.assertEqual(expr("∞"), ("InfinityLiteral",))
        self.assertEqual(expr("42"), I(42))

    def test_literal_positions(self) -> None:
        literals = parse_driver("F(\n 12, nil, ∞, True, False)").result.arguments
        self.assertEqual(
            [(node.line, node.column) for node in literals],
            [(2, 2), (2, 6), (2, 11), (2, 14), (2, 20)],
        )

    def test_operator_positions(self) -> None:
        result = parse_driver("q - p + 1").result
        self.assertEqual((result.line, result.column), (1, 7))
        self.assertEqual((result.left.line, result.left.column), (1, 3))


class ArrayTest(unittest.TestCase):
    def test_single_expression_allocates(self) -> None:
        self.assertEqual(expr("[5]"), ("Alloc", I(5)))
        self.assertEqual(expr("[n_1 + 1]"), ("Alloc", B("+", N("n_1"), I(1))))

    def test_comma_list_is_a_literal(self) -> None:
        self.assertEqual(expr("[5, 2, 4, 6, 1, 3]"), ("ArrayLiteral", tuple(I(v) for v in (5, 2, 4, 6, 1, 3))))

    def test_trailing_comma_is_a_one_element_literal(self) -> None:
        self.assertEqual(expr("[5,]"), ("ArrayLiteral", (I(5),)))
        self.assertEqual(expr("[5, 2,]"), ("ArrayLiteral", (I(5), I(2))))

    def test_empty_brackets_are_an_empty_literal(self) -> None:
        self.assertEqual(expr("[]"), ("ArrayLiteral", ()))

    def test_array_positions(self) -> None:
        for source in ("x ← 1; [x]", "x ← 1; [x,]", "x ← 1; []"):
            with self.subTest(source=source):
                result = parse_driver(source).result
                self.assertEqual((result.line, result.column), (1, 8))


class BracketTest(unittest.TestCase):
    def test_comma_makes_a_call(self) -> None:
        self.assertEqual(expr("left[A, i]"), ("Call", "left", (N("A"), N("i")), "bracket"))
        self.assertEqual(expr("f[a, b, c]"), ("Call", "f", (N("a"), N("b"), N("c")), "bracket"))

    def test_local_makes_an_index(self) -> None:
        driver = parse_driver("A ← [3]; A[1]")
        self.assertEqual(shape(driver.result), Ix("A", I(1)))
        self.assertEqual((driver.result.line, driver.result.column), (1, 10))

    def test_non_local_single_bracket_is_an_attribute_not_a_call(self) -> None:
        driver = parse_driver("A ← [3]; contains[A]")
        self.assertEqual(shape(driver.result), ("Attribute", "contains", N("A")))
        self.assertEqual((driver.result.line, driver.result.column), (1, 10))

    def test_local_shadows_an_attribute(self) -> None:
        proc = procedure("P(A)\n\tcontains ← [2]\n\treturn contains[A]\n")
        self.assertEqual(proc[3][1], ("Return", Ix("contains", N("A"))))

    def test_parameter_is_local(self) -> None:
        proc = procedure("P(A, i)\n\treturn A[i]\n")
        self.assertEqual(proc[3][0], ("Return", Ix("A", N("i"))))

    def test_for_variable_is_local_in_its_body(self) -> None:
        proc = procedure("P(A)\n\tfor k ← 1 to 2 do\n\t\tA[1] ← k[1]\n")
        self.assertEqual(proc[3][0][5][0][2], Ix("k", I(1)))

    def test_paren_calls(self) -> None:
        self.assertEqual(expr("F()"), ("Call", "F", (), "paren"))
        self.assertEqual(expr("F(1, x + 1)"), ("Call", "F", (I(1), B("+", N("x"), I(1))), "paren"))
        result = parse_driver("  F(1)").result
        self.assertEqual((result.line, result.column), (1, 3))


class StatementTest(CompileErrorCase):
    def test_optional_keywords(self) -> None:
        with_words = procedure("P(a):\n\tfor i ← 1 to a do\n\t\twhile a do\n\t\t\tif a then\n\t\t\t\treturn 1\n")
        without = procedure("P(a)\n\tfor i ← 1 to a\n\t\twhile a\n\t\t\tif a\n\t\t\t\treturn 1\n")
        self.assertEqual(with_words, without)
        self.assertEqual(with_words[3][0][5][0][0], "WhileLoop")

    def test_if_else(self) -> None:
        proc = procedure("P(a)\n\tif a then\n\t\tx ← 1\n\telse\n\t\tx ← 2\n\treturn x\n")
        self.assertEqual(
            proc[3],
            (
                ("If", N("a"), (("Assign", N("x"), I(1)),), (("Assign", N("x"), I(2)),)),
                ("Return", N("x")),
            ),
        )

    def test_empty_parameter_lists(self) -> None:
        self.assertEqual(procedure("P()\n\treturn 1\n")[2], ())
        datatype = shape(parse_module("Module M\ndatatype H extends Array:\n\tm[]:\n\t\treturn 1\n").definitions[0])
        self.assertEqual(datatype[3][0][2], ())

    def test_several_definitions(self) -> None:
        module = parse_module("Module A.B.C\nP()\n\treturn 1\nQ(x)\n\treturn x\n")
        self.assertEqual(module.name, "A.B.C")
        self.assertEqual([d.name for d in module.definitions], ["P", "Q"])
        self.assertEqual((module.definitions[1].line, module.definitions[1].column), (4, 1))

    def test_positions_of_statements(self) -> None:
        proc = parse_module("Module M\nP(A)\n\tA[1] ↔ A[2]\n\tF(A)\n\treturn 1\n").definitions[0]
        self.assertEqual([(s.line, s.column) for s in proc.body], [(3, 2), (4, 2), (5, 2)])
        datatype = parse_module("Module M\ndatatype H extends Array:\n\tc ← 0\n\tm[]:\n\t\treturn 1\n").definitions[0]
        self.assertEqual((datatype.line, datatype.column), (2, 1))
        self.assertEqual([(m.line, m.column) for m in datatype.members], [(3, 2), (4, 2)])

    def test_for_without_assign(self) -> None:
        self.assertModuleError("Module M\nP()\n\tfor i to 3\n\t\treturn 1\n", "Expected ← but found 'to'.", 3, 8)

    def test_missing_module_header(self) -> None:
        self.assertModuleError("P()\n\treturn 1\n", "Expected Module but found 'P'.", 1, 1)

    def test_definition_must_be_a_name_or_datatype(self) -> None:
        self.assertModuleError("Module M\n5\n", "Expected a definition but found '5'.", 2, 1)

    def test_datatype_member_must_assign_or_bracket(self) -> None:
        self.assertModuleError(
            "Module M\ndatatype H extends Array:\n\tx + 1\n", "Expected a datatype member but found '+'.", 3, 4
        )

    def test_statement_must_start_with_a_known_word(self) -> None:
        self.assertModuleError("Module M\nP()\n\t5\n", "Expected a statement but found '5'.", 3, 2)

    def test_bare_name_is_not_a_statement(self) -> None:
        self.assertModuleError("Module M\nP()\n\tx + 1\n", "Expected a statement but found 'x + 1'.", 3, 7)

    def test_value_cannot_be_assigned(self) -> None:
        self.assertModuleError("Module M\nP()\n\tF(x) ← 1\n", TARGET_MESSAGE, 3, 9)
        self.assertModuleError("Module M\nP(A)\n\tA[1] ↔ 2\n", TARGET_MESSAGE, 3, 10)

    def test_header_after_simple_statement_still_needs_indent(self) -> None:
        self.assertModuleError("Module M\nP()\n\tif a then\n\treturn 1\n", "Expected indent but found 'return'.", 4, 2)


class LengthTest(CompileErrorCase):
    def test_length_cannot_be_a_parameter(self) -> None:
        self.assertModuleError("Module M\nP(A, length)\n\treturn 1\n", LENGTH_MESSAGE, 2, 6)

    def test_length_cannot_be_assigned(self) -> None:
        self.assertDriverError("length ← 3; 1", LENGTH_MESSAGE, 1, 1)

    def test_length_attribute_cannot_be_stored(self) -> None:
        self.assertDriverError("A ← [1]; length[A] ← 2; 1", LENGTH_MESSAGE, 1, 10)

    def test_length_cannot_be_exchanged(self) -> None:
        self.assertDriverError("A ← [1]; A[1] ↔ length; 1", LENGTH_MESSAGE, 1, 17)

    def test_length_cannot_be_a_loop_variable(self) -> None:
        self.assertModuleError("Module M\nP()\n\tfor length ← 1 to 2\n\t\treturn 1\n", LENGTH_MESSAGE, 3, 6)

    def test_length_cannot_be_a_datatype_member(self) -> None:
        self.assertModuleError("Module M\ndatatype H extends Array:\n\tlength ← 0\n", LENGTH_MESSAGE, 3, 2)


class RejectedOperatorTest(CompileErrorCase):
    def test_comparisons_do_not_chain(self) -> None:
        self.assertDriverError("a < b < c", CHAIN_MESSAGE, 1, 7)
        self.assertDriverError("a = b != c", CHAIN_MESSAGE, 1, 7)

    def test_or_is_rejected(self) -> None:
        self.assertDriverError("a and b or c", OR_MESSAGE, 1, 9)

    def test_ceiling_is_rejected(self) -> None:
        self.assertDriverError("1 + ⌈a/2⌉", CEILING_MESSAGE, 1, 5)

    def test_bare_floor_is_rejected(self) -> None:
        self.assertDriverError("x + |.x.|", FLOOR_MESSAGE, 1, 5)

    def test_slash_outside_floor_is_rejected(self) -> None:
        self.assertDriverError("x / 2", SLASH_MESSAGE, 1, 3)
        self.assertDriverError("F(a * b / 2)", SLASH_MESSAGE, 1, 9)
        self.assertDriverError("a and b / 2", SLASH_MESSAGE, 1, 9)

    def test_floor_needs_its_closing_bracket(self) -> None:
        self.assertDriverError("⌊a/2", "Expected ⌋ but found ''.", 1, 1)

    def test_expression_required(self) -> None:
        self.assertDriverError("", "Expected an expression but found ''.", 1, 1)
        self.assertDriverError("x ← ;1", "Expected an expression but found ';'.", 1, 5)


class DriverTest(CompileErrorCase):
    def test_statements_then_expression(self) -> None:
        driver = parse_driver("A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A")
        self.assertEqual(
            shape(driver),
            (
                "Driver",
                (
                    ("Assign", N("A"), ("ArrayLiteral", tuple(I(v) for v in (5, 2, 4, 6, 1, 3)))),
                    ("ExprStmt", ("Call", "InsertionSort", (N("A"),), "paren")),
                ),
                N("A"),
            ),
        )

    def test_driver_may_span_lines(self) -> None:
        driver = parse_driver("A ← [4, 1, 3]\n; BuildMaxHeap(A)\n; contains[A]")
        self.assertEqual(shape(driver.result), ("Attribute", "contains", N("A")))
        self.assertEqual(driver.result.line, 3)

    def test_expression_only_driver(self) -> None:
        driver = parse_driver("  left[[1, 2, 3, 4], 1]")
        self.assertEqual(shape(driver.statements), ())
        self.assertEqual((driver.line, driver.column), (1, 3))

    def test_driver_anchors_at_first_statement(self) -> None:
        driver = parse_driver("x ← 1;\n  x")
        self.assertEqual((driver.line, driver.column), (1, 1))

    def test_driver_ends_with_an_expression(self) -> None:
        self.assertDriverError("x ← 1; x ← 2", "Expected end of file but found '←'.", 1, 10)
        self.assertDriverError("1; 2", "Expected a statement but found '1'.", 1, 1)

    def test_bare_name_statement_in_driver(self) -> None:
        self.assertDriverError("x; 2", "Expected a statement but found ';'.", 1, 2)


class NodeTest(unittest.TestCase):
    def test_every_node_is_frozen_and_dispatches_to_its_own_visit(self) -> None:
        nodes = [
            obj for obj in vars(ast).values()
            if isinstance(obj, type) and dataclasses.is_dataclass(obj)
        ]
        self.assertEqual(len(nodes), 28)

        class Recorder:
            def __getattr__(self, name: str) -> object:
                return lambda node: (name, type(node).__name__)

        for cls in nodes:
            with self.subTest(node=cls.__name__):
                values = {f.name: 0 for f in dataclasses.fields(cls)}
                node = cls(**values)
                self.assertEqual(node.accept(Recorder()), ("visit_" + cls.__name__.lower(), cls.__name__))
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    node.line = 2  # type: ignore[misc]

    def test_directions_label_their_count(self) -> None:
        loops = procedure("P()\n\tfor i ← 1 to 2\n\t\tF(i)\n\tfor i ← 2 downto 1\n\t\tF(i)\n")[3]
        self.assertEqual([loop[3] for loop in loops], ["CountUp", "CountDown"])
        module = parse_module("Module M\nP()\n\tfor i ← 1 to 2\n\t\tF(i)\n\tfor i ← 2 downto 1\n\t\tF(i)\n")
        self.assertEqual([loop.direction.label() for loop in module.definitions[0].body], ["up", "down"])


if __name__ == "__main__":
    unittest.main()
