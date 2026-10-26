"""Pattern: Value Object. Runtime values: integers, booleans, ∞, nil, unassigned, and arrays."""

from clrs.bytecode import BooleanConstant
from clrs.bytecode import InfinityConstant
from clrs.bytecode import IntegerConstant
from clrs.bytecode import NilConstant


class Infinity:
    """Pattern: Value Object. The single ∞, above every integer and equal only to itself."""

    def __repr__(self) -> str:
        return "∞"


class Nil:
    """Pattern: Null Object. The single nil; it is not an integer and does not compare."""

    def __repr__(self) -> str:
        return "NIL"


class Unassigned:
    """Pattern: Null Object. A local slot that has never been stored; distinct from nil."""

    def __repr__(self) -> str:
        return "unassigned"


INFINITY = Infinity()
NIL = Nil()
UNASSIGNED = Unassigned()


class ClrsArray:
    """Pattern: Entity. A 1-based array with a fixed length and its own attribute record."""

    def __init__(self, slots: list[object]) -> None:
        self._slots = slots
        self._attributes: dict[str, object] = {}

    def length(self) -> int:
        return len(self._slots)

    def holds(self, index: int) -> bool:
        return 1 <= index <= len(self._slots)

    def get(self, index: int) -> object:
        return self._slots[index - 1]

    def put(self, index: int, value: object) -> None:
        self._slots[index - 1] = value

    def has(self, name: str) -> bool:
        return name in self._attributes

    def attribute(self, name: str) -> object:
        return self._attributes[name]

    def set_attribute(self, name: str, value: object) -> None:
        self._attributes[name] = value

    def items(self) -> tuple[object, ...]:
        return tuple(self._slots)

    def __repr__(self) -> str:
        return f"ClrsArray({list(self._slots)!r})"


def is_integer(value: object) -> bool:
    return type(value) is int


def is_boolean(value: object) -> bool:
    return type(value) is bool


def kind(value: object) -> str:
    if is_integer(value):
        return "an integer"
    if is_boolean(value):
        return "a boolean"
    if isinstance(value, ClrsArray):
        return "an array"
    return repr(value)


CONSTANT_VALUES = {
    NilConstant: lambda constant: NIL,
    InfinityConstant: lambda constant: INFINITY,
    IntegerConstant: lambda constant: constant.value,
    BooleanConstant: lambda constant: constant.value,
}


def constant_value(constant: object) -> object:
    return CONSTANT_VALUES[type(constant)](constant)  # type: ignore[no-untyped-call]
