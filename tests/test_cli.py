"""The command line, on the real pipeline: printed values, faults on stderr, and exit codes."""

import io
import os
import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from clrs.cli import CompileCommand
from clrs.cli import COMPILE_USAGE
from clrs.cli import RunCommand
from clrs.cli import RUN_USAGE
from clrs.common.decisions import DecisionLog
from tests.paths import FIXTURES, SORTING

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = SORTING
SORT = "A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A"


def example(name: str) -> str:
    return str(EXAMPLES / name)


class CommandLineProcessTest(unittest.TestCase):
    def test_insertion_sort_through_python_dash_m(self) -> None:
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONWARNINGS="ignore")
        argv = [sys.executable, "-m", "clrs", "run", example("insertion-sort.clrs"), "--", SORT]
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "[1, 2, 3, 4, 5, 6]\n", ""))

    def test_module_main_exits_with_the_command_status(self) -> None:
        argv = ["clrs", "run", "--", "⌊-3/2⌋"]
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stdout", out):
            with self.assertRaises(SystemExit) as exited:
                runpy.run_module("clrs", run_name="__main__")
        self.assertEqual((exited.exception.code, out.getvalue()), (0, "-2\n"))

    def test_module_main_writes_faults_to_stderr(self) -> None:
        argv = ["clrs", "run", "--", "⌊1/0⌋"]
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stdout", out):
            with mock.patch.object(sys, "stderr", err), self.assertRaises(SystemExit) as exited:
                runpy.run_module("clrs", run_name="__main__")
        self.assertEqual(exited.exception.code, 1)
        self.assertEqual((out.getvalue(), err.getvalue()), ("", "driver: runtime fault: Division by zero.\n"))


