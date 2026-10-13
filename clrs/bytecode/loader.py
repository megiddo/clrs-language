"""Pattern: Facade. Reads .clrsa text back into a program with resolved labels."""

from clrs.bytecode.blocks import Block
from clrs.bytecode.blocks import ClosedBlock
from clrs.bytecode import COMMENT
from clrs.bytecode import HEADER
from clrs.bytecode import PACKED_VERSION
from clrs.bytecode import Program
from clrs.bytecode import Routine
from clrs.common.decisions import DecisionLog

DIRECTIVES = {
    ".proc": 1,
    ".driver": 0,
    ".datatype": 2,
    ".param": 1,
    ".local": 1,
    ".default": 2,
    ".end": 0,
    ".entry": 1,
    ".module": 1,
}
OPENERS = frozenset({".proc", ".driver", ".datatype"})
BETWEEN = frozenset({".entry", ".module"})


class ProgramBuilder:
    """Pattern: Builder. Feeds each line to the open block and keeps finished blocks in order."""

    def __init__(self, log: DecisionLog, version: int) -> None:
        self._log = log
        self._version = version
        self._block: Block = ClosedBlock(log)
        self._blocks: list[object] = []
        self._entries: list[tuple[str, int]] = []

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
        if head in BETWEEN:
            self._between(head, words[0], number)
            return
        if head == ".param":
            self._block.param(words[0], number)
            return
        if head == ".local":
            self._block.local(words[0], number)
            return
        if head == ".default":
            self._block.default(words[0], words[1], number)
            return
        self._blocks.append(self._block.end(number))
        self._block = ClosedBlock(self._log)

    def _between(self, head: str, name: str, number: int) -> None:
        self._block.between(head, number)
        if head == ".module":
            self._log.record("load", "module")
            return
        if self._entries:
            self._log.refuse("entry", f"A second .entry; the first is on line {self._entries[0][1]}.", number)
        if self._version == 0:
            self._log.refuse("entry", f".entry needs the {HEADER} {PACKED_VERSION} header on line 1.", number)
        self._entries.append((name, number))

    def finish(self, number: int) -> Program:
        self._block.finish(number)
        blocks = tuple(self._blocks)
        if not self._entries:
            return Program(blocks, None, self._version)
        name, line = self._entries[0]
        EntrySpecification(self._log).check(blocks, name, line)
        return Program(blocks, name, self._version)


class EntrySpecification:
    """Pattern: Specification. An entry names exactly one routine: a `.proc` of that name or the `.driver`."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log

    def check(self, blocks: tuple[object, ...], name: str, line: int) -> None:
        routines = [block for block in blocks if isinstance(block, Routine)]
        procedures = [r for r in routines if r.directive == ".proc" and r.name == name]
        drivers = [r for r in routines if r.directive == ".driver"]
        candidates = len(procedures) + len(drivers)
        if candidates == 0:
            self._log.refuse("entry", f".entry {name} names no .proc, and there is no .driver.", line)
        if candidates > 1:
            self._log.refuse("entry", f".entry {name} is ambiguous: {candidates} routines could run.", line)
        self._log.record("load", "entry")


class Loader:
    """Pattern: Facade. Reads the optional ▷ clrsa header, strips ▷ comments, reads blocks, and resolves labels."""

    def load(self, text: str) -> Program:
        log = DecisionLog()
        lines = text.splitlines()
        builder = ProgramBuilder(log, self._version(lines[:1], log))
        for number, raw in enumerate(lines, start=1):
            code, mark, _ = raw.partition(COMMENT)
            if mark != "":
                log.record("load", "comment")
            if code.strip() != "":
                builder.line(number, code.strip())
        return builder.finish(len(lines))

    def _version(self, first: list[str], log: DecisionLog) -> int:
        words = "".join(first).split()
        if words[:2] != HEADER.split() or len(words) != 3 or not words[2].isdigit():
            return 0
        if words[2] != str(PACKED_VERSION):
            log.refuse("version", f"Only {HEADER} {PACKED_VERSION} can be loaded.", 1)
        log.record("load", "packed")
        return PACKED_VERSION
