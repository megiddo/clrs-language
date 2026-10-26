"""Pattern: Iterator. Yields tokens from CLRS source, including indent."""

from clrs.front.aliases import AliasTable
from clrs.common.decisions import DecisionLog
from clrs.common.errors import BACKTICK_MESSAGE
from clrs.common.errors import CompileError
from clrs.common.errors import JUMP_MESSAGE
from clrs.front.indent import IndentStrategy
from clrs.front.tokens import Token
from clrs.front.tokens import TokenKind
from clrs.front.tokens import column_of

_KEYWORDS = {
    "Module": TokenKind.MODULE,
    "import": TokenKind.IMPORT,
    "as": TokenKind.AS,
    "datatype": TokenKind.DATATYPE,
    "extends": TokenKind.EXTENDS,
    "for": TokenKind.FOR,
    "to": TokenKind.TO,
    "downto": TokenKind.DOWNTO,
    "do": TokenKind.DO,
    "while": TokenKind.WHILE,
    "if": TokenKind.IF,
    "then": TokenKind.THEN,
    "else": TokenKind.ELSE,
    "return": TokenKind.RETURN,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
    "True": TokenKind.TRUE,
    "False": TokenKind.FALSE,
    "nil": TokenKind.NIL,
    "NIL": TokenKind.NIL,
}

_SINGLES = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "[": TokenKind.LBRACK,
    "]": TokenKind.RBRACK,
    ",": TokenKind.COMMA,
    ":": TokenKind.COLON,
    ";": TokenKind.SEMI,
    ".": TokenKind.DOT,
    "=": TokenKind.EQ,
    "<": TokenKind.LT,
    ">": TokenKind.GT,
    "←": TokenKind.ASSIGN,
    "↔": TokenKind.EXCHANGE,
    "≤": TokenKind.LE,
    "≥": TokenKind.GE,
    "≠": TokenKind.NE,
    "∞": TokenKind.INFINITY,
    "⌊": TokenKind.FLOOR,
    "⌋": TokenKind.FLOOR_END,
    "⌈": TokenKind.CEIL,
    "⌉": TokenKind.CEIL_END,
}


