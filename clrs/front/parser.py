"""Pattern: Facade. Parses a CLRS module or a driver into an AST."""

from clrs.front.ast import AttributeDefault
from clrs.front.ast import Datatype
from clrs.front.ast import Driver
from clrs.front.ast import Import
from clrs.front.ast import Method
from clrs.front.ast import Module
from clrs.front.ast import Procedure
from clrs.front.cursor import TokenCursor
from clrs.common.decisions import DecisionLog
from clrs.common.errors import CompileError
from clrs.common.errors import ALIAS_MESSAGE
from clrs.common.errors import DUPLICATE_ALIAS_MESSAGE
from clrs.common.errors import IMPORT_MESSAGE
from clrs.common.errors import LENGTH_MESSAGE
from clrs.front.expressions import ExpressionBuilder
from clrs.front.lexer import Lexer
from clrs.front.scope import Scope
from clrs.front.statements import StatementBuilder
from clrs.front.statements import declare
from clrs.front.statements import position_of
from clrs.front.tokens import Token
from clrs.front.tokens import TokenKind


class ModuleBuilder:
    """Pattern: Builder. Builds a module syntax tree from tokens."""

    def __init__(self, tokens: tuple[Token, ...], log: DecisionLog) -> None:
        self._cursor = TokenCursor(tokens)
        self._log = log
        self._import_aliases = frozenset[str]()

    def parse(self) -> Module:
        token = self._cursor.expect(TokenKind.MODULE)
        name = self._dotted()
        self._cursor.expect(TokenKind.NEWLINE)
        imports: list[Import] = []
        while self._cursor.check(TokenKind.IMPORT):
            imports.append(self._import())
        self._check_aliases(imports)
        self._import_aliases = frozenset(item.alias for item in imports if item.alias)
        definitions: list[object] = []
        while not self._cursor.check(TokenKind.EOF):
            definitions.append(self._definition())
        return Module(name, tuple(definitions), token.line, token.column, tuple(imports))

    def _import(self) -> Import:
        token = self._cursor.advance()
        self._log.record("parse", "import")
        path = self._dotted()
        alias: str | None = None
        if self._cursor.check(TokenKind.AS):
            self._cursor.advance()
            alias_token = self._cursor.expect(TokenKind.NAME)
            if self._cursor.check(TokenKind.DOT):
                self._log.reject("alias", ALIAS_MESSAGE, alias_token.line, alias_token.column)
            alias = alias_token.text
        self._cursor.expect(TokenKind.NEWLINE)
        return Import(path, token.line, token.column, alias)

    def _check_aliases(self, imports: list[Import]) -> None:
        seen: set[str] = set()
        for item in imports:
            if item.alias is None:
                continue
            if item.alias in seen:
                self._log.reject("alias", DUPLICATE_ALIAS_MESSAGE, item.line, item.column)
            seen.add(item.alias)

    def _dotted(self) -> str:
        name = self._cursor.expect(TokenKind.NAME)
        parts = [name.text]
        while self._cursor.check(TokenKind.DOT):
            self._cursor.advance()
            parts.append(self._cursor.expect(TokenKind.NAME).text)
        return ".".join(parts)

    def _definition(self) -> object:
        if self._cursor.check(TokenKind.DATATYPE):
            return self._datatype()
        if self._cursor.check(TokenKind.NAME):
            return self._procedure()
        token = self._cursor.peek()
        if token.kind is TokenKind.IMPORT:
            self._log.reject("import", IMPORT_MESSAGE, token.line, token.column)
        raise CompileError(
            f"Expected a definition but found {token.text!r}.",
            token.line,
            token.column,
        )

    def _procedure(self) -> Procedure:
        name = self._cursor.expect(TokenKind.NAME)
        self._cursor.expect(TokenKind.LPAREN)
        scope = Scope(self._import_aliases)
        parameters = self._names(TokenKind.RPAREN, scope)
        if self._cursor.check(TokenKind.COLON):
            self._cursor.advance()
        self._cursor.expect(TokenKind.NEWLINE)
        body = StatementBuilder(self._cursor, scope, self._log, True).parse_suite()
        return Procedure(name.text, parameters, body, name.line, name.column)

    def _datatype(self) -> Datatype:
        token = self._cursor.advance()
        name = self._cursor.expect(TokenKind.NAME)
        self._cursor.expect(TokenKind.EXTENDS)
        base = self._cursor.expect(TokenKind.NAME)
        self._cursor.expect(TokenKind.COLON)
        self._cursor.expect(TokenKind.NEWLINE)
        self._cursor.expect(TokenKind.INDENT)
        members: list[object] = []
        while not self._cursor.check(TokenKind.DEDENT):
            members.append(self._member())
        self._cursor.expect(TokenKind.DEDENT)
        return Datatype(name.text, base.text, tuple(members), token.line, token.column)

    def _member(self) -> object:
        name = self._cursor.expect(TokenKind.NAME)
        if name.text == "length":
            self._log.reject("length", LENGTH_MESSAGE, name.line, name.column)
        if self._cursor.check(TokenKind.ASSIGN):
            return self._default(name)
        if self._cursor.check(TokenKind.LBRACK):
            return self._method(name)
        token = self._cursor.peek()
        raise CompileError(
            f"Expected a datatype member but found {token.text!r}.",
            token.line,
            token.column,
        )

    def _default(self, name: Token) -> AttributeDefault:
        self._cursor.advance()
        value = ExpressionBuilder(self._cursor, Scope(), self._log).parse()
        self._cursor.expect(TokenKind.NEWLINE)
        return AttributeDefault(name.text, value, name.line, name.column)

    def _method(self, name: Token) -> Method:
        self._cursor.expect(TokenKind.LBRACK)
        scope = Scope(self._import_aliases)
        parameters = self._names(TokenKind.RBRACK, scope)
        self._cursor.expect(TokenKind.COLON)
        self._cursor.expect(TokenKind.NEWLINE)
        body = StatementBuilder(self._cursor, scope, self._log, True).parse_suite()
        return Method(name.text, parameters, body, name.line, name.column)

    def _names(self, closing: TokenKind, scope: Scope) -> tuple[str, ...]:
        if self._cursor.check(closing):
            self._cursor.advance()
            return ()
        names: list[str] = []
        while True:
            token = self._cursor.expect(TokenKind.NAME)
            declare(scope, self._log, token.text, token.line, token.column)
            names.append(token.text)
            if not self._cursor.check(TokenKind.COMMA):
                break
            self._cursor.advance()
        self._cursor.expect(closing)
        return tuple(names)


