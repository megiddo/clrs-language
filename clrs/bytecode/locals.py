"""Pattern: Visitor. Collects a routine's local names in slot order."""

from clrs.front.ast import Assign
from clrs.front.ast import Exchange
from clrs.front.ast import ExprStmt
from clrs.front.ast import ForLoop
from clrs.front.ast import If
from clrs.front.ast import Name
from clrs.front.ast import Return
from clrs.front.ast import WhileLoop


class LocalNames:
    """Pattern: Visitor. Collects parameters, assigned names, and loop variables in order."""

    def __init__(self, parameters: tuple[str, ...]) -> None:
        self._names = list(parameters)

    def collect(self, statements: tuple[object, ...]) -> tuple[str, ...]:
        self._walk(statements)
        return tuple(self._names)

    def _walk(self, statements: tuple[object, ...]) -> None:
        for statement in statements:
            statement.accept(self)  # type: ignore[attr-defined]

    def _add(self, name: str) -> None:
        if name not in self._names:
            self._names.append(name)

    def visit_assign(self, node: Assign) -> None:
        if isinstance(node.target, Name):
            self._add(node.target.text)

    def visit_exchange(self, node: Exchange) -> None:
        return None

    def visit_return(self, node: Return) -> None:
        return None

    def visit_exprstmt(self, node: ExprStmt) -> None:
        return None

    def visit_forloop(self, node: ForLoop) -> None:
        self._add(node.variable)
        self._walk(node.body)

    def visit_whileloop(self, node: WhileLoop) -> None:
        self._walk(node.body)

    def visit_if(self, node: If) -> None:
        self._walk(node.consequent)
        self._walk(node.alternate)
