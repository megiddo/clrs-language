import unittest
from pathlib import Path

from clrs.common.errors import BACKTICK_MESSAGE
from clrs.common.errors import CompileError
from clrs.common.errors import JUMP_MESSAGE
from clrs.common.errors import ONE_SPACE_MESSAGE
from clrs.common.errors import SPACE_MIX_MESSAGE
from clrs.common.errors import TAB_MIX_MESSAGE
from clrs.front.lexer import Lexer
from clrs.front.tokens import Token
from clrs.front.tokens import TokenKind as K
from tests.paths import SORTING

EXAMPLES = SORTING


def flat(source: str) -> list[tuple[K, str]]:
    return [(t.kind, t.text) for t in Lexer(source, False).tokens()[:-1]]


def kinds(source: str) -> list[K]:
    return [t.kind for t in Lexer(source, True).tokens()]


class LexErrorCase(unittest.TestCase):
    def assertCompileError(
        self, source: str, tracks: bool, message: str, line: int, column: int
    ) -> None:
        with self.assertRaises(CompileError) as caught:
            Lexer(source, tracks).tokens()
        self.assertEqual(caught.exception.message, message)
        self.assertEqual((caught.exception.line, caught.exception.column), (line, column))
        self.assertEqual(str(caught.exception), f"{line}:{column}: {message}")


class LongestAliasTest(unittest.TestCase):
    def test_exchange_beats_assign(self) -> None:
        self.assertEqual(flat("a <-> b"), [(K.NAME, "a"), (K.EXCHANGE, "<->"), (K.NAME, "b")])

    def test_assign_without_greater_than(self) -> None:
        self.assertEqual(flat("a <- b"), [(K.NAME, "a"), (K.ASSIGN, "<-"), (K.NAME, "b")])

    def test_assign_glyph_followed_by_greater_than_is_exchange(self) -> None:
        self.assertEqual(flat("a ←> b")[1], (K.EXCHANGE, "←>"))

    def test_less_equal_is_one_token_not_less_then_equal(self) -> None:
        self.assertEqual(flat("a<=b"), [(K.NAME, "a"), (K.LE, "<="), (K.NAME, "b")])
        self.assertEqual(flat("a>=b")[1], (K.GE, ">="))
        self.assertEqual(flat("a!=b")[1], (K.NE, "!="))

    def test_less_then_minus_space_is_not_assign(self) -> None:
        self.assertEqual(flat("a < -b"), [(K.NAME, "a"), (K.LT, "<"), (K.MINUS, "-"), (K.NAME, "b")])

    def test_floor_and_ceiling_spellings(self) -> None:
        self.assertEqual(
            flat("|.a/b.|"),
            [(K.FLOOR, "|."), (K.NAME, "a"), (K.SLASH, "/"), (K.NAME, "b"), (K.FLOOR_END, ".|")],
        )
        self.assertEqual(flat("|^a^|"), [(K.CEIL, "|^"), (K.NAME, "a"), (K.CEIL_END, "^|")])

    def test_pipe_greater_is_a_comment_not_a_floor(self) -> None:
        self.assertEqual(flat("a |> |. b"), [(K.NAME, "a")])

    def test_dot_inf_is_infinity_not_floor_end(self) -> None:
        self.assertEqual(flat(".Inf"), [(K.INFINITY, ".Inf")])
        self.assertEqual(flat(".|"), [(K.FLOOR_END, ".|")])
        self.assertEqual(flat("Clrs.Sorting"), [(K.NAME, "Clrs"), (K.DOT, "."), (K.NAME, "Sorting")])

    def test_glyphs_and_aliases_are_the_same_kinds(self) -> None:
        pairs = [
            ("←", "<-"),
            ("↔", "<->"),
            ("≤", "<="),
            ("≥", ">="),
            ("≠", "!="),
            ("∞", ".Inf"),
            ("⌊", "|."),
            ("⌋", ".|"),
            ("⌈", "|^"),
            ("⌉", "^|"),
        ]
        for glyph, alias in pairs:
            with self.subTest(glyph=glyph):
                self.assertEqual(flat(glyph)[0][0], flat(alias)[0][0])

    def test_single_character_operators(self) -> None:
        self.assertEqual(
            [kind for kind, _ in flat("+ - * / ( ) [ ] , : ; . = < >")],
            [
                K.PLUS, K.MINUS, K.STAR, K.SLASH, K.LPAREN, K.RPAREN, K.LBRACK,
                K.RBRACK, K.COMMA, K.COLON, K.SEMI, K.DOT, K.EQ, K.LT, K.GT,
            ],
        )


