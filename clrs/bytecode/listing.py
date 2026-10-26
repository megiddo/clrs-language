"""Pattern: Builder. Accumulates the text lines of one routine as it is lowered."""

from clrs.bytecode import COMMENT
from clrs.bytecode import Opcode
from clrs.bytecode import render


class RoutineListing:
    """Pattern: Builder. Accumulates one routine's slots, labels, comments, and opcodes."""

    def __init__(self, header: str, parameters: tuple[str, ...], names: tuple[str, ...]) -> None:
        self._header = header
        self._parameters = parameters
        self._locals = list(names)
        self._body: list[str] = []
        self._labels = 0
        self._temporaries = 0
        self._commented = 0

    def is_local(self, name: str) -> bool:
        return name in self._locals

    def op(self, opcode: Opcode, *operands: object) -> None:
        self._body.append(render(opcode, operands))

    def label(self, name: str) -> None:
        self._body.append(f"{name}:")

    def new_labels(self, *kinds: str) -> tuple[str, ...]:
        self._labels += 1
        return tuple(f"L_{kind}_{self._labels}" for kind in kinds)

    def comment(self, line: int, text: str) -> None:
        if line != self._commented:
            self._commented = line
            self._body.append(f"{COMMENT} {text}")

    def reset_temporaries(self) -> None:
        self._temporaries = 0

    def temporary(self) -> str:
        self._temporaries += 1
        name = f"${self._temporaries}"
        if name not in self._locals:
            self._locals.append(name)
        return name

    def lines(self) -> list[str]:
        params = [f".param {name}" for name in self._parameters]
        locals_ = [f".local {name}" for name in self._locals[len(self._parameters) :]]
        return [self._header, *params, *locals_, *self._body, ".end"]
