"""Pattern: Facade. Reads .clrsa text back into a program with resolved labels."""

from clrs.bytecode.blocks import Block
from clrs.bytecode.blocks import ClosedBlock
from clrs.bytecode import COMMENT
from clrs.bytecode import Program
from clrs.common.decisions import DecisionLog

DIRECTIVES = {".proc": 1, ".driver": 0, ".datatype": 2, ".local": 1, ".default": 2, ".end": 0}
OPENERS = frozenset({".proc", ".driver", ".datatype"})


class ProgramBuilder:
    """Pattern: Builder. Feeds each line to the open block and keeps finished blocks in order."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._block: Block = ClosedBlock(log)
        self._blocks: list[object] = []

    def line(self, number: int, text: str) -> None:
        words = text.split()
        if text.startswith("."):
            self._directive(words[0], words[1:], number)
            return
        if text.endswith(":") and len(words) == 1:
            self._log.record("load", "label")
            self._block.label(text[:-1], number)
            return
        self._block.instruction(words[0], words[1:], number)

    def _directive(self, head: str, words: list[str], number: int) -> None:
        if head not in DIRECTIVES:
            self._log.refuse("directive", f"{head} is not a directive.", number)
        if len(words) != DIRECTIVES[head]:
            self._log.refuse("directive", f"{head} takes {DIRECTIVES[head]} operand(s).", number)
        if head in OPENERS:
            self._block = self._block.open(head, words, number)
            return
        if head == ".local":
            self._block.local(words[0], number)
            return
        if head == ".default":
            self._block.default(words[0], words[1], number)
            return
        self._blocks.append(self._block.end(number))
        self._block = ClosedBlock(self._log)

    def finish(self, number: int) -> Program:
        self._block.finish(number)
        return Program(tuple(self._blocks))


class Loader:
    """Pattern: Facade. Strips ▷ comments, reads blocks, and resolves labels."""

    def load(self, text: str) -> Program:
        log = DecisionLog()
        builder = ProgramBuilder(log)
        lines = text.splitlines()
        for number, raw in enumerate(lines, start=1):
            code, mark, _ = raw.partition(COMMENT)
            if mark != "":
                log.record("load", "comment")
            if code.strip() != "":
                builder.line(number, code.strip())
        return builder.finish(len(lines))
