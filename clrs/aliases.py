"""Pattern: Repository. Longest-match ASCII spellings of CLRS glyphs."""

from dataclasses import dataclass

from clrs.tokens import TokenKind


@dataclass(frozen=True)
class AliasHit:
    """Pattern: Value Object. One alias match, or a miss of length zero."""

    kind: TokenKind
    length: int
    text: str


_MISS = AliasHit(TokenKind.EOF, 0, "")

# Shorter spellings are listed first. Match order is longest-first, so
# `<->` wins over `<-` and `.Inf` wins over `.|`.
_ALIASES = (
    ("<-", TokenKind.ASSIGN),
    ("<=", TokenKind.LE),
    (">=", TokenKind.GE),
    ("!=", TokenKind.NE),
    ("<->", TokenKind.EXCHANGE),
    ("←>", TokenKind.EXCHANGE),
    ("|>", TokenKind.COMMENT),
    ("|.", TokenKind.FLOOR),
    (".|", TokenKind.FLOOR_END),
    ("|^", TokenKind.CEIL),
    ("^|", TokenKind.CEIL_END),
    (".Inf", TokenKind.INFINITY),
)


def _spelling_length(item: tuple[str, TokenKind]) -> int:
    return len(item[0])


class AliasTable:
    """Pattern: Repository. Longest-match ASCII spellings of CLRS glyphs."""

    def __init__(self) -> None:
        self._ordered = tuple(sorted(_ALIASES, key=_spelling_length, reverse=True))

    def match(self, text: str) -> AliasHit:
        for spelling, kind in self._ordered:
            if text.startswith(spelling):
                return AliasHit(kind, len(spelling), spelling)
        return _MISS
