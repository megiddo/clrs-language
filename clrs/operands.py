"""Pattern: Strategy. Reads one .clrsa operand word by the kind its opcode declares."""

import re

from clrs.bytecode import BooleanConstant
from clrs.bytecode import COMPARISON_NAMES
from clrs.bytecode import InfinityConstant
from clrs.bytecode import IntegerConstant
from clrs.bytecode import NilConstant
from clrs.decisions import DecisionLog

CONSTANT_WORDS = {
    "True": BooleanConstant(True),
    "False": BooleanConstant(False),
    "NIL": NilConstant(),
    "∞": InfinityConstant(),
}

INTEGER = re.compile(r"-?[0-9]+")
COUNT = re.compile(r"[0-9]+")


class OperandReader:
    """Pattern: Strategy. One reader per operand kind; locals are checked against slots."""

    def __init__(self, locals_: list[str], log: DecisionLog) -> None:
        self._locals = locals_
        self._log = log
        self._readers = {
            "constant": self._constant,
            "local": self._local,
            "attribute": self._word,
            "procedure": self._word,
            "label": self._word,
            "count": self._count,
            "comparison": self._comparison,
        }

    def read(self, kind: str, word: str, line: int) -> object:
        return self._readers[kind](word, line)

    def _constant(self, word: str, line: int) -> object:
        if word in CONSTANT_WORDS:
            return CONSTANT_WORDS[word]
        if INTEGER.fullmatch(word) is None:
            self._log.refuse("constant", f"{word} is not a constant.", line)
        return IntegerConstant(int(word))

    def _local(self, word: str, line: int) -> str:
        if word not in self._locals:
            self._log.refuse("local", f"{word} is not a declared local.", line)
        return word

    def _word(self, word: str, line: int) -> str:
        return word

    def _count(self, word: str, line: int) -> int:
        if COUNT.fullmatch(word) is None:
            self._log.refuse("count", f"{word} is not a count.", line)
        return int(word)

    def _comparison(self, word: str, line: int) -> str:
        if word not in COMPARISON_NAMES.values():
            self._log.refuse("comparison", f"{word} is not a comparison.", line)
        return word