class DriverBuilder:
    """Pattern: Builder. Builds a driver syntax tree from tokens."""

    def __init__(self, tokens: tuple[Token, ...], log: DecisionLog) -> None:
        self._cursor = TokenCursor(tokens)
        self._log = log

    def parse(self) -> Driver:
        scope = Scope()
        statements_builder = StatementBuilder(self._cursor, scope, self._log, False)
        statements: list[object] = []
        while self._cursor.see(TokenKind.SEMI):
            statements.append(statements_builder.parse_statement())
            self._cursor.expect(TokenKind.SEMI)
        result = statements_builder.expressions().parse()
        self._cursor.expect(TokenKind.EOF)
        anchor = self._anchor(statements, result)
        line, column = position_of(anchor)
        return Driver(tuple(statements), result, line, column)

    def _anchor(self, statements: list[object], result: object) -> object:
        if len(statements) > 0:
            return statements[0]
        return result


class Parser:
    """Pattern: Facade. Parses a CLRS module or a driver into an AST."""

    def parse_module(self, source: str) -> Module:
        log = DecisionLog()
        log.record("parse", "module")
        return ModuleBuilder(Lexer(source, True).tokens(), log).parse()

    def parse_driver(self, source: str) -> Driver:
        log = DecisionLog()
        log.record("parse", "driver")
        return DriverBuilder(Lexer(source, False).tokens(), log).parse()
