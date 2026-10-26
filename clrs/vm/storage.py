"""Pattern: Command. Executors for constants, locals, arrays, elements, and attributes."""

from clrs.bytecode import Instruction
from clrs.common.decisions import DecisionLog
from clrs.vm.frames import Frame
from clrs.vm.values import NIL
from clrs.vm.values import ClrsArray
from clrs.vm.values import constant_value
from clrs.vm.values import is_integer
from clrs.vm.values import kind

STRUCTURAL = "length"


def log_of(machine: object) -> DecisionLog:
    return machine.log  # type: ignore[attr-defined,no-any-return]


def array_of(log: DecisionLog, value: object, use: str) -> ClrsArray:
    if not isinstance(value, ClrsArray):
        log.fault("array", f"{use} needs an array, not {kind(value)}.")
    return value


def checked_index(log: DecisionLog, array: ClrsArray, index: object) -> int:
    if not is_integer(index):
        log.fault("index", f"An index must be an integer, not {kind(index)}.")
    if not array.holds(index):  # type: ignore[arg-type]
        log.fault("bounds", f"Index {index} is outside 1 to {array.length()}.")
    return index  # type: ignore[return-value]


class Constant:
    """Pattern: Command. CONST pushes the runtime value of its typed operand."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        frame.push(constant_value(instruction.operands[0]))


class Load:
    """Pattern: Command. LOAD pushes a local; an unassigned slot faults."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        frame.push(frame.load(str(instruction.operands[0])))


class Store:
    """Pattern: Command. STORE rebinds a local slot in this frame only."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        frame.store(str(instruction.operands[0]), frame.pop())


class Pop:
    """Pattern: Command. POP discards the value of an expression statement."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        frame.pop()


class Allocate:
    """Pattern: Command. ALLOC builds an array of that many nil slots."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = log_of(machine)
        size = frame.pop()
        if not is_integer(size) or size < 0:  # type: ignore[operator]
            log.fault("size", f"An array size must be a non-negative integer, not {size!r}.")
        frame.push(ClrsArray([NIL] * size))  # type: ignore[operator]


class Pack:
    """Pattern: Command. PACK n builds an array literal from the top n values in order."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        count = int(instruction.operands[0])  # type: ignore[call-overload]
        frame.push(ClrsArray(list(frame.pop_many(count))))


class LoadIndex:
    """Pattern: Command. LOAD_IDX reads one element of a 1-based array."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = log_of(machine)
        index = frame.pop()
        array = array_of(log, frame.pop(), "Indexing")
        frame.push(array.get(checked_index(log, array, index)))


class StoreIndex:
    """Pattern: Command. STORE_IDX writes an element; every holder of the array sees it."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = log_of(machine)
        value = frame.pop()
        index = frame.pop()
        array = array_of(log, frame.pop(), "Indexing")
        array.put(checked_index(log, array, index), value)


class LoadAttribute:
    """Pattern: Command. LOAD_ATTR: length is structural; any other name must be written first."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = log_of(machine)
        name = str(instruction.operands[0])
        array = array_of(log, frame.pop(), name)
        if name == STRUCTURAL:
            log.record("attribute", "length")
            frame.push(array.length())
            return
        if not array.has(name):
            log.fault("attribute", f"{name} has not been set on this array.")
        log.record("attribute", "stored")
        frame.push(array.attribute(name))


class StoreAttribute:
    """Pattern: Command. STORE_ATTR writes an array attribute; length cannot be stored."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = log_of(machine)
        name = str(instruction.operands[0])
        value = frame.pop()
        array = array_of(log, frame.pop(), name)
        if name == STRUCTURAL:
            log.fault("length", "length cannot be stored.")
        array.set_attribute(name, value)