class CommandLineTest(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        if argv and argv[0] == "compile":
            status = CompileCommand(out, err, DecisionLog()).execute(list(argv))
        else:
            status = RunCommand(out, err, DecisionLog()).execute(list(argv))
        return status, out.getvalue(), err.getvalue()

    def printed(self, driver: str, *files: str) -> str:
        status, out, err = self.run_cli("run", *files, "--", driver)
        self.assertEqual((status, err), (0, ""), driver)
        return out

    def test_scalars(self) -> None:
        cases = {
            "q ← 7; p ← 2; q - p + 1": "6\n",
            "0 - 12": "-12\n",
            "1 < 2": "True\n",
            "2 < 1": "False\n",
            "∞": "∞\n",
            "NIL": "NIL\n",
            "A ← [1]; A[1]": "NIL\n",
        }
        for driver, text in cases.items():
            self.assertEqual(self.printed(driver), text, driver)

    def test_arrays_by_length(self) -> None:
        self.assertEqual(self.printed("[]"), "[]\n")
        self.assertEqual(self.printed("[5,]"), "[5,]\n")
        self.assertEqual(self.printed("[5, 2]"), "[5, 2]\n")
        self.assertEqual(self.printed("[2]"), "[NIL, NIL]\n")
        self.assertEqual(self.printed("[1]"), "[NIL,]\n")
        self.assertEqual(self.printed("[True, ∞, NIL]"), "[True, ∞, NIL]\n")

    def test_nested_arrays(self) -> None:
        self.assertEqual(self.printed("B ← [1,]; [B, [], [2, 3]]"), "[[1,], [], [2, 3]]\n")

    def test_prints_only_the_last_expression(self) -> None:
        self.assertEqual(self.printed("x ← 1; x ← x + 1; x"), "2\n")

    def test_many_files_link(self) -> None:
        names = ("heap.clrs", "max-heapify.clrs", "build-max-heap.clrs", "heapsort.clrs")
        driver = "A ← [4, 1, 3, 2, 16, 9, 10, 14, 8, 7]; HeapSort(A); A"
        text = "[16, 1, 2, 3, 9, 4, 7, 8, 10, 14]\n"
        self.assertEqual(self.printed(driver, *map(example, names)), text)

    def test_insertion_sort(self) -> None:
        self.assertEqual(self.printed(SORT, example("insertion-sort.clrs")), "[1, 2, 3, 4, 5, 6]\n")

    def assert_fault(self, argv: tuple[str, ...], message: str) -> None:
        status, out, err = self.run_cli(*argv)
        self.assertEqual((status, out, err), (1, "", message + "\n"))

    def test_compile_error_in_a_file(self) -> None:
        path = str(FIXTURES / "broken-for.clrs")
        message = f"{path}: compile error: 5:22: A for loop is missing an end expression."
        self.assert_fault(("run", path, "--", "1"), message)

    def test_compile_error_in_the_driver(self) -> None:
        self.assert_fault(("run", "--", "1 or 2"), "driver: compile error: 1:3: or is not a CLRS operator.")

    def test_runtime_fault(self) -> None:
        path = example("merge.clrs")
        argv = ("run", path, "--", "A ← [3, 1]; Merge(A, 1, 1, 2); A")
        self.assert_fault(argv, "driver: runtime fault: NIL cannot be compared.")

    def test_link_error(self) -> None:
        path = example("insertion-sort.clrs")
        message = f"{path}: link error: InsertionSort in Clrs.Sorting is already defined."
        self.assert_fault(("run", path, path, "--", "1"), message)

    def test_arity_is_a_link_error_of_the_driver(self) -> None:
        path = example("insertion-sort.clrs")
        message = "driver: link error: the driver calls InsertionSort with 2 argument(s), but InsertionSort takes 1."
        self.assert_fault(("run", path, "--", "A ← [2, 1]; InsertionSort(A, 1)"), message)

    def test_unreadable_file(self) -> None:
        missing = str(ROOT / "missing.clrs")
        self.assert_fault(("run", missing, "--", "1"), f"{missing}: cannot read: No such file or directory")

    def test_first_fault_stops_the_run(self) -> None:
        bad = str(FIXTURES / "broken-for.clrs")
        status, out, err = self.run_cli("run", bad, example("insertion-sort.clrs"), "--", "⌊1/0⌋")
        self.assertEqual((status, out, err.count("\n")), (1, "", 1))
        self.assertTrue(err.startswith(f"{bad}: compile error"))

    def test_usage(self) -> None:
        cases = [
            (),
            ("run",),
            ("go", "--", "1"),
            ("run", "1"),
            ("run", "--"),
            ("run", "--", "1", "2"),
        ]
        for argv in cases:
            self.assertEqual(self.run_cli(*argv), (2, "", RUN_USAGE + "\n"), argv)

    def test_compile_writes_merged_module_to_stdout(self) -> None:
        status, out, err = self.run_cli("compile", example("insertion-sort.clrs"))
        self.assertEqual((status, err), (0, ""))
        self.assertIn(".proc InsertionSort", out)
        self.assertIn("CONST 2", out)

    def test_compile_writes_to_output_file(self) -> None:
        target = ROOT / "build" / "insertion-sort.clrsa"
        target.parent.mkdir(exist_ok=True)
        status, out, err = self.run_cli(
            "compile",
            example("insertion-sort.clrs"),
            "-o",
            str(target),
        )
        self.assertEqual((status, out, err), (0, "", ""))
        self.assertIn(".proc InsertionSort", target.read_text(encoding="utf-8"))

    def test_compile_heap_family_matches_run_link(self) -> None:
        names = ("heap.clrs", "max-heapify.clrs", "build-max-heap.clrs", "heapsort.clrs")
        status, out, err = self.run_cli("compile", *map(example, names))
        self.assertEqual((status, err), (0, ""))
        for piece in ("MaxHeapify", "BuildMaxHeap", "HeapSort", "left"):
            self.assertIn(piece, out)

    def test_compile_with_driver_appends_driver_block(self) -> None:
        status, out, err = self.run_cli(
            "compile",
            example("insertion-sort.clrs"),
            "--",
            SORT,
        )
        self.assertEqual((status, err), (0, ""))
        self.assertIn(".driver", out)
        self.assertIn("CALL InsertionSort", out)

    def test_compile_usage(self) -> None:
        self.assertEqual(self.run_cli("compile"), (2, "", COMPILE_USAGE + "\n"))
        self.assertEqual(self.run_cli("compile", "-o"), (2, "", COMPILE_USAGE + "\n"))

    def test_driver_may_look_like_a_separator(self) -> None:
        self.assertEqual(self.run_cli("run", "--", "--")[0], 1)


if __name__ == "__main__":
    unittest.main()
