"""Pattern: Builder. Builds statements, suites, and declarations."""

from clrs.ast import Assign
from clrs.ast import Attribute
from clrs.ast import Call
from clrs.ast import Exchange
from clrs.ast import ExprStmt
from clrs.ast import ForLoop
from clrs.ast import If
from clrs.ast import Index
from clrs.ast import Name
from clrs.ast import Return
from clrs.ast import WhileLoop
from clrs.cursor import TokenCursor
from clrs.decisions import DecisionLog
from clrs.direction import Directions
from clrs.errors import BLOCK_INTRO
from clrs.errors import CompileError
from clrs.errors import FOR_DIRECTION_MESSAGE
from clrs.errors import FOR_END_MESSAGE
from clrs.errors import LENGTH_MESSAGE
from clrs.errors import TARGET_MESSAGE
from clrs.expressions import ExpressionBuilder
from clrs.scope import Scope
from clrs.tokens import EXPRESSION_STARTS
from clrs.tokens import Token
from clrs.tokens import TokenKind


def declare(scope: Scope, log: DecisionLog, name: str, line: int, column: int) -> None:
    if name == "length":
        log.reject("length", LENGTH_MESSAGE, line, column)
    scope.declare(name)


def position_of(node: object) -> tuple[int, int]:
    return node.line, node.column  # type: ignore[attr-defined]


class StatementBuilder:
    """Pattern: Builder. Builds statements, suites, and declarations."""

    def __init__(
        self,
        cursor: TokenCursor,
        scope: Scope,
        log: DecisionLog,
        ends_with_newline: bool,
    ) -> None:
        self._cursor = cursor
        self._scope = scope
        self._log = log
        self._ends_with_newline = ends_with_newline
        self._expressions = ExpressionBuilder(cursor, scope, log)
        self._directions = Directions()
        self._previous = ""

    def expressions(self) -> ExpressionBuilder:
        return self._expressions

    def parse_suite(self) -> tuple[object, ...]:
        self._cursor.expect(TokenKind.INDENT)
        statements: list[object] = []
        while not self._cursor.check(TokenKind.DEDENT):
            statements.append(self.parse_statement())
        self._cursor.expect(TokenKind.DEDENT)
        return tuple(statements)

    def parse_statement(self) -> object:
        if self._cursor.check(TokenKind.INDENT):
            self._bad_indent()
        if self._cursor.check(TokenKind.FOR):
            return self._for_loop()
        if self._cursor.check(TokenKind.WHILE):
            return self._while_loop()
        if self._cursor.check(TokenKind.IF):
            return self._if_statement()
        if self._cursor.check(TokenKind.RETURN):
            return self._return_statement()
        if self._cursor.check(TokenKind.NAME):
            return self._named()
        token = self._cursor.peek()
        raise CompileError(
            f"Expected a statement but found {token.text!r}.",
            token.line,
            token.column,
        )

    def _bad_indent(self) -> None:
        token = self._cursor.peek()
        self._log.reject(
            "indent",
            f'Indented under "{self._previous}", {BLOCK_INTRO}',
            token.line,
            token.column,
        )

    def _named(self) -> object:
        expr = self._expressions.parse()
        if self._cursor.check(TokenKind.ASSIGN):
            return self._assign(expr)
        if self._cursor.check(TokenKind.EXCHANGE):
            return self._exchange(expr)
        if isinstance(expr, Call):
            self._end()
            return ExprStmt(expr, expr.line, expr.column)
        token = self._cursor.peek()
        raise CompileError(
            f"Expected a statement but found {token.text!r}.",
            token.line,
            token.column,
        )

    def _assign(self, target: object) -> Assign:
        self._cursor.advance()
        self._writable(target)
        value = self._expressions.parse()
        if isinstance(target, Name):
            declare(self._scope, self._log, target.text, target.line, target.column)
        line, column = position_of(target)
        self._end()
        return Assign(target, value, line, column)

    def _exchange(self, left: object) -> Exchange:
        self._cursor.advance()
        self._writable(left)
        right = self._expressions.parse()
        self._writable(right)
        line, column = position_of(left)
        self._end()
        return Exchange(left, right, line, column)

    def _writable(self, target: object) -> None:
        if isinstance(target, Name):
            self._forbid_length(target.text, target.line, target.column)
            return
        if isinstance(target, Attribute):
            self._forbid_length(target.name, target.line, target.column)
            return
        if isinstance(target, Index):
            return
        token = self._cursor.peek()
        self._log.reject("target", TARGET_MESSAGE, token.line, token.column)

    def _forbid_length(self, name: str, line: int, column: int) -> None:
        if name == "length":
            self._log.reject("length", LENGTH_MESSAGE, line, column)

    def _for_loop(self) -> ForLoop:
        token = self._cursor.advance()
        name = self._cursor.expect(TokenKind.NAME)
        self._cursor.expect(TokenKind.ASSIGN)
        start = self._expressions.parse()
        direction_token = self._direction_token()
        end = self._end_expression()
        self._optional(TokenKind.DO)
        self._cursor.expect(TokenKind.NEWLINE)
        declare(self._scope, self._log, name.text, name.line, name.column)
        body = self.parse_suite()
        direction = self._directions.choose(direction_token.text)
        self._log.record("for", direction.label())
        return ForLoop(name.text, start, direction, end, body, token.line, token.column)

    def _direction_token(self) -> Token:
        if self._cursor.check(TokenKind.TO) or self._cursor.check(TokenKind.DOWNTO):
            return self._cursor.advance()
        token = self._cursor.peek()
        self._log.reject("for", FOR_DIRECTION_MESSAGE, token.line, token.column)

    def _end_expression(self) -> object:
        if self._cursor.peek().kind not in EXPRESSION_STARTS:
            token = self._cursor.peek()
            self._log.reject("for", FOR_END_MESSAGE, token.line, token.column)
        return self._expressions.parse()

    def _while_loop(self) -> WhileLoop:
        token = self._cursor.advance()
        test = self._expressions.parse()
        self._optional(TokenKind.DO)
        self._cursor.expect(TokenKind.NEWLINE)
        return WhileLoop(test, self.parse_suite(), token.line, token.column)

    def _if_statement(self) -> If:
        token = self._cursor.advance()
        test = self._expressions.parse()
        self._optional(TokenKind.THEN)
        self._cursor.expect(TokenKind.NEWLINE)
        consequent = self.parse_suite()
        alternate: tuple[object, ...] = ()
        if self._cursor.check(TokenKind.ELSE):
            self._cursor.advance()
            self._cursor.expect(TokenKind.NEWLINE)
            alternate = self.parse_suite()
        return If(test, consequent, alternate, token.line, token.column)

    def _return_statement(self) -> Return:
        token = self._cursor.advance()
        value = self._expressions.parse()
        self._end()
        return Return(value, token.line, token.column)

    def _optional(self, kind: TokenKind) -> None:
        if self._cursor.check(kind):
            self._cursor.advance()

    def _end(self) -> None:
        if self._ends_with_newline:
            token = self._cursor.expect(TokenKind.NEWLINE)
            self._previous = token.text