class WordTest(unittest.TestCase):
    def test_keywords(self) -> None:
        words = "Module datatype extends for to downto do while if then else return and or True False nil NIL"
        self.assertEqual(
            [kind for kind, _ in flat(words)],
            [
                K.MODULE, K.DATATYPE, K.EXTENDS, K.FOR, K.TO, K.DOWNTO, K.DO, K.WHILE,
                K.IF, K.THEN, K.ELSE, K.RETURN, K.AND, K.OR, K.TRUE, K.FALSE, K.NIL, K.NIL,
            ],
        )

    def test_names_keep_underscores_and_digits(self) -> None:
        self.assertEqual(flat("n_1 _x key2 fortune"), [
            (K.NAME, "n_1"), (K.NAME, "_x"), (K.NAME, "key2"), (K.NAME, "fortune"),
        ])

    def test_numbers_are_whole_digit_runs(self) -> None:
        self.assertEqual(flat("123+4"), [(K.NUMBER, "123"), (K.PLUS, "+"), (K.NUMBER, "4")])
        self.assertEqual(flat("+1"), [(K.PLUS, "+"), (K.NUMBER, "1")])

    def test_columns_are_one_based(self) -> None:
        tokens = Lexer("ab  <- 10", False).tokens()
        self.assertEqual([(t.line, t.column) for t in tokens[:3]], [(1, 1), (1, 5), (1, 8)])

    def test_eof_sits_on_last_line(self) -> None:
        self.assertEqual(Lexer("a\nb\nc", False).tokens()[-1], Token(K.EOF, "", 3, 1))
        self.assertEqual(Lexer("", False).tokens(), (Token(K.EOF, "", 1, 1),))
        self.assertEqual(Lexer("", True).tokens(), (Token(K.EOF, "", 1, 1),))

    def test_flat_lexing_spans_lines_without_newline_tokens(self) -> None:
        tokens = Lexer("a ;\n  b", False).tokens()
        self.assertEqual([t.kind for t in tokens], [K.NAME, K.SEMI, K.NAME, K.EOF])
        self.assertEqual((tokens[2].line, tokens[2].column), (2, 3))


class BadCharacterTest(LexErrorCase):
    def test_backtick_explains_caret_and_comment(self) -> None:
        self.assertCompileError("a `b", False, BACKTICK_MESSAGE, 1, 3)

    def test_unknown_character(self) -> None:
        self.assertCompileError("a\n @", False, "Unexpected character '@'.", 2, 2)

    def test_lone_caret_is_not_a_token(self) -> None:
        self.assertCompileError("^", False, "Unexpected character '^'.", 1, 1)


class CommentTest(unittest.TestCase):
    def test_glyph_and_pipe_comments_emit_nothing(self) -> None:
        self.assertEqual(flat("a ▷ b c"), [(K.NAME, "a")])
        self.assertEqual(flat("a|>b"), [(K.NAME, "a")])
        self.assertEqual(flat("▷ all"), [])

    def test_newline_carries_the_visible_code_without_comment(self) -> None:
        source = "Module M\nP()\n\tx ← 1 ▷ note |> more\n\ty ← 2 |> note ▷ more\n"
        newlines = [t for t in Lexer(source, True).tokens() if t.kind is K.NEWLINE]
        self.assertEqual([t.text for t in newlines], ["Module M", "P()", "x ← 1", "y ← 2"])
        repeated = "Module M\nP()\n\tx ← 1 ▷ a ▷ b\n\ty ← 2 |> a |> b\n"
        texts = [t.text for t in Lexer(repeated, True).tokens() if t.kind is K.NEWLINE]
        self.assertEqual(texts[2:], ["x ← 1", "y ← 2"])
        self.assertEqual(newlines[2].column, len("\tx ← 1 ▷ note |> more") + 1)

    def test_comment_only_line_does_not_open_or_close_a_level(self) -> None:
        with_comments = "Module M\nP()\n\tx ← 1\n\t\t\t▷ deep\n▷ shallow\n\t\t|> odd\n\ty ← 2\n"
        without = "Module M\nP()\n\tx ← 1\n\ty ← 2\n"
        self.assertEqual(kinds(with_comments), kinds(without))

    def test_first_comment_line_fixes_the_unit(self) -> None:
        source = "Module M\nP()\n  ▷ two spaces\n\tx ← 1\n"
        with self.assertRaises(CompileError) as caught:
            Lexer(source, True).tokens()
        self.assertEqual(caught.exception.message, SPACE_MIX_MESSAGE)
        self.assertEqual(caught.exception.line, 4)


