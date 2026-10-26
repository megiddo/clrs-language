"""Pattern: Observer. Publishes parse, compile, load, and run decisions on the clrs logger."""

import logging
from typing import NoReturn

from clrs.common.errors import CompileError
from clrs.common.errors import LinkError
from clrs.common.errors import LoadError
from clrs.common.errors import RuntimeFault


class DecisionLog:
    """Pattern: Observer. Publishes parse, compile, load, and run decisions on the clrs logger."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("clrs")

    def record(self, decision: str, outcome: str) -> None:
        self._logger.info("%s %s", decision, outcome)

    def reject(self, outcome: str, message: str, line: int, column: int) -> NoReturn:
        self.record("reject", outcome)
        raise CompileError(message, line, column)

    def refuse(self, outcome: str, message: str, line: int) -> NoReturn:
        self.record("refuse", outcome)
        raise LoadError(message, line)

    def fault(self, outcome: str, message: str) -> NoReturn:
        self.record("fault", outcome)
        raise RuntimeFault(message)

    def unlinked(self, outcome: str, message: str) -> NoReturn:
        self.record("unlinked", outcome)
        raise LinkError(message)
