"""Pattern: Iterator. One-token lookahead over a token sequence."""

from clrs.errors import CompileError
from clrs.tokens import Token
from clrs.tokens import TokenKind


class TokenCursor:
    """Pattern: Iterator. One-token lookahead over a token sequence."""

    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self._tokens = tokens
        self._index = 0

    def peek(self) -> Token:
        return self._tokens[self._index]

    def advance(self) -> Token:
        token = self._tokens[self._index]
        nxt = self._index + 1
        if nxt < len(self._tokens):
            self._index = nxt
        return token

    def check(self, kind: TokenKind) -> bool:
        return self.peek().kind is kind

    def expect(self, kind: TokenKind) -> Token:
        token = self.peek()
        if token.kind is not kind:
            raise CompileError(
                f"Expected {kind.value} but found {token.text!r}.",
                token.line,
                token.column,
            )
        return self.advance()

    def see(self, kind: TokenKind) -> bool:
        for found in self._tokens[self._index :]:
            if found.kind is kind:
                return True
        return False
