"""Machine semantics through the Engine: pointers, scalars, short-circuit, floor, ∞, nil, faults."""

import sys
import unittest

from clrs import Engine
from clrs import RuntimeFault
from clrs.values import INFINITY
from clrs.values import NIL
from clrs.values import ClrsArray

PROCEDURES = """Module Clrs.Test

Rebind(A)
\tA ← [9, 9]
\treturn 0

Poke(A)
\tA[1] ← 9

Bump(n)
\tn ← n + 1

Mark(A)
\tcontains[A] ← 7

Last()
\tfor i ← 1 to 3 do
\t\tx ← i
\treturn i

First()
\tfor i ← 3 downto 1 do
\t\tx ← i
\treturn i

Shrink(n)
\tc ← 0
\tfor i ← 1 to n do
\t\tn ← n - 1
\t\tc ← c + 1
\treturn c

Never()
\tif False then
\t\tx ← 1
\treturn x

Down(n)
\tif n > 0 then
\t\treturn Down(n - 1)
\treturn 0

Fact(n)
\tif n = 0 then
\t\treturn 1
\treturn n * Fact(n - 1)

Ignore(a, b, c)
\treturn 0
"""


def machine() -> Engine:
    engine = Engine()
    engine.load_source(PROCEDURES)
    return engine


def items(value: object) -> tuple[object, ...]:
    assert isinstance(value, ClrsArray)
    return value.items()


class FaultCase(unittest.TestCase):
    def fault(self, driver: str) -> str:
        with self.assertRaises(RuntimeFault) as caught:
            machine().run(driver)
        return caught.exception.message


class PointerTest(unittest.TestCase):
    def test_parameter_rebind_is_invisible(self) -> None:
        self.assertEqual(items(machine().run("A ← [1, 2]; Rebind(A); A")), (1, 2))

    def test_element_write_is_visible(self) -> None:
        self.assertEqual(items(machine().run("A ← [1, 2]; Poke(A); A")), (9, 2))

    def test_scalar_argument_is_a_value(self) -> None:
        self.assertEqual(machine().run("n ← 1; Bump(n); n"), 1)

    def test_attribute_write_is_visible(self) -> None:
        self.assertEqual(machine().run("A ← [1]; Mark(A); contains[A]"), 7)

    def test_aliases_share_one_array(self) -> None:
        self.assertEqual(items(machine().run("A ← [1, 2]; B ← A; B[2] ← 5; A")), (1, 5))


class ShortCircuitTest(FaultCase):
    def test_and_does_not_read_index_zero(self) -> None:
        self.assertIs(machine().run("i ← 0; A ← [1,]; i > 0 and A[i] > 0"), False)

    def test_index_zero_would_fault(self) -> None:
        self.assertEqual(self.fault("i ← 0; A ← [1,]; A[i] > 0"), "Index 0 is outside 1 to 1.")

    def test_and_reads_right_when_left_holds(self) -> None:
        self.assertIs(machine().run("i ← 1; A ← [1,]; i > 0 and A[i] > 0"), True)
        self.assertIs(machine().run("i ← 1; A ← [1,]; i > 0 and A[i] > 1"), False)


class ArithmeticTest(FaultCase):
    def test_floor_of_negative_quotient(self) -> None:
        self.assertEqual(machine().run("⌊-3/2⌋"), -2)

    def test_floor_divisions(self) -> None:
        cases = {"⌊3/2⌋": 1, "⌊-4/2⌋": -2, "⌊7/-2⌋": -4, "⌊(1 + 6)/2⌋": 3}
        for driver, expected in cases.items():
            self.assertEqual(machine().run(driver), expected, driver)

    def test_associativity_and_precedence(self) -> None:
        cases = {"10 - 3 - 2": 5, "q ← 5; p ← 2; q - p + 1": 4, "1 + 2 * 3": 7, "2 * 3 - 1": 5}
        for driver, expected in cases.items():
            self.assertEqual(machine().run(driver), expected, driver)

    def test_unary_minus(self) -> None:
        self.assertEqual(machine().run("x ← 4; -x"), -4)

    def test_division_by_zero(self) -> None:
        self.assertEqual(self.fault("⌊5/0⌋"), "Division by zero.")

    def test_arithmetic_needs_integers(self) -> None:
        cases = {
            "True + 1": "+ needs two integers, not a boolean and an integer.",
            "1 - ∞": "- needs two integers, not an integer and ∞.",
            "NIL * 2": "* needs two integers, not NIL and an integer.",
            "A ← [1]; ⌊A/2⌋": "/ needs two integers, not an array and an integer.",
        }
        for driver, message in cases.items():
            self.assertEqual(self.fault(driver), message, driver)


