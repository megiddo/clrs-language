"""Pattern: Value Object. Opcodes, constants, instructions, and routines of textual bytecode."""

from dataclasses import dataclass
from enum import Enum

COMMENT = "▷"


class Opcode(Enum):
    """Pattern: Enumeration. The opcodes of textual bytecode."""

    CONST = "CONST"
    LOAD = "LOAD"
    STORE = "STORE"
    LOAD_IDX = "LOAD_IDX"
    STORE_IDX = "STORE_IDX"
    LOAD_ATTR = "LOAD_ATTR"
    STORE_ATTR = "STORE_ATTR"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    FLOORDIV = "FLOORDIV"
    CMP = "CMP"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    CALL = "CALL"
    RET = "RET"
    ALLOC = "ALLOC"
    PACK = "PACK"
    POP = "POP"

    def operands(self) -> tuple[str, ...]:
        return SIGNATURES.get(self, ())


SIGNATURES = {
    Opcode.CONST: ("constant",),
    Opcode.LOAD: ("local",),
    Opcode.STORE: ("local",),
    Opcode.LOAD_ATTR: ("attribute",),
    Opcode.STORE_ATTR: ("attribute",),
    Opcode.CMP: ("comparison",),
    Opcode.JUMP: ("label",),
    Opcode.JUMP_IF_FALSE: ("label",),
    Opcode.CALL: ("procedure", "count"),
    Opcode.PACK: ("count",),
}

COMPARISON_NAMES = {"<": "lt", ">": "gt", "<=": "le", ">=": "ge", "=": "eq", "!=": "ne"}

ARITHMETIC = {"+": Opcode.ADD, "-": Opcode.SUB, "*": Opcode.MUL}


@dataclass(frozen=True)
class IntegerConstant:
    """Pattern: Value Object. An integer operand of CONST."""

    value: int

    def text(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BooleanConstant:
    """Pattern: Value Object. The True or False operand of CONST."""

    value: bool

    def text(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class NilConstant:
    """Pattern: Value Object. The NIL operand of CONST, which is not an integer."""

    def text(self) -> str:
        return "NIL"


@dataclass(frozen=True)
class InfinityConstant:
    """Pattern: Value Object. The ∞ operand of CONST."""

    def text(self) -> str:
        return "∞"


@dataclass(frozen=True)
class Target:
    """Pattern: Value Object. A jump label and the instruction index it resolves to."""

    label: str
    index: int

    def text(self) -> str:
        return self.label


def operand_text(operand: object) -> str:
    if isinstance(operand, (str, int)):
        return str(operand)
    return operand.text()  # type: ignore[attr-defined]


def render(opcode: Opcode, operands: tuple[object, ...]) -> str:
    return " ".join([opcode.value, *[operand_text(operand) for operand in operands]])


@dataclass(frozen=True)
class Instruction:
    """Pattern: Value Object. One opcode and its parsed operands."""

    opcode: Opcode
    operands: tuple[object, ...]

    def text(self) -> str:
        return render(self.opcode, self.operands)


@dataclass(frozen=True)
class Routine:
    """Pattern: Value Object. A procedure or driver: parameters, then other locals, then code."""

    directive: str
    name: str
    parameters: tuple[str, ...]
    locals: tuple[str, ...]
    instructions: tuple[Instruction, ...]
    labels: tuple[tuple[str, int], ...]

    def slots(self) -> tuple[str, ...]:
        return self.parameters + self.locals

    def lines(self) -> list[str]:
        header = " ".join(part for part in (self.directive, self.name) if part)
        lines = [
            header,
            *[f".param {name}" for name in self.parameters],
            *[f".local {name}" for name in self.locals],
        ]
        for index, instruction in enumerate(self.instructions):
            lines.extend(self._labels_at(index))
            lines.append(instruction.text())
        lines.extend(self._labels_at(len(self.instructions)))
        lines.append(".end")
        return lines

    def _labels_at(self, index: int) -> list[str]:
        return [f"{name}:" for name, at in self.labels if at == index]


@dataclass(frozen=True)
class DatatypeRecord:
    """Pattern: Value Object. A datatype, its base, and its recorded attribute defaults."""

    name: str
    base: str
    defaults: tuple[tuple[str, object], ...]

    def lines(self) -> list[str]:
        defaults = [f".default {name} {operand_text(value)}" for name, value in self.defaults]
        return [f".datatype {self.name} {self.base}", *defaults, ".end"]


@dataclass(frozen=True)
class Program:
    """Pattern: Value Object. Loaded blocks in file order."""

    blocks: tuple[object, ...]

    def text(self) -> str:
        lines: list[str] = []
        for block in self.blocks:
            lines.extend(block.lines())  # type: ignore[attr-defined]
        return "".join(f"{line}\n" for line in lines)
