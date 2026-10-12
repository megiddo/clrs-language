"""Pattern: Strategy. How a name, index, or attribute target is read and written."""

from collections.abc import Callable

from clrs.ast import Attribute
from clrs.ast import Index
from clrs.ast import Name
from clrs.bytecode import Opcode
from clrs.decisions import DecisionLog
from clrs.listing import RoutineListing
from clrs.lowering import ExpressionLowering


class NameAddress:
    """Pattern: Strategy. A local slot; it has no address expression to evaluate."""

    def __init__(self, node: Name, expressions: ExpressionLowering, listing: RoutineListing) -> None:
        self._node = node
        self._expressions = expressions
        self._listing = listing

    def assign(self, value: object) -> None:
        self.store(lambda: self._expressions.lower(value))

    def bind(self) -> None:
        return None

    def load(self) -> None:
        self._expressions.lower(self._node)

    def store(self, push: Callable[[], None]) -> None:
        push()
        self._listing.op(Opcode.STORE, self._node.text)


class IndexAddress:
    """Pattern: Strategy. An array element; the array and index are evaluated once on bind."""

    def __init__(self, node: Index, expressions: ExpressionLowering, listing: RoutineListing) -> None:
        self._node = node
        self._expressions = expressions
        self._listing = listing
        self._array = ""
        self._index = ""

    def assign(self, value: object) -> None:
        self._expressions.lower(self._node.target)
        self._expressions.lower(self._node.index)
        self._expressions.lower(value)
        self._listing.op(Opcode.STORE_IDX)

    def bind(self) -> None:
        self._array = self._spill(self._node.target)
        self._index = self._spill(self._node.index)

    def _spill(self, node: object) -> str:
        name = self._listing.temporary()
        self._expressions.lower(node)
        self._listing.op(Opcode.STORE, name)
        return name

    def load(self) -> None:
        self._listing.op(Opcode.LOAD, self._array)
        self._listing.op(Opcode.LOAD, self._index)
        self._listing.op(Opcode.LOAD_IDX)

    def store(self, push: Callable[[], None]) -> None:
        self._listing.op(Opcode.LOAD, self._array)
        self._listing.op(Opcode.LOAD, self._index)
        push()
        self._listing.op(Opcode.STORE_IDX)


class AttributeAddress:
    """Pattern: Strategy. An attribute; its owner is evaluated once on bind."""

    def __init__(
        self,
        node: Attribute,
        expressions: ExpressionLowering,
        listing: RoutineListing,
    ) -> None:
        self._node = node
        self._expressions = expressions
        self._listing = listing
        self._owner = ""

    def assign(self, value: object) -> None:
        self._expressions.lower(self._node.owner)
        self._expressions.lower(value)
        self._listing.op(Opcode.STORE_ATTR, self._node.name)

    def bind(self) -> None:
        self._owner = self._listing.temporary()
        self._expressions.lower(self._node.owner)
        self._listing.op(Opcode.STORE, self._owner)

    def load(self) -> None:
        self._listing.op(Opcode.LOAD, self._owner)
        self._listing.op(Opcode.LOAD_ATTR, self._node.name)

    def store(self, push: Callable[[], None]) -> None:
        self._listing.op(Opcode.LOAD, self._owner)
        push()
        self._listing.op(Opcode.STORE_ATTR, self._node.name)


Address = NameAddress | IndexAddress | AttributeAddress


class Addresses:
    """Pattern: Factory. Chooses the address strategy for an assignment or exchange target."""

    def __init__(
        self,
        expressions: ExpressionLowering,
        listing: RoutineListing,
        log: DecisionLog,
    ) -> None:
        self._expressions = expressions
        self._listing = listing
        self._log = log

    def of(self, target: object) -> Address:
        if isinstance(target, Name):
            self._log.record("address", "name")
            return NameAddress(target, self._expressions, self._listing)
        if isinstance(target, Index):
            self._log.record("address", "index")
            return IndexAddress(target, self._expressions, self._listing)
        self._log.record("address", "attribute")
        return AttributeAddress(target, self._expressions, self._listing)  # type: ignore[arg-type]