class ComparisonTest(FaultCase):
    def test_infinity_is_above_every_integer(self) -> None:
        for driver in ("∞ > 1000000000000000000000", "-5 < ∞", "∞ >= 0", "∞ = ∞", "∞ != 3"):
            self.assertIs(machine().run(driver), True, driver)
        for driver in ("∞ < ∞", "∞ <= 99", "∞ = 7", "∞ > ∞"):
            self.assertIs(machine().run(driver), False, driver)

    def test_integer_comparisons(self) -> None:
        cases = {"1 < 2": True, "2 < 1": False, "2 <= 2": True, "3 >= 4": False, "2 = 2": True}
        cases |= {"2 != 2": False, "3 > 2": True, "2 > 2": False}
        for driver, expected in cases.items():
            self.assertIs(machine().run(driver), expected, driver)

    def test_booleans_and_arrays_test_equality(self) -> None:
        cases = {"True = True": True, "True != False": True, "False = True": False}
        cases |= {"A ← [1]; B ← A; A = B": True, "A ← [1,]; A = [1,]": False}
        cases |= {"A ← [1,]; A != [1,]": True}
        for driver, expected in cases.items():
            self.assertIs(machine().run(driver), expected, driver)

    def test_nil_does_not_compare(self) -> None:
        for driver in ("NIL = NIL", "1 < NIL", "A ← [1]; NIL != A"):
            self.assertEqual(self.fault(driver), "NIL cannot be compared.", driver)

    def test_ordering_and_mixed_faults(self) -> None:
        cases = {
            "True < False": "lt needs integers or ∞, not a boolean and a boolean.",
            "A ← [1]; A >= 1": "ge needs integers or ∞, not an array and an integer.",
            "1 = True": "eq cannot compare an integer with a boolean.",
            "A ← [1]; False != A": "ne cannot compare a boolean with an array.",
        }
        for driver, message in cases.items():
            self.assertEqual(self.fault(driver), message, driver)

    def test_condition_must_be_boolean(self) -> None:
        source = "Module M\nP()\n\tif 1 then\n\t\treturn 1\n\treturn 0\n"
        engine = Engine()
        engine.load_source(source)
        with self.assertRaises(RuntimeFault) as caught:
            engine.run("P()")
        self.assertEqual(caught.exception.message, "A condition must be a boolean, not an integer.")


class LoopTest(unittest.TestCase):
    def test_loop_variable_survives(self) -> None:
        self.assertEqual(machine().run("Last()"), 4)
        self.assertEqual(machine().run("First()"), 0)

    def test_for_rereads_its_end_each_iteration(self) -> None:
        self.assertEqual(machine().run("Shrink(6)"), 3)