class IndentTest(LexErrorCase):
    def test_insertion_sort_levels(self) -> None:
        tokens = Lexer((EXAMPLES / "insertion-sort.clrs").read_text(), True).tokens()
        marks = [(t.kind, t.line, t.column) for t in tokens if t.kind in (K.INDENT, K.DEDENT)]
        self.assertEqual(
            marks,
            [
                (K.INDENT, 4, 2),
                (K.INDENT, 5, 3),
                (K.INDENT, 8, 4),
                (K.DEDENT, 10, 1),
                (K.DEDENT, 10, 1),
                (K.DEDENT, 10, 1),
            ],
        )

    def test_code_columns_count_indent(self) -> None:
        tokens = Lexer("Module M\nP()\n\tx ← 1\n", True).tokens()
        x = [t for t in tokens if t.text == "x"][0]
        assign = [t for t in tokens if t.kind is K.ASSIGN][0]
        self.assertEqual((x.line, x.column, assign.column), (3, 2, 4))

    def test_tab_and_two_spaces_are_the_same_structure(self) -> None:
        spaced = (EXAMPLES / "bubblesort.clrs").read_text()
        tabbed = spaced.replace("  ", "\t")
        self.assertNotEqual(spaced, tabbed)
        self.assertEqual(kinds(spaced), kinds(tabbed))
        self.assertEqual(kinds(spaced).count(K.INDENT), 4)

    def test_dedent_several_levels_at_once(self) -> None:
        source = "Module M\nP()\n\tif a then\n\t\tif b then\n\t\t\tx ← 1\nQ()\n\ty ← 1\n"
        tokens = Lexer(source, True).tokens()
        q = [i for i, t in enumerate(tokens) if t.text == "Q"][0]
        self.assertEqual([t.kind for t in tokens[q - 3 : q]], [K.DEDENT, K.DEDENT, K.DEDENT])
        self.assertEqual(tokens[q - 1].line, 6)

    def test_blank_and_whitespace_lines_are_skipped(self) -> None:
        self.assertEqual(kinds("Module M\n\n   \n\t\nP()\n\tx ← 1\n"), kinds("Module M\nP()\n\tx ← 1\n"))

    def test_tab_file_rejects_spaces(self) -> None:
        self.assertCompileError("Module M\nP()\n\tx ← 1\n  y ← 2\n", True, TAB_MIX_MESSAGE, 4, 1)

    def test_tab_file_rejects_tab_then_space(self) -> None:
        self.assertCompileError("Module M\nP()\n\tx ← 1\n\t y ← 2\n", True, TAB_MIX_MESSAGE, 4, 1)

    def test_space_file_rejects_tab(self) -> None:
        self.assertCompileError("Module M\nP()\n  x ← 1\n\ty ← 2\n", True, SPACE_MIX_MESSAGE, 4, 1)

    def test_space_file_rejects_odd_spaces(self) -> None:
        self.assertCompileError("Module M\nP()\n  x ← 1\n   y ← 2\n", True, SPACE_MIX_MESSAGE, 4, 1)

    def test_one_space_indent_is_rejected(self) -> None:
        self.assertCompileError("Module M\nP()\n x ← 1\n", True, ONE_SPACE_MESSAGE, 3, 1)

    def test_jump_of_two_levels_is_rejected(self) -> None:
        self.assertCompileError("Module M\nP()\n\t\tx ← 1\n", True, JUMP_MESSAGE, 3, 3)
        self.assertCompileError("Module M\nP()\n      x ← 1\n", True, JUMP_MESSAGE, 3, 7)

    def test_jump_after_detected_unit(self) -> None:
        self.assertCompileError("Module M\nP()\n  x ← 1\n      y ← 1\n", True, JUMP_MESSAGE, 4, 7)


if __name__ == "__main__":
    unittest.main()
