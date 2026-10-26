"""Pattern: Strategy. Renders a run result as the text the command line prints."""

from collections.abc import Callable

from clrs.common.decisions import DecisionLog
from clrs.vm.values import ClrsArray
from clrs.vm.values import Infinity
from clrs.vm.values import Nil


class ValuePrinter:
    """Pattern: Strategy. One rendering per runtime type, chosen by exact type so True is not 1."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._renderers: dict[type, tuple[str, Callable[[object], str]]] = {
            int: ("integer", str),
            bool: ("boolean", str),
            Infinity: ("infinity", lambda value: "∞"),
            Nil: ("nil", lambda value: "NIL"),
            ClrsArray: ("array", self._array),  # type: ignore[dict-item]
        }

    def render(self, value: object) -> str:
        outcome, renderer = self._renderers[type(value)]
        self._log.record("print", outcome)
        return renderer(value)

    def _array(self, array: ClrsArray) -> str:
        items = [self.render(item) for item in array.items()]
        if len(items) == 1:
            self._log.record("print", "single")
            return f"[{items[0]},]"
        return "[" + ", ".join(items) + "]"
