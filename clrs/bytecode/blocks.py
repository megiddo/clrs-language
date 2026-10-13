"""Pattern: Builder. One builder per open .clrsa block; a Null Object stands for no block."""

from typing import NoReturn

from clrs.bytecode import DatatypeRecord
from clrs.bytecode import Instruction
from clrs.bytecode import Opcode
from clrs.bytecode import Routine
from clrs.bytecode import Target
from clrs.common.decisions import DecisionLog
from clrs.bytecode.operands import OperandReader


class Block:
    """Pattern: Null Object. Accepts nothing; each block overrides what it allows."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log

    def place(self) -> str:
        return "outside a block"

    def _refuse(self, what: str, line: int) -> NoReturn:
        self._log.refuse("block", f"{what} cannot appear {self.place()}.", line)

    def open(self, directive: str, words: list[str], line: int) -> "Block":
        self._refuse(directive, line)

    def local(self, name: str, line: int) -> None:
        self._refuse(".local", line)

    def default(self, name: str, word: str, line: int) -> None:
        self._refuse(".default", line)

    def label(self, name: str, line: int) -> None:
        self._refuse("A label", line)

    def instruction(self, mnemonic: str, words: list[str], line: int) -> None:
        self._refuse("An instruction", line)

    def end(self, line: int) -> object:
        self._refuse(".end", line)

    def finish(self, line: int) -> None:
        self._log.refuse("block", f"Missing .end {self.place()}.", line)


class ClosedBlock(Block):
    """Pattern: Null Object. Between blocks; only a block-opening directive is allowed."""

    def open(self, directive: str, words: list[str], line: int) -> Block:
        if directive == ".datatype":
            self._log.record("load", "datatype")
            return DatatypeBlock(words[0], words[1], self._log)
        if directive == ".driver":
            self._log.record("load", "driver")
            return RoutineBlock(".driver", "", self._log)
        self._log.record("load", "procedure")
        return RoutineBlock(".proc", words[0], self._log)

    def finish(self, line: int) -> None:
        return None


class DatatypeBlock(Block):
    """Pattern: Builder. Collects a datatype's recorded defaults."""

    def __init__(self, name: str, base: str, log: DecisionLog) -> None:
        super().__init__(log)
        self._name = name
        self._base = base
        self._defaults: list[tuple[str, object]] = []

    def place(self) -> str:
        return f"inside .datatype {self._name}"

    def default(self, name: str, word: str, line: int) -> None:
        constant = OperandReader([], self._log).read("constant", word, line)
        self._defaults.append((name, constant))

    def end(self, line: int) -> DatatypeRecord:
        return DatatypeRecord(self._name, self._base, tuple(self._defaults))


class RoutineBlock(Block):
    """Pattern: Builder. Collects locals, labels, and instructions, then resolves jumps."""

    def __init__(self, directive: str, name: str, log: DecisionLog) -> None:
        super().__init__(log)
        self._directive = directive
        self._name = name
        self._locals: list[str] = []
        self._labels: list[tuple[str, int]] = []
        self._pending: list[tuple[Opcode, tuple[object, ...], int]] = []
        self._operands = OperandReader(self._locals, log)

    def place(self) -> str:
        return " ".join(part for part in ("inside", self._directive, self._name) if part)

    def local(self, name: str, line: int) -> None:
        if len(self._pending) > 0 or len(self._labels) > 0:
            self._log.refuse("local", ".local must come before the first instruction.", line)
        if name in self._locals:
            self._log.refuse("local", f"{name} is declared twice.", line)
        self._locals.append(name)

    def label(self, name: str, line: int) -> None:
        if name in dict(self._labels):
            self._log.refuse("label", f"{name} is defined twice.", line)
        self._labels.append((name, len(self._pending)))

    def instruction(self, mnemonic: str, words: list[str], line: int) -> None:
        if mnemonic not in Opcode.__members__:
            self._log.refuse("opcode", f"{mnemonic} is not an opcode.", line)
        opcode = Opcode[mnemonic]
        kinds = opcode.operands()
        if len(words) != len(kinds):
            self._log.refuse("operands", f"{mnemonic} takes {len(kinds)} operand(s).", line)
        operands = tuple(
            self._operands.read(kind, word, line) for kind, word in zip(kinds, words)
        )
        self._pending.append((opcode, operands, line))

    def end(self, line: int) -> Routine:
        instructions = tuple(self._resolve(*pending) for pending in self._pending)
        return Routine(
            self._directive,
            self._name,
            tuple(self._locals),
            instructions,
            tuple(self._labels),
        )

    def _resolve(self, opcode: Opcode, operands: tuple[object, ...], line: int) -> Instruction:
        if opcode.operands() != ("label",):
            return Instruction(opcode, operands)
        label = str(operands[0])
        labels = dict(self._labels)
        if label not in labels:
            self._log.refuse("label", f"{label} is not defined.", line)
        self._log.record("label", "resolve")
        return Instruction(opcode, (Target(label, labels[label]),))
