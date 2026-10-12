"""Pattern: Command. Executors for ADD, SUB, MUL, FLOORDIV, and CMP over runtime values."""

import operator
from collections.abc import Callable

from clrs.bytecode import Instruction
from clrs.decisions import DecisionLog
from clrs.frames import Frame
from clrs.values import INFINITY
from clrs.values import NIL
from clrs.values import ClrsArray
from clrs.values import is_boolean
from clrs.values import is_integer
from clrs.values import kind

ORDERS: dict[str, Callable[[object, object], bool]] = {
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
}
EQUALITIES: dict[str, Callable[[object, object], bool]] = {"eq": operator.eq, "ne": operator.ne}


class Arithmetic:
    """Pattern: Command. Pops two integers and pushes one integer."""

    def __init__(self, symbol: str, apply: Callable[[int, int], int]) -> None:
        self._symbol = symbol
        self._apply = apply

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log: DecisionLog = machine.log  # type: ignore[attr-defined]
        right = frame.pop()
        left = frame.pop()
        if not (is_integer(left) and is_integer(right)):
            message = f"{self._symbol} needs two integers, not {kind(left)} and {kind(right)}."
            log.fault("arithmetic", message)
        self._check(log, right)
        frame.push(self._apply(left, right))  # type: ignore[arg-type]

    def _check(self, log: DecisionLog, right: object) -> None:
        return None


class FloorDivision(Arithmetic):
    """Pattern: Command. Integer division rounded toward negative infinity."""

    def __init__(self) -> None:
        super().__init__("/", operator.floordiv)

    def _check(self, log: DecisionLog, right: object) -> None:
        if right == 0:
            log.fault("zero", "Division by zero.")


def rank(value: object) -> tuple[int, int]:
    if value is INFINITY:
        return (1, 0)
    return (0, value)  # type: ignore[return-value]


def orderable(value: object) -> bool:
    return is_integer(value) or value is INFINITY


class Compare:
    """Pattern: Command. CMP: integers and ∞ order; booleans and arrays only test equality."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log: DecisionLog = machine.log  # type: ignore[attr-defined]
        right = frame.pop()
        left = frame.pop()
        frame.push(self.compare(log, str(instruction.operands[0]), left, right))

    def compare(self, log: DecisionLog, name: str, left: object, right: object) -> bool:
        if left is NIL or right is NIL:
            log.fault("nil", "NIL cannot be compared.")
        if orderable(left) and orderable(right):
            return self._order(log, name, left, right)
        if name in ORDERS:
            log.fault("order", f"{name} needs integers or ∞, not {kind(left)} and {kind(right)}.")
        if is_boolean(left) and is_boolean(right):
            log.record("compare", "boolean")
            return EQUALITIES[name](left, right)
        if isinstance(left, ClrsArray) and isinstance(right, ClrsArray):
            log.record("compare", "identity")
            return EQUALITIES[name](id(left), id(right))
        log.fault("mixed", f"{name} cannot compare {kind(left)} with {kind(right)}.")

    def _order(self, log: DecisionLog, name: str, left: object, right: object) -> bool:
        if left is INFINITY or right is INFINITY:
            log.record("compare", "infinity")
        else:
            log.record("compare", "integer")
        table = ORDERS | EQUALITIES
        return table[name](rank(left), rank(right))
