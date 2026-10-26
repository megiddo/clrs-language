"""Packed .clrsa: the ▷ clrsa 1 header, .module and .entry, clrs pack, and clrs run app.clrsa."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from clrs import Engine
from clrs import LinkError
from clrs import LoadError
from clrs import load_program
from clrs.cli import PACK_USAGE
from clrs.cli import PackCommand
from clrs.cli import RUN_USAGE
from clrs.cli import RunCommand
from clrs.cli import main
from clrs.common.decisions import DecisionLog
from clrs.vm.values import ClrsArray

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SORT = "A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A"
HEAP = ("heap.clrs", "max-heapify.clrs", "build-max-heap.clrs", "heapsort.clrs")
HEAP_DRIVER = "A ← [4, 1, 3, 2, 16, 9, 10, 14, 8, 7]; HeapSort(A); A"
PROC = ".proc P\nCONST 7\nRET\n.end\n"
DRIVER = ".driver\nCONST 1\nRET\n.end\n"
MAIN = "Module demo\n\nimport Clrs.Sorting\n\nMain()\n\tA ← [3, 1, 2]\n\tInsertionSort(A)\n\treturn A\n"


def example(name: str) -> str:
    return str(EXAMPLES / name)


def items(value: object) -> tuple[object, ...]:
    assert isinstance(value, ClrsArray)
    return value.items()


class Scratch:
    """A temporary directory for packed files and small workspaces."""

    def __init__(self, test: unittest.TestCase) -> None:
        holder = tempfile.TemporaryDirectory()
        test.addCleanup(holder.cleanup)
        self.root = Path(holder.name).resolve()

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def workspace(self) -> Path:
        self.write("clrs.mod", 'module = "test.io/pack"\n\n[paths]\n"Clrs.Sorting" = "lib"\n')
        self.write("lib/insertion-sort.clrs", (EXAMPLES / "insertion-sort.clrs").read_text(encoding="utf-8"))
        return self.write("cmd/main.clrs", MAIN)


class LoaderTest(unittest.TestCase):
    def test_library_text_has_no_version_and_no_entry(self) -> None:
        program = load_program(PROC)
        self.assertEqual((program.format_version, program.entry), (0, None))

    def test_header_sets_the_format_version(self) -> None:
        program = load_program(f"▷ clrsa 1\n{PROC}")
        self.assertEqual((program.format_version, program.entry), (1, None))
        self.assertEqual(load_program(f"  ▷   clrsa   1  \n{PROC}").format_version, 1)

    def test_a_header_after_line_one_is_a_comment(self) -> None:
        self.assertEqual(load_program(f"\n▷ clrsa 1\n{PROC}").format_version, 0)
        for first in ("▷ clrsa merged from p.clrs", "▷ clrsa", "▷ clrsa 1 x", "▷ clrsa -1", "▷ clrs 1"):
            with self.subTest(first=first):
                self.assertEqual(load_program(f"{first}\n{PROC}").format_version, 0)

    def test_entry_names_the_driver(self) -> None:
        program = load_program(f"▷ clrsa 1\n{PROC}.entry main\n{DRIVER}")
        self.assertEqual(program.entry, "main")
        self.assertIs(program.entry_routine(), program.blocks[1])

    def test_entry_names_a_procedure(self) -> None:
        program = load_program(f"▷ clrsa 1\n.module M\n.entry P\n{PROC}.proc Q\nRET\n.end\n")
        self.assertEqual(program.entry_routine().name, "P")
        self.assertIs(program.entry_routine(), program.blocks[0])

    def test_entry_resolves_by_name_wherever_it_is_written(self) -> None:
        program = load_program(f"▷ clrsa 1\n.proc Q\nRET\n.end\n{PROC}.entry P\n")
        self.assertIs(program.entry_routine(), program.blocks[1])

    def test_text_round_trips_the_header_and_entry(self) -> None:
        text = f"▷ clrsa 1\n.module M\n{PROC}.entry main\n{DRIVER}"
        program = load_program(text)
        self.assertEqual(program.text(), f"▷ clrsa 1\n{PROC}.entry main\n{DRIVER}")
        self.assertEqual(load_program(program.text()), program)
        self.assertEqual(load_program(PROC).text(), PROC)

    FAULTS = [
        ("▷ clrsa 2\n", 1, "Only ▷ clrsa 1 can be loaded."),
        ("▷ clrsa 01\n", 1, "Only ▷ clrsa 1 can be loaded."),
        (f"{PROC}.entry P\n", 5, ".entry needs the ▷ clrsa 1 header on line 1."),
        (f"\n▷ clrsa 1\n.entry P\n{PROC}", 3, ".entry needs the ▷ clrsa 1 header on line 1."),
        (f"▷ clrsa 1\n.entry main\n.entry main\n{DRIVER}", 3, "A second .entry; the first is on line 2."),
        (f"▷ clrsa 1\n.entry Q\n{PROC}", 2, ".entry Q names no .proc, and there is no .driver."),
        ("▷ clrsa 1\n.entry H\n.datatype H Array\n.end\n", 2, ".entry H names no .proc, and there is no .driver."),
        (f"▷ clrsa 1\n.entry P\n{PROC}{DRIVER}", 2, ".entry P is ambiguous: 2 routines could run."),
        (f"▷ clrsa 1\n.entry main\n{DRIVER}{DRIVER}", 2, ".entry main is ambiguous: 2 routines could run."),
        ("▷ clrsa 1\n.proc P\n.entry P\nRET\n.end\n", 3, ".entry cannot appear inside .proc P."),
        (".driver\n.module M\n.end\n", 2, ".module cannot appear inside .driver."),
        (".entry\n", 1, ".entry takes 1 operand(s)."),
        (".module A B\n", 1, ".module takes 1 operand(s)."),
    ]

    def test_faults(self) -> None:
        for text, line, message in self.FAULTS:
            with self.subTest(text=text):
                with self.assertRaises(LoadError) as caught:
                    load_program(text)
                self.assertEqual((caught.exception.line, caught.exception.message), (line, message))


class EnginePackTest(unittest.TestCase):
    def packed(self, entry: str, driver: str, *paths: str) -> str:
        engine = Engine()
        engine.load_entry(paths[0])
        for path in paths[1:]:
            engine.load_extra(path)
        if driver != "":
            engine.compile_driver(driver)
        return engine.packed_text(entry)

    def run_packed(self, text: str) -> object:
        engine = Engine()
        return engine.run_entry(load_program(text))

    def test_insertion_sort_packs_and_runs_without_a_driver(self) -> None:
        text = self.packed("main", SORT, example("insertion-sort.clrs"))
        self.assertTrue(text.startswith("▷ clrsa 1\n.module Clrs.Sorting\n"))
        self.assertIn(".end\n.entry main\n.driver\n", text)
        self.assertEqual(text.count(".entry"), 1)
        self.assertEqual(items(self.run_packed(text)), (1, 2, 3, 4, 5, 6))

    def test_a_driver_may_take_any_entry_name(self) -> None:
        text = self.packed("demo", SORT, example("insertion-sort.clrs"))
        self.assertIn(".entry demo\n.driver\n", text)
        self.assertEqual(load_program(text).entry, "demo")

    def test_the_heap_family_matches_a_driver_run(self) -> None:
        paths = [example(name) for name in HEAP]
        expected = items(Engine.of(*paths).run(HEAP_DRIVER))
        text = self.packed("main", HEAP_DRIVER, *paths)
        self.assertIn(".datatype Heap", text)
        self.assertEqual(items(self.run_packed(text)), expected)

    def test_a_procedure_entry_through_the_import_graph(self) -> None:
        entry = Scratch(self).workspace()
        text = self.packed("Main", "", str(entry))
        self.assertEqual(text.count(".module "), 2)
        self.assertIn(".module demo\n", text)
        self.assertIn("\n.entry Main\n.proc Main\n", text)
        self.assertNotIn(".driver", text)
        self.assertEqual(items(self.run_packed(text)), (1, 2, 3))

    def test_pack_rejects_unrunnable_entries(self) -> None:
        sort = example("insertion-sort.clrs")
        cases = [
            (("InsertionSort", SORT, sort), "entry InsertionSort names both a procedure and the driver."),
            (("main", "", sort), "entry main is not a loaded procedure, and there is no driver."),
            (("InsertionSort", "", sort), "entry InsertionSort takes 1 argument(s), but an entry takes none."),
        ]
        for arguments, message in cases:
            with self.subTest(entry=arguments[0]):
                with self.assertRaises(LinkError) as caught:
                    self.packed(*arguments)
                self.assertEqual(str(caught.exception), message)

    def test_run_entry_faults_before_the_machine(self) -> None:
        cases = [
            (PROC, "There is no .entry to run; write one with clrs pack."),
            ("▷ clrsa 1\n.entry F\n.proc F\n.param n\nRET\n.end\n", "entry F takes 1 argument(s), but an entry takes none."),
            (f"▷ clrsa 1\n{PROC}{PROC}.entry main\n{DRIVER}", "P in packed is already defined."),
            (f"▷ clrsa 1\n{PROC}.entry main\n.driver\nCALL P 1\nRET\n.end\n", "main calls P with 1 argument(s), but P takes 0."),
        ]
        for text, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(LinkError) as caught:
                    self.run_packed(text)
                self.assertEqual(str(caught.exception), message.replace("main calls", "the driver calls"))

    def test_a_procedure_entry_runs_with_its_callees(self) -> None:
        text = "▷ clrsa 1\n.entry Main\n.proc Main\nCALL P 0\nRET\n.end\n" + PROC
        self.assertEqual(self.run_packed(text), 7)


class CommandLinePackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = Scratch(self)
        self.app = str(self.scratch.root / "app.clrsa")

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        command = PackCommand if argv[:1] == ("pack",) else RunCommand
        status = command(out, err, DecisionLog()).execute(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_pack_then_run_insertion_sort(self) -> None:
        packed = self.run_cli("pack", example("insertion-sort.clrs"), "--", SORT, "-o", self.app)
        self.assertEqual(packed, (0, "", ""))
        self.assertEqual(self.run_cli("run", self.app), (0, "[1, 2, 3, 4, 5, 6]\n", ""))

    def test_pack_writes_to_stdout_without_an_output(self) -> None:
        status, out, err = self.run_cli("pack", example("insertion-sort.clrs"), "--", SORT)
        self.assertEqual((status, err), (0, ""))
        self.assertTrue(out.startswith("▷ clrsa 1\n"))
        self.assertIn(".entry main\n", out)

    def test_pack_options_in_any_order_with_a_named_procedure_entry(self) -> None:
        entry = str(self.scratch.workspace())
        self.assertEqual(self.run_cli("pack", "-o", self.app, "--entry", "Main", entry), (0, "", ""))
        self.assertEqual(self.run_cli("run", self.app), (0, "[1, 2, 3]\n", ""))

    def test_pack_faults(self) -> None:
        sort = example("insertion-sort.clrs")
        missing = str(ROOT / "missing.clrs")
        cases = [
            (("pack", missing, "--", "1"), f"{missing}: cannot read: No such file or directory"),
            (("pack", sort, "--", "1 or 2"), "driver: compile error: 1:3: or is not a CLRS operator."),
            (("pack", sort), "pack: link error: entry main is not a loaded procedure, and there is no driver."),
        ]
        for argv, message in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(*argv), (1, "", message + "\n"))

    def test_pack_usage(self) -> None:
        sort = example("insertion-sort.clrs")
        cases = [
            ("pack",),
            ("pack", "--", "1"),
            ("pack", sort, "-o"),
            ("pack", sort, "--"),
            ("pack", sort, "-o", "a.clrsa", "-o", "b.clrsa"),
            ("pack", sort, "--", "1", "--", "2"),
            ("pack", sort, "--entry", "two words"),
            ("pack", sort, "--entry", ""),
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(*argv), (2, "", PACK_USAGE + "\n"))
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(PackCommand(out, err, DecisionLog()).execute(["compile", sort]), 2)

    def test_run_packed_faults(self) -> None:
        library = str(self.scratch.write("lib.clrsa", PROC))
        future = str(self.scratch.write("future.clrsa", f"▷ clrsa 2\n{PROC}"))
        zero = str(self.scratch.write("zero.clrsa", "▷ clrsa 1\n.entry main\n.driver\nCONST 1\nCONST 0\nFLOORDIV\nRET\n.end\n"))
        missing = str(self.scratch.root / "missing.clrsa")
        cases = [
            (library, f"{library}: link error: There is no .entry to run; write one with clrs pack."),
            (future, f"{future}: load error: 1: Only ▷ clrsa 1 can be loaded."),
            (zero, f"{zero}: runtime fault: Division by zero."),
            (missing, f"{missing}: cannot read: No such file or directory"),
        ]
        for path, message in cases:
            with self.subTest(path=path):
                self.assertEqual(self.run_cli("run", path), (1, "", message + "\n"))

    def test_only_a_lone_clrsa_argument_runs_packed(self) -> None:
        self.assertEqual(self.run_cli("run", "app.clrs"), (2, "", RUN_USAGE + "\n"))
        status, out, err = self.run_cli("run", self.app, "--", "1")
        self.assertEqual((status, out), (1, ""))
        self.assertTrue(err.startswith(f"{self.app}: cannot read"))

    def test_main_dispatches_pack_and_lists_every_usage(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            self.assertEqual(main(["pack", example("insertion-sort.clrs"), "--", "1"]), 0)
            self.assertTrue(out.getvalue().startswith("▷ clrsa 1\n"))
            self.assertEqual(main(["compile", example("insertion-sort.clrs")]), 0)
            self.assertNotIn(".entry", out.getvalue().split("▷ Module", 2)[2])
            for argv in ([], ["bogus"]):
                self.assertEqual(main(argv), 2)
        usage = err.getvalue().splitlines()
        self.assertEqual(len(usage), 6)
        self.assertEqual(usage[2], PACK_USAGE)
        self.assertEqual(usage[0], RUN_USAGE)


class PackProcessTest(unittest.TestCase):
    def test_python_dash_m_pack_then_run(self) -> None:
        app = str(Scratch(self).root / "app.clrsa")
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONWARNINGS="ignore")
        clrs = [sys.executable, "-m", "clrs"]
        pack = [*clrs, "pack", example("insertion-sort.clrs"), "--", SORT, "-o", app]
        done = subprocess.run(pack, capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        done = subprocess.run([*clrs, "run", app], capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "[1, 2, 3, 4, 5, 6]\n", ""))


if __name__ == "__main__":
    unittest.main()