class ArrayTest(FaultCase):
    def test_allocation_is_nil_slots(self) -> None:
        self.assertEqual(items(machine().run("n ← 2; [n + 1]")), (NIL, NIL, NIL))
        self.assertEqual(items(machine().run("[0]")), ())

    def test_literals(self) -> None:
        self.assertEqual(items(machine().run("[5, 2, 4]")), (5, 2, 4))
        self.assertEqual(items(machine().run("[5,]")), (5,))
        self.assertEqual(items(machine().run("[]")), ())
        self.assertEqual(items(machine().run("[True, NIL, ∞]")), (True, NIL, INFINITY))

    def test_length_is_structural(self) -> None:
        self.assertEqual(machine().run("A ← [4]; length[A]"), 4)
        self.assertEqual(machine().run("A ← [7, 8]; length[A]"), 2)

    def test_fresh_array_has_no_contains_until_written(self) -> None:
        message = "contains has not been set on this array."
        self.assertEqual(self.fault("A ← [1, 2]; contains[A]"), message)
        self.assertEqual(machine().run("A ← [1, 2]; contains[A] ← 2; contains[A]"), 2)

    def test_reading_a_nil_slot_is_nil(self) -> None:
        self.assertIs(machine().run("A ← [2]; A[2]"), NIL)

    def test_bad_sizes(self) -> None:
        cases = {
            "[-1]": "An array size must be a non-negative integer, not -1.",
            "[True]": "An array size must be a non-negative integer, not True.",
            "[∞]": "An array size must be a non-negative integer, not ∞.",
        }
        for driver, message in cases.items():
            self.assertEqual(self.fault(driver), message, driver)

    def test_bad_indexes(self) -> None:
        cases = {
            "A ← [1, 2]; A[3]": "Index 3 is outside 1 to 2.",
            "A ← [1, 2]; A[0] ← 1; A": "Index 0 is outside 1 to 2.",
            "A ← [1, 2]; A[3] ← 1; A": "Index 3 is outside 1 to 2.",
            "A ← [1]; A[True]": "An index must be an integer, not a boolean.",
            "A ← [1]; A[∞] ← 2; A": "An index must be an integer, not ∞.",
            "x ← 1; x[1]": "Indexing needs an array, not an integer.",
            "x ← NIL; x[1] ← 2; x": "Indexing needs an array, not NIL.",
            "x ← 1; length[x]": "length needs an array, not an integer.",
            "x ← True; contains[x] ← 1; x": "contains needs an array, not a boolean.",
        }
        for driver, message in cases.items():
            self.assertEqual(self.fault(driver), message, driver)

    def test_last_index_is_in_bounds(self) -> None:
        self.assertEqual(items(machine().run("A ← [1, 2]; A[2] ← 7; A")), (1, 7))


class CallTest(FaultCase):
    def test_unassigned_local_is_not_nil(self) -> None:
        self.assertEqual(self.fault("Never()"), "x is read before it is assigned.")
        self.assertIs(machine().run("x ← NIL; x"), NIL)

    def test_returns_and_nested_calls(self) -> None:
        self.assertEqual(machine().run("Fact(5)"), 120)
        self.assertIs(machine().run("A ← [1]; Poke(A)"), NIL)

    def test_deep_calls_do_not_use_python_recursion(self) -> None:
        depth = sys.getrecursionlimit() * 5
        self.assertEqual(machine().run(f"Down({depth})"), 0)

    def test_frame_limit(self) -> None:
        self.assertEqual(machine().run("Down(9998)"), 0)
        self.assertEqual(self.fault("Down(9999)"), "More than 10000 calls are active.")

    def test_unknown_procedure(self) -> None:
        self.assertEqual(self.fault("Nope(1)"), "Nope is not a loaded procedure.")

    def test_arity(self) -> None:
        self.assertEqual(machine().run("Ignore(1, 2, 3)"), 0)
        self.assertEqual(self.fault("Fact(1, 2)"), "Fact takes at most 1 argument(s), not 2.")

    def test_arguments_bind_in_order(self) -> None:
        source = "Module M\nMinus(a, b)\n\treturn a - b\n"
        engine = Engine()
        engine.load_source(source)
        self.assertEqual(engine.run("Minus(10, 3)"), 7)

    def test_module_does_not_run(self) -> None:
        engine = Engine()
        engine.load_source("Module M\nBoom()\n\treturn 1 + True\n")
        self.assertEqual(engine.modules(), ("M",))


if __name__ == "__main__":
    unittest.main()
