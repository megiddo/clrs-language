"""Pattern: Observer. Publishes parse decisions on the clrs logger."""

import logging

from clrs.errors import CompileError


class DecisionLog:
    """Pattern: Observer. Publishes parse decisions on the clrs logger."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("clrs")

    def record(self, decision: str, outcome: str) -> None:
        self._logger.info("%s %s", decision, outcome)

    def reject(self, outcome: str, message: str, line: int, column: int) -> None:
        self.record("reject", outcome)
        raise CompileError(message, line, column)
