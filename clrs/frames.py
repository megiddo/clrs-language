"""Pattern: Entity. Activation frames and the explicit frame stack the machine runs on."""

from clrs.bytecode import Instruction
from clrs.bytecode import Routine
from clrs.decisions import DecisionLog
from clrs.values import UNASSIGNED

MAX_FRAMES = 10000


class Frame:
    """Pattern: Entity. One activation: local slots, an operand stack, and a program counter."""

    def __init__(self, routine: Routine, arguments: tuple[object, ...], log: DecisionLog) -> None:
        self._routine = routine
        self._log = log
        self._slots = {name: UNASSIGNED for name in routine.locals}
        for name, value in zip(routine.locals, arguments):
            self._slots[name] = value
        self._operands: list[object] = []
        self._counter = 0

    def name(self) -> str:
        return self._routine.name or "the driver"

    def fetch(self) -> Instruction:
        if self._counter >= len(self._routine.instructions):
            self._log.fault("fall", f"{self.name()} ran past its last instruction.")
        instruction = self._routine.instructions[self._counter]
        self._counter += 1
        return instruction

    def jump(self, index: int) -> None:
        self._counter = index

    def push(self, value: object) -> None:
        self._operands.append(value)

    def pop(self) -> object:
        if len(self._operands) == 0:
            self._log.fault("underflow", f"The operand stack of {self.name()} is empty.")
        return self._operands.pop()

    def pop_many(self, count: int) -> tuple[object, ...]:
        values = [self.pop() for _ in range(count)]
        return tuple(reversed(values))

    def load(self, name: str) -> object:
        value = self._slots[name]
        if value is UNASSIGNED:
            self._log.fault("unassigned", f"{name} is read before it is assigned.")
        return value

    def store(self, name: str, value: object) -> None:
        self._slots[name] = value


class FrameStack:
    """Pattern: Entity. The call stack as data, so a CLRS call never recurses in Python."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._frames: list[Frame] = []

    def push(self, frame: Frame) -> None:
        if len(self._frames) >= MAX_FRAMES:
            self._log.fault("depth", f"More than {MAX_FRAMES} calls are active.")
        self._frames.append(frame)

    def pop(self) -> Frame:
        return self._frames.pop()

    def top(self) -> Frame:
        return self._frames[-1]

    def empty(self) -> bool:
        return len(self._frames) == 0