class Lexer:
    """Pattern: Iterator. Yields tokens from CLRS source, including indent."""

    def __init__(self, source: str, tracks_indent: bool) -> None:
        self._source = source
        self._tracks_indent = tracks_indent
        self._log = DecisionLog()
        self._aliases = AliasTable()
        self._indent = IndentStrategy()
        self._unit_logged = False

    def tokens(self) -> tuple[Token, ...]:
        if self._tracks_indent:
            return self._tokenize_indented()
        return self._tokenize_flat()

    def _lines(self) -> list[tuple[int, str]]:
        rows = self._source.splitlines()
        if len(rows) == 0:
            return [(1, "")]
        return list(enumerate(rows, start=1))

    def _tokenize_flat(self) -> tuple[Token, ...]:
        tokens: list[Token] = []
        last = 1
        for line_number, line in self._lines():
            last = line_number
            tokens.extend(self._scan_code(line, line_number, 0))
        tokens.append(Token(TokenKind.EOF, "", last, 1))
        return tuple(tokens)

    def _tokenize_indented(self) -> tuple[Token, ...]:
        tokens: list[Token] = []
        stack = [0]
        last = 1
        for line_number, line in self._lines():
            last = line_number
            if line.strip() == "":
                continue
            self._take_line(line, line_number, stack, tokens)
        self._close_stack(stack, tokens, last)
        tokens.append(Token(TokenKind.EOF, "", last, 1))
        return tuple(tokens)

    def _take_line(
        self,
        line: str,
        line_number: int,
        stack: list[int],
        tokens: list[Token],
    ) -> None:
        measured = self._indent.measure(line)
        self._log_unit()
        if measured.problem != "":
            self._log.reject("indent", measured.problem, line_number, 1)
        if self._opens_comment(measured.body):
            self._log.record("comment", "keep")
            return
        self._fit_stack(stack, tokens, measured.level, line_number, measured.width)
        tokens.extend(self._scan_code(measured.body, line_number, measured.width))
        tokens.append(
            Token(
                TokenKind.NEWLINE,
                self._visible(measured.body),
                line_number,
                column_of(len(line)),
            )
        )

    def _log_unit(self) -> None:
        if self._unit_logged:
            return
        name = self._indent.unit()
        if name == "":
            return
        self._unit_logged = True
        self._log.record("indent", name)

    def _fit_stack(
        self,
        stack: list[int],
        tokens: list[Token],
        level: int,
        line_number: int,
        width: int,
    ) -> None:
        current = stack[-1]
        if level > current:
            self._open_level(stack, tokens, level, current, line_number, width)
            return
        while stack[-1] > level:
            stack.pop()
            tokens.append(Token(TokenKind.DEDENT, "", line_number, 1))

    def _open_level(
        self,
        stack: list[int],
        tokens: list[Token],
        level: int,
        current: int,
        line_number: int,
        width: int,
    ) -> None:
        if level != current + 1:
            self._log.reject("indent", JUMP_MESSAGE, line_number, column_of(width))
        stack.append(level)
        tokens.append(Token(TokenKind.INDENT, "", line_number, column_of(width)))

    def _close_stack(self, stack: list[int], tokens: list[Token], line_number: int) -> None:
        while len(stack) > 1:
            stack.pop()
            tokens.append(Token(TokenKind.DEDENT, "", line_number, 1))

    def _scan_code(self, text: str, line: int, indent_width: int) -> list[Token]:
        tokens: list[Token] = []
        remaining = text
        offset = 0
        while remaining != "":
            if remaining[:1] in " \t":
                remaining = remaining[1:]
                offset = offset + 1
                continue
            if self._opens_comment(remaining):
                self._log.record("comment", "keep")
                break
            column = column_of(indent_width + offset)
            token, size = self._read_token(remaining, line, column)
            tokens.append(token)
            remaining = remaining[size:]
            offset = offset + size
        return tokens

    def _opens_comment(self, text: str) -> bool:
        if text.startswith("▷"):
            return True
        return self._aliases.match(text).kind is TokenKind.COMMENT

    def _visible(self, text: str) -> str:
        return text[: self._comment_cut(text)].rstrip()

    def _comment_cut(self, text: str) -> int:
        cut = len(text)
        glyph = text.find("▷")
        if glyph >= 0 and glyph < cut:
            cut = glyph
        pipe = text.find("|>")
        if pipe >= 0 and pipe < cut:
            cut = pipe
        return cut

    def _read_token(self, text: str, line: int, column: int) -> tuple[Token, int]:
        hit = self._aliases.match(text)
        if hit.length != 0:
            return Token(hit.kind, hit.text, line, column), hit.length
        return self._read_plain(text, line, column)

    def _read_plain(self, text: str, line: int, column: int) -> tuple[Token, int]:
        char = text[:1]
        if char.isdigit():
            return self._read_number(text, line, column)
        if char.isalpha() or char == "_":
            return self._read_name(text, line, column)
        if char == "`":
            raise CompileError(BACKTICK_MESSAGE, line, column)
        kind = _SINGLES.get(char)
        if kind is None:
            raise CompileError(f"Unexpected character {char!r}.", line, column)
        return Token(kind, char, line, column), 1

    def _read_number(self, text: str, line: int, column: int) -> tuple[Token, int]:
        size = 1
        while size < len(text) and text[size].isdigit():
            size = size + 1
        return Token(TokenKind.NUMBER, text[:size], line, column), size

    def _read_name(self, text: str, line: int, column: int) -> tuple[Token, int]:
        size = 1
        while size < len(text) and self._name_continues(text[size]):
            size = size + 1
        lexeme = text[:size]
        return Token(_KEYWORDS.get(lexeme, TokenKind.NAME), lexeme, line, column), size

    def _name_continues(self, char: str) -> bool:
        return char.isalnum() or char == "_"
