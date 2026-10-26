"""Pattern: Builder. Builds expression value objects from tokens."""

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
from clrs.front.cursor import TokenCursor
from clrs.common.decisions import DecisionLog
from clrs.common.errors import CEILING_MESSAGE
from clrs.common.errors import CompileError
from clrs.common.errors import CHAIN_MESSAGE
from clrs.common.errors import FLOOR_MESSAGE
from clrs.common.errors import OR_MESSAGE
from clrs.common.errors import SLASH_MESSAGE
from clrs.front.scope import Scope
from clrs.front.tokens import COMPARISONS
from clrs.front.tokens import OPERATOR_TEXT
from clrs.front.tokens import Token
from clrs.front.tokens import TokenKind


class ExpressionBuilder:
    """Pattern: Builder. Builds expression value objects from tokens."""

    def __init__(self, cursor: TokenCursor, scope: Scope, log: DecisionLog) -> None:
        self._cursor = cursor
        self._scope = scope
        self._log = log

    def parse(self) -> object:
        return self._conjunction()

    def _conjunction(self) -> object:
        left = self._comparison()
        while self._cursor.check(TokenKind.AND):
            token = self._cursor.advance()
            right = self._comparison()
            left = And(left, right, token.line, token.column)
        if self._cursor.check(TokenKind.OR):
            token = self._cursor.peek()
            self._log.reject("or", OR_MESSAGE, token.line, token.column)
        self._reject_slash()
        return left

    def _comparison(self) -> object:
        left = self._additive()
        if self._cursor.peek().kind not in COMPARISONS:
            return left
        token = self._cursor.advance()
        right = self._additive()
        if self._cursor.peek().kind in COMPARISONS:
            bad = self._cursor.peek()
            self._log.reject("chain", CHAIN_MESSAGE, bad.line, bad.column)
        return Comparison(OPERATOR_TEXT[token.kind], left, right, token.line, token.column)

    def _additive(self) -> object:
        left = self._multiplicative()
        while self._cursor.check(TokenKind.PLUS) or self._cursor.check(TokenKind.MINUS):
            token = self._cursor.advance()
            right = self._multiplicative()
            left = Binary(OPERATOR_TEXT[token.kind], left, right, token.line, token.column)
        return left

    def _multiplicative(self) -> object:
        left = self._unary()
        while self._cursor.check(TokenKind.STAR):
            token = self._cursor.advance()
            right = self._unary()
            left = Binary(OPERATOR_TEXT[token.kind], left, right, token.line, token.column)
        return left

    def _unary(self) -> object:
        if self._cursor.check(TokenKind.MINUS):
            token = self._cursor.advance()
            return UnaryMinus(self._unary(), token.line, token.column)
        return self._primary()

    def _primary(self) -> object:
        token = self._cursor.peek()
        if token.kind is TokenKind.NUMBER:
            self._cursor.advance()
            return IntegerLiteral(int(token.text), token.line, token.column)
        if token.kind is TokenKind.TRUE:
            return self._boolean(True, token)
        if token.kind is TokenKind.FALSE:
            return self._boolean(False, token)
        if token.kind is TokenKind.NIL:
            self._cursor.advance()
            return NilLiteral(token.line, token.column)
        if token.kind is TokenKind.INFINITY:
            self._cursor.advance()
            return InfinityLiteral(token.line, token.column)
        if token.kind is TokenKind.LPAREN:
            return self._grouped()
        if token.kind is TokenKind.FLOOR:
            self._cursor.advance()
            return self._floor(token)
        if token.kind is TokenKind.CEIL:
            self._log.reject("ceiling", CEILING_MESSAGE, token.line, token.column)
        if token.kind is TokenKind.LBRACK:
            return self._array(token)
        if token.kind is TokenKind.NAME:
            return self._name()
        raise CompileError(
            f"Expected an expression but found {token.text!r}.",
            token.line,
            token.column,
        )

    def _boolean(self, value: bool, token: Token) -> BooleanLiteral:
        self._cursor.advance()
        return BooleanLiteral(value, token.line, token.column)

    def _grouped(self) -> object:
        self._cursor.advance()
        expr = self.parse()
        self._cursor.expect(TokenKind.RPAREN)
        return expr

    def _floor(self, token: Token) -> FloorDiv:
        left = self._additive()
        if not self._cursor.check(TokenKind.SLASH):
            self._log.reject("floor", FLOOR_MESSAGE, token.line, token.column)
        return self._finish_floor(token, left)

    def _finish_floor(self, token: Token, left: object) -> FloorDiv:
        self._cursor.advance()
        right = self._additive()
        self._cursor.expect(TokenKind.FLOOR_END)
        self._log.record("floor", "division")
        return FloorDiv(left, right, token.line, token.column)

    def _reject_slash(self) -> None:
        if self._cursor.check(TokenKind.SLASH):
            token = self._cursor.peek()
            self._log.reject("slash", SLASH_MESSAGE, token.line, token.column)

    def _array(self, opening: Token) -> object:
        self._cursor.advance()
        if self._cursor.check(TokenKind.RBRACK):
            self._cursor.advance()
            return self._logged_array("literal", ArrayLiteral((), opening.line, opening.column))
        first = self.parse()
        if self._cursor.check(TokenKind.RBRACK):
            self._cursor.advance()
            return self._logged_array("allocate", Alloc(first, opening.line, opening.column))
        elements = self._literal_rest(first)
        return self._logged_array(
            "literal",
            ArrayLiteral(tuple(elements), opening.line, opening.column),
        )

    def _literal_rest(self, first: object) -> list[object]:
        elements = [first]
        while self._cursor.check(TokenKind.COMMA):
            self._cursor.advance()
            if self._cursor.check(TokenKind.RBRACK):
                break
            elements.append(self.parse())
        self._cursor.expect(TokenKind.RBRACK)
        return elements

    def _logged_array(self, outcome: str, node: object) -> object:
        self._log.record("array", outcome)
        return node

    def _name(self) -> object:
        token = self._cursor.advance()
        if self._cursor.check(TokenKind.LPAREN):
            return self._paren_call(token)
        if self._cursor.check(TokenKind.LBRACK):
            return self._brackets(token)
        return Name(token.text, token.line, token.column)

    def _paren_call(self, name: Token) -> Call:
        self._cursor.advance()
        return Call(name.text, self._arguments(TokenKind.RPAREN), "paren", name.line, name.column)

    def _arguments(self, closing: TokenKind) -> tuple[object, ...]:
        if self._cursor.check(closing):
            self._cursor.advance()
            return ()
        values = [self.parse()]
        while self._cursor.check(TokenKind.COMMA):
            self._cursor.advance()
            values.append(self.parse())
        self._cursor.expect(closing)
        return tuple(values)

    def _brackets(self, name: Token) -> object:
        self._cursor.advance()
        first = self.parse()
        if self._cursor.check(TokenKind.COMMA):
            return self._bracket_call(name, self._more_arguments(first))
        self._cursor.expect(TokenKind.RBRACK)
        return self._single_bracket(name, first)

    def _more_arguments(self, first: object) -> tuple[object, ...]:
        values = [first]
        while self._cursor.check(TokenKind.COMMA):
            self._cursor.advance()
            values.append(self.parse())
        self._cursor.expect(TokenKind.RBRACK)
        return tuple(values)

    def _bracket_call(self, name: Token, arguments: tuple[object, ...]) -> Call:
        self._log.record("bracket", "call")
        return Call(name.text, arguments, "bracket", name.line, name.column)

    def _single_bracket(self, name: Token, index: object) -> object:
        if self._scope.is_local(name.text):
            self._log.record("bracket", "index")
            target = Name(name.text, name.line, name.column)
            return Index(target, index, name.line, name.column)
        self._log.record("bracket", "attribute")
        return Attribute(name.text, index, name.line, name.column)
