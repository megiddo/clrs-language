import unittest
from pathlib import Path

from clrs_lint.lint import COMMENT_GLYPH, lint_text, lint_path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

CLEAN = (
    "insertion-sort.clrs",
    "merge.clrs",
    "mergesort.clrs",
    "bubblesort.clrs",
    "heapsort.clrs",
    "max-heapify.clrs",
    "build-max-heap.clrs",
    "heap.clrs",
)


class LintExamplesTest(unittest.TestCase):
    def test_clean_examples_have_no_diagnostics(self) -> None:
        for name in CLEAN:
            with self.subTest(name=name):
                self.assertEqual(lint_path(EXAMPLES / name), [])

    def test_linear_search_for_has_no_direction(self) -> None:
        diagnostics = lint_path(EXAMPLES / "linear-search.clrs")
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].line, 5)
        self.assertIn("to", diagnostics[0].message)
        self.assertIn("downto", diagnostics[0].message)

    def test_indent_under_an_assignment_is_an_error(self) -> None:
        source = "Sort(A)\n\tq ← 1\n\t\tSort(A)\n"
        diagnostics = lint_text(source, "<stdin>")
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].line, 3)
        self.assertIn("does not open a block", diagnostics[0].message)
        self.assertIn("q ← 1", diagnostics[0].message)

    def test_for_needs_an_end_expression_after_to(self) -> None:
        source = "Sort(A)\n\tfor i ← length[A] to\n\t\tx ← i\n"
        diagnostics = lint_text(source, "<stdin>")
        self.assertEqual(diagnostics[0].line, 2)
        self.assertIn("end expression", diagnostics[0].message)

    def test_ascii_for_with_a_bound_is_legal(self) -> None:
        source = "Sort(A)\n\tfor i <- 1 to length[A] do\n\t\tx <- A[i]\n"
        self.assertEqual(lint_text(source, "<stdin>"), [])

    def test_backtick_is_not_a_comment(self) -> None:
        source = "Sort(A)\n\t` v is the subject\n"
        diagnostics = lint_text(source, "<stdin>")
        self.assertEqual(len(diagnostics), 1)
        self.assertIn("Backtick is not a CLRS token", diagnostics[0].message)
        self.assertIn("caret", diagnostics[0].message)

    def test_backtick_inside_a_real_comment_is_fine(self) -> None:
        source = f"Sort(A)\n\t{COMMENT_GLYPH} the ` character\n"
        self.assertEqual(lint_text(source, "<stdin>"), [])

    def test_comment_glyph_is_the_preprocessor_target(self) -> None:
        script = (ROOT / "lang" / "preprocessor_001.sh").read_text(encoding="utf-8")
        self.assertEqual(COMMENT_GLYPH, "\u25b7")
        self.assertIn("|>/" + COMMENT_GLYPH, script)
        self.assertIn("|^", script)
        self.assertIn("^|", script)
        self.assertNotIn("`", script)


if __name__ == "__main__":
    unittest.main()
