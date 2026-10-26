"""Pattern: Visitor. Lowers statements and control flow to labels and jumps."""

from clrs.bytecode.addresses import Addresses
from clrs.front.ast import Assign
from clrs.front.ast import Exchange
from clrs.front.ast import ExprStmt
from clrs.front.ast import ForLoop
from clrs.front.ast import If
from clrs.front.ast import Return
from clrs.front.ast import WhileLoop
from clrs.bytecode import IntegerConstant
from clrs.bytecode import Opcode
from clrs.common.decisions import DecisionLog
from clrs.bytecode.listing import RoutineListing
from clrs.bytecode.lowering import ExpressionLowering


class StatementLowering:
    """Pattern: Visitor. Lowers statements, each preceded by its source line as a comment."""

    def __init__(
        self,
        listing: RoutineListing,
        source: tuple[str, ...],
        log: DecisionLog,
    ) -> None:
        self._listing = listing
        self._source = source
        self._log = log
        self._expressions = ExpressionLowering(listing, log)
        self._addresses = Addresses(self._expressions, listing, log)

    def expressions(self) -> ExpressionLowering:
        return self._expressions

    def comment(self, node: object) -> None:
        line = node.line  # type: ignore[attr-defined]
        self._listing.comment(line, self._source[line - 1].strip())

    def lower(self, statements: tuple[object, ...]) -> None:
        for statement in statements:
            self.comment(statement)
            statement.accept(self)  # type: ignore[attr-defined]

    def visit_assign(self, node: Assign) -> None:
        self._addresses.of(node.target).assign(node.value)

    def visit_exchange(self, node: Exchange) -> None:
        self._listing.reset_temporaries()
        left = self._addresses.of(node.left)
        right = self._addresses.of(node.right)
        left.bind()
        right.bind()
        saved = self._listing.temporary()
        left.load()
        self._listing.op(Opcode.STORE, saved)
        left.store(right.load)
        right.store(lambda: self._listing.op(Opcode.LOAD, saved))

    def visit_return(self, node: Return) -> None:
        self._expressions.lower(node.value)
        self._listing.op(Opcode.RET)

    def visit_exprstmt(self, node: ExprStmt) -> None:
        self._expressions.lower(node.expression)
        self._listing.op(Opcode.POP)

    def visit_forloop(self, node: ForLoop) -> None:
        self._expressions.lower(node.start)
        self._listing.op(Opcode.STORE, node.variable)
        top, end = self._listing.new_labels("for", "for_end")
        self._listing.label(top)
        self._listing.op(Opcode.LOAD, node.variable)
        self._expressions.lower(node.end)
        self._listing.op(Opcode.CMP, node.direction.comparison())  # type: ignore[attr-defined]
        self._listing.op(Opcode.JUMP_IF_FALSE, end)
        self.lower(node.body)
        self._listing.op(Opcode.LOAD, node.variable)
        self._listing.op(Opcode.CONST, IntegerConstant(1))
        self._listing.op(Opcode[node.direction.step()])  # type: ignore[attr-defined]
        self._listing.op(Opcode.STORE, node.variable)
        self._listing.op(Opcode.JUMP, top)
        self._listing.label(end)

    def visit_whileloop(self, node: WhileLoop) -> None:
        top, end = self._listing.new_labels("while", "while_end")
        self._listing.label(top)
        self._expressions.branch_unless(node.test, end)
        self.lower(node.body)
        self._listing.op(Opcode.JUMP, top)
        self._listing.label(end)

    def visit_if(self, node: If) -> None:
        if node.alternate == ():
            self._log.record("if", "bare")
            (end,) = self._listing.new_labels("endif")
            self._expressions.branch_unless(node.test, end)
            self.lower(node.consequent)
            self._listing.label(end)
            return
        self._log.record("if", "else")
        otherwise, end = self._listing.new_labels("else", "endif")
        self._expressions.branch_unless(node.test, otherwise)
        self.lower(node.consequent)
        self._listing.op(Opcode.JUMP, end)
        self._listing.label(otherwise)
        self.lower(node.alternate)
        self._listing.label(end)
