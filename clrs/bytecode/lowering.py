"""Pattern: Visitor. Lowers expressions to stack instructions on a routine listing."""

from clrs.front.ast import Alloc
from clrs.front.ast import And
from clrs.front.ast import ArrayLiteral
from clrs.front.ast import Attribute
from clrs.front.ast import Binary
from clrs.front.ast import BooleanLiteral
from clrs.front.ast import Call
from clrs.front.ast import Comparison
from clrs.front.ast import FloorDiv
from clrs.front.ast import Index
from clrs.front.ast import InfinityLiteral
from clrs.front.ast import IntegerLiteral
from clrs.front.ast import Name
from clrs.front.ast import NilLiteral
from clrs.front.ast import UnaryMinus
from clrs.bytecode import ARITHMETIC
from clrs.bytecode import BooleanConstant
from clrs.bytecode import COMPARISON_NAMES
from clrs.bytecode import InfinityConstant
from clrs.bytecode import IntegerConstant
from clrs.bytecode import NilConstant
from clrs.bytecode import Opcode
from clrs.common.decisions import DecisionLog
from clrs.bytecode.listing import RoutineListing

LITERALS = {
    IntegerLiteral: lambda node: IntegerConstant(node.value),
    BooleanLiteral: lambda node: BooleanConstant(node.value),
    NilLiteral: lambda node: NilConstant(),
    InfinityLiteral: lambda node: InfinityConstant(),
}


class ExpressionLowering:
    """Pattern: Visitor. Lowers expressions so each pushes exactly one value."""

    def __init__(self, listing: RoutineListing, log: DecisionLog) -> None:
        self._listing = listing
        self._log = log

    def lower(self, node: object) -> None:
        node.accept(self)  # type: ignore[attr-defined]

    def branch_unless(self, test: object, label: str) -> None:
        if isinstance(test, And):
            self._log.record("condition", "and")
            self.branch_unless(test.left, label)
            self.branch_unless(test.right, label)
            return
        self._log.record("condition", "value")
        self.lower(test)
        self._listing.op(Opcode.JUMP_IF_FALSE, label)

    def visit_name(self, node: Name) -> None:
        if not self._listing.is_local(node.text):
            self._log.reject("name", f'"{node.text}" is not a local.', node.line, node.column)
        self._listing.op(Opcode.LOAD, node.text)

    def _constant(self, node: object) -> None:
        self._listing.op(Opcode.CONST, LITERALS[type(node)](node))

    def visit_integerliteral(self, node: IntegerLiteral) -> None:
        self._constant(node)

    def visit_booleanliteral(self, node: BooleanLiteral) -> None:
        self._constant(node)

    def visit_nilliteral(self, node: NilLiteral) -> None:
        self._constant(node)

    def visit_infinityliteral(self, node: InfinityLiteral) -> None:
        self._constant(node)

    def visit_and(self, node: And) -> None:
        self._log.record("and", "value")
        false_label, end_label = self._listing.new_labels("and_false", "and_end")
        self.branch_unless(node, false_label)
        self._listing.op(Opcode.CONST, BooleanConstant(True))
        self._listing.op(Opcode.JUMP, end_label)
        self._listing.label(false_label)
        self._listing.op(Opcode.CONST, BooleanConstant(False))
        self._listing.label(end_label)

    def visit_comparison(self, node: Comparison) -> None:
        self.lower(node.left)
        self.lower(node.right)
        self._listing.op(Opcode.CMP, COMPARISON_NAMES[node.operator])

    def visit_binary(self, node: Binary) -> None:
        self.lower(node.left)
        self.lower(node.right)
        self._listing.op(ARITHMETIC[node.operator])

    def visit_unaryminus(self, node: UnaryMinus) -> None:
        self._listing.op(Opcode.CONST, IntegerConstant(0))
        self.lower(node.operand)
        self._listing.op(Opcode.SUB)

    def visit_floordiv(self, node: FloorDiv) -> None:
        self.lower(node.left)
        self.lower(node.right)
        self._listing.op(Opcode.FLOORDIV)

    def visit_call(self, node: Call) -> None:
        for argument in node.arguments:
            self.lower(argument)
        self._listing.op(Opcode.CALL, node.name, len(node.arguments))

    def visit_index(self, node: Index) -> None:
        self.lower(node.target)
        self.lower(node.index)
        self._listing.op(Opcode.LOAD_IDX)

    def visit_attribute(self, node: Attribute) -> None:
        self.lower(node.owner)
        self._listing.op(Opcode.LOAD_ATTR, node.name)

    def visit_alloc(self, node: Alloc) -> None:
        self.lower(node.size)
        self._listing.op(Opcode.ALLOC)

    def visit_arrayliteral(self, node: ArrayLiteral) -> None:
        for element in node.elements:
            self.lower(element)
        self._listing.op(Opcode.PACK, len(node.elements))
