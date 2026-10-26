"""Pattern: Enumeration. Lexical token kinds for CLRS source."""

import enum
from dataclasses import dataclass


def column_of(offset: int) -> int:
    return offset + 1


class TokenKind(enum.Enum):
    """Pattern: Enumeration. Names each kind of lexical token."""

    EOF = "end of file"
    NEWLINE = "newline"
    INDENT = "indent"
    DEDENT = "dedent"
    NAME = "name"
    NUMBER = "number"
    MODULE = "Module"
    IMPORT = "import"
    DATATYPE = "datatype"
    EXTENDS = "extends"
    FOR = "for"
    TO = "to"
    DOWNTO = "downto"
    DO = "do"
    WHILE = "while"
    IF = "if"
    THEN = "then"
    ELSE = "else"
    RETURN = "return"
    AND = "and"
    OR = "or"
    TRUE = "True"
    FALSE = "False"
    NIL = "nil"
    ASSIGN = "←"
    EXCHANGE = "↔"
    LE = "<="
    GE = ">="
    NE = "!="
    LT = "<"
    GT = ">"
    EQ = "="
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    LPAREN = "("
    RPAREN = ")"
    LBRACK = "["
    RBRACK = "]"
    COMMA = ","
    COLON = ":"
    DOT = "."
    SEMI = ";"
    FLOOR = "⌊"
    FLOOR_END = "⌋"
    CEIL = "⌈"
    CEIL_END = "⌉"
    INFINITY = "∞"
    COMMENT = "comment"


OPERATOR_TEXT = {
    TokenKind.PLUS: "+",
    TokenKind.MINUS: "-",
    TokenKind.STAR: "*",
    TokenKind.LT: "<",
    TokenKind.GT: ">",
    TokenKind.LE: "<=",
    TokenKind.GE: ">=",
    TokenKind.EQ: "=",
    TokenKind.NE: "!=",
}

COMPARISONS = frozenset(
    {
        TokenKind.LT,
        TokenKind.GT,
        TokenKind.LE,
        TokenKind.GE,
        TokenKind.EQ,
        TokenKind.NE,
    }
)

EXPRESSION_STARTS = frozenset(
    {
        TokenKind.NAME,
        TokenKind.NUMBER,
        TokenKind.TRUE,
        TokenKind.FALSE,
        TokenKind.NIL,
        TokenKind.INFINITY,
        TokenKind.LPAREN,
        TokenKind.LBRACK,
        TokenKind.MINUS,
        TokenKind.FLOOR,
        TokenKind.CEIL,
    }
)


@dataclass(frozen=True)
class Token:
    """Pattern: Value Object. A lexeme with its source position."""

    kind: TokenKind
    text: str
    line: int
    column: int
