"""clrs.mod discovery and structured imports, on real files in temporary workspaces."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from clrs import CompileError
from clrs import Engine
from clrs import LinkError
from clrs.cli import CompileCommand
from clrs.cli import RunCommand
from clrs.common.decisions import DecisionLog
from clrs.common.errors import SourceFault
from clrs.run.manifest import ManifestFinder
from clrs.vm.values import ClrsArray
from tests.paths import ROOT, SORTING as SORTING_DIR

EXAMPLES = SORTING_DIR
INSERTION_SOURCE = (SORTING_DIR / "insertion-sort.clrs").read_text(encoding="utf-8")
MANIFEST = 'module = "test.io/ws"\n\n[paths]\n"Clrs.Sorting" = "lib/sorting"\n"Clrs.Heap" = "lib/heap"\n"demo" = "cmd/demo"\n'
DEMO = "Module demo\n\nimport Clrs.Sorting\n\nRun(A)\n\tInsertionSort(A)\n\treturn A\n"
UNSORTED = "[5, 2, 4, 6, 1, 3]"


class Workspace:
    """A temporary directory tree with a clrs.mod at its root."""

    def __init__(self, test: unittest.TestCase, manifest: str = MANIFEST) -> None:
        holder = tempfile.TemporaryDirectory()
        test.addCleanup(holder.cleanup)
        self.root = Path(holder.name).resolve()
        if manifest != "":
            self.write("clrs.mod", manifest)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def sorting(self) -> Path:
        return self.write("lib/sorting/insertion-sort.clrs", INSERTION_SOURCE)


def items(value: object) -> tuple[object, ...]:
    assert isinstance(value, ClrsArray)
    return value.items()


class ImportCase(unittest.TestCase):
    def fault(self, path: Path) -> SourceFault:
        with self.assertRaises(SourceFault) as caught:
            Engine().load_entry(path)
        return caught.exception

    def assertCompileFault(self, path: Path, label: Path, message: str, line: int, column: int) -> None:
        fault = self.fault(path)
        self.assertEqual(fault.path, str(label))
        self.assertIsInstance(fault.cause, CompileError)
        cause: CompileError = fault.cause  # type: ignore[assignment]
        self.assertEqual((cause.message, cause.line, cause.column), (message, line, column))


class ResolutionTest(ImportCase):
    def test_nested_entry_finds_the_manifest_and_its_imports(self) -> None:
        workspace = Workspace(self)
        workspace.sorting()
        entry = workspace.write("cmd/demo/main.clrs", DEMO)
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.modules(), ("Clrs.Sorting", "demo"))
        self.assertEqual(items(engine.run(f"Run({UNSORTED})")), (1, 2, 3, 4, 5, 6))

    def test_every_file_in_the_mapped_directory_merges(self) -> None:
        workspace = Workspace(self)
        workspace.sorting()
        workspace.write("lib/sorting/helper.clrs", "Module Clrs.Sorting\n\nSortAll(A)\n\tInsertionSort(A)\n")
        workspace.write("lib/sorting/notes.txt", "not a source file")
        entry = workspace.write("cmd/demo/main.clrs", "Module demo\nimport Clrs.Sorting\n")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(items(engine.run("A ← [3, 1, 2]; SortAll(A); A")), (1, 2, 3))

    def test_imports_are_transitive_and_dependencies_load_first(self) -> None:
        workspace = Workspace(self)
        workspace.write("lib/heap/heap.clrs", "Module Clrs.Heap\n\nTwice(x)\n\treturn x + x\n")
        workspace.write("lib/sorting/s.clrs", "Module Clrs.Sorting\nimport Clrs.Heap\n\nFour(x)\n\treturn Twice(Twice(x))\n")
        entry = workspace.write("cmd/demo/main.clrs", "Module demo\nimport Clrs.Sorting\n\nRun(x)\n\treturn Four(x)\n")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.modules(), ("Clrs.Heap", "Clrs.Sorting", "demo"))
        self.assertEqual(engine.run("Run(3)"), 12)

    def test_a_shared_dependency_loads_once(self) -> None:
        manifest = MANIFEST + '"Left" = "lib/left"\n"Right" = "lib/right"\n'
        workspace = Workspace(self, manifest)
        workspace.write("lib/heap/h.clrs", "Module Clrs.Heap\n\nOne()\n\treturn 1\n")
        workspace.write("lib/left/l.clrs", "Module Left\nimport Clrs.Heap\n\nL()\n\treturn One()\n")
        workspace.write("lib/right/r.clrs", "Module Right\nimport Clrs.Heap\nimport Clrs.Heap\n\nR()\n\treturn One()\n")
        entry = workspace.write("main.clrs", "Module demo\nimport Left\nimport Right\n")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.modules(), ("Clrs.Heap", "Left", "Right", "demo"))
        self.assertEqual(engine.run("L() + R()"), 2)

    def test_entry_without_imports_needs_no_manifest(self) -> None:
        workspace = Workspace(self, "")
        entry = workspace.write("main.clrs", "Module M\n\nP()\n\treturn 7\n")
        engine = Engine()
        engine.load_entry(str(entry))
        self.assertEqual(engine.run("P()"), 7)

    def test_entry_in_a_mapped_directory_loads_alone(self) -> None:
        workspace = Workspace(self)
        sort = workspace.sorting()
        workspace.write("lib/sorting/broken.clrs", "Module Clrs.Sorting\nP(\n")
        engine = Engine()
        engine.load_entry(sort)
        self.assertEqual(items(engine.run("A ← [2, 1]; InsertionSort(A); A")), (1, 2))


class ImportFaultTest(ImportCase):
    def test_unknown_import(self) -> None:
        workspace = Workspace(self)
        entry = workspace.write("cmd/demo/main.clrs", "Module demo\n\nimport Clrs.Foo\n")
        message = "unknown module Clrs.Foo (not in clrs.mod of test.io/ws)."
        self.assertCompileFault(entry, entry, message, 3, 1)

    def test_unknown_import_in_a_dependency_names_that_file(self) -> None:
        workspace = Workspace(self)
        sort = workspace.write("lib/sorting/s.clrs", "Module Clrs.Sorting\nimport Nope\n")
        entry = workspace.write("main.clrs", "Module demo\nimport Clrs.Sorting\n")
        message = "unknown module Nope (not in clrs.mod of test.io/ws)."
        self.assertCompileFault(entry, sort, message, 2, 1)

    def test_import_without_a_manifest(self) -> None:
        workspace = Workspace(self, "")
        entry = workspace.write("main.clrs", "Module demo\nimport Clrs.Sorting\n")
        fault = self.fault(entry)
        self.assertEqual(fault.path, str(entry))
        self.assertTrue(fault.cause.message.startswith("No clrs.mod in "))  # type: ignore[attr-defined]
        self.assertTrue(fault.cause.message.endswith(" or above it, so Clrs.Sorting cannot be imported."))  # type: ignore[attr-defined]
        self.assertEqual((fault.cause.line, fault.cause.column), (2, 1))  # type: ignore[attr-defined]

    def test_header_mismatch_in_a_mapped_directory(self) -> None:
        workspace = Workspace(self)
        workspace.sorting()
        stray = workspace.write("lib/sorting/stray.clrs", "Module Clrs.Other\n\nP()\n\treturn 1\n")
        entry = workspace.write("cmd/demo/main.clrs", DEMO)
        message = "This file declares Module Clrs.Other, but clrs.mod maps its directory to Clrs.Sorting."
        self.assertCompileFault(entry, stray, message, 1, 1)

    def test_header_mismatch_of_the_entry_itself(self) -> None:
        workspace = Workspace(self)
        entry = workspace.write("cmd/demo/main.clrs", "Module Demo\n")
        message = "This file declares Module Demo, but clrs.mod maps its directory to demo."
        self.assertCompileFault(entry, entry, message, 1, 1)

    def test_cycle_lists_the_modules(self) -> None:
        workspace = Workspace(self)
        heap = workspace.write("lib/heap/h.clrs", "Module Clrs.Heap\nimport Clrs.Sorting\n")
        workspace.write("lib/sorting/s.clrs", "Module Clrs.Sorting\nimport Clrs.Heap\n")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Sorting\n")
        message = "Import cycle: Clrs.Sorting → Clrs.Heap → Clrs.Sorting."
        self.assertCompileFault(entry, heap, message, 2, 1)

    def test_a_module_that_imports_itself_is_a_cycle(self) -> None:
        workspace = Workspace(self)
        entry = workspace.write("cmd/demo/main.clrs", "Module demo\nimport demo\n")
        self.assertCompileFault(entry, entry, "Import cycle: demo → demo.", 2, 1)

    def test_a_mapped_directory_without_sources(self) -> None:
        workspace = Workspace(self)
        workspace.write("lib/heap/readme.txt", "empty")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Heap\n")
        message = f"Clrs.Heap maps to {workspace.root / 'lib' / 'heap'} in clrs.mod, which holds no .clrs files."
        self.assertCompileFault(entry, entry, message, 2, 1)

    def test_a_parse_error_in_a_dependency_names_that_file(self) -> None:
        workspace = Workspace(self)
        broken = workspace.write("lib/sorting/broken.clrs", "Module Clrs.Sorting\nP(\n")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Sorting\n")
        self.assertCompileFault(entry, broken, "Expected name but found 'P('.", 2, 3)

    def test_a_compile_error_after_parsing_names_its_file(self) -> None:
        workspace = Workspace(self)
        bad = workspace.write("lib/sorting/s.clrs", "Module Clrs.Sorting\n\nP()\n\treturn y\n")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Sorting\n")
        fault = self.fault(entry)
        self.assertEqual(fault.path, str(bad))
        self.assertIsInstance(fault.cause, CompileError)

    def test_unreadable_entry(self) -> None:
        workspace = Workspace(self)
        missing = workspace.root / "missing.clrs"
        fault = self.fault(missing)
        self.assertEqual(fault.path, str(missing))
        self.assertIsInstance(fault.cause, FileNotFoundError)

    def test_repo_manifest_maps_sorting_to_lib(self) -> None:
        manifest = ManifestFinder(DecisionLog()).find(EXAMPLES / "insertion-sort.clrs")
        self.assertEqual(manifest.name, "clrs.io/local")
        self.assertEqual(manifest.keys_for(EXAMPLES.resolve()), ("Clrs.Sorting",))

    def test_importing_the_repo_sorting_loads_linear_search(self) -> None:
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        holder = tempfile.TemporaryDirectory(dir=build)
        self.addCleanup(holder.cleanup)
        entry = Path(holder.name) / "main.clrs"
        entry.write_text("Module demo\nimport Clrs.Sorting\n", encoding="utf-8")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.run(f"LinearSearch({UNSORTED}, 6)"), 4)


class ManifestFaultTest(ImportCase):
    def assertManifestFault(self, text: str, message: str) -> None:
        workspace = Workspace(self, text)
        entry = workspace.write("main.clrs", "Module main\n")
        self.assertCompileFault(entry, workspace.root / "clrs.mod", message, 1, 1)

    def test_invalid_toml(self) -> None:
        fault_text = "clrs.mod is not valid TOML: Expected '=' after a key in a key/value pair (at line 1, column 7)."
        self.assertManifestFault("module\n", fault_text)

    def test_missing_module_line(self) -> None:
        self.assertManifestFault('[paths]\n"A" = "a"\n', 'clrs.mod needs a line module = "…".')
        self.assertManifestFault("module = 3\n", 'clrs.mod needs a line module = "…".')

    def test_paths_must_be_a_table(self) -> None:
        self.assertManifestFault('module = "m"\npaths = "x"\n', "[paths] in clrs.mod must be a table.")

    def test_paths_need_dotted_keys_and_string_directories(self) -> None:
        message = "[paths] entry {} must map a dotted module path to a directory string."
        self.assertManifestFault('module = "m"\n[paths]\n"lib/a" = "a"\n', message.format("'lib/a'"))
        self.assertManifestFault('module = "m"\n[paths]\n"A." = "a"\n', message.format("'A.'"))
        self.assertManifestFault('module = "m"\n[paths]\n"A" = 1\n', message.format("'A'"))

    def test_paths_are_optional(self) -> None:
        workspace = Workspace(self, 'module = "m"\n')
        entry = workspace.write("main.clrs", "Module main\n\nP()\n\treturn 1\n")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.run("P()"), 1)

    def test_require_lists_modules_that_must_be_mapped(self) -> None:
        text = 'module = "m"\n\n[require]\n"Clrs.Sorting" = "local"\n'
        self.assertManifestFault(text, "[require] lists Clrs.Sorting, but [paths] and [replace] do not map it.")

    def test_replace_overrides_paths(self) -> None:
        workspace = Workspace(
            self,
            'module = "m"\n\n[paths]\n"Clrs.Sorting" = "lib/old"\n\n[replace]\n"Clrs.Sorting" = "lib/sorting"\n',
        )
        workspace.sorting()
        entry = workspace.write("cmd/demo/main.clrs", DEMO)
        engine = Engine()
        engine.load_entry(entry)
        result = engine.run(f"Run({UNSORTED})")
        assert isinstance(result, ClrsArray)
        self.assertEqual(result.items(), (1, 2, 3, 4, 5, 6))

    def test_exclude_blocks_an_import(self) -> None:
        workspace = Workspace(
            self,
            'module = "m"\n\n[paths]\n"Clrs.Sorting" = "lib/sorting"\n\n[exclude]\n"Clrs.Sorting" = true\n',
        )
        workspace.sorting()
        entry = workspace.write("cmd/demo/main.clrs", DEMO)
        self.assertCompileFault(
            entry,
            entry,
            "module Clrs.Sorting is excluded in clrs.mod of m.",
            3,
            1,
        )

    def test_unreadable_manifest(self) -> None:
        workspace = Workspace(self, "")
        (workspace.root / "clrs.mod").mkdir()
        entry = workspace.write("main.clrs", "Module main\n")
        self.assertFalse((workspace.root / "clrs.mod").is_file())
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.modules(), ("main",))
        unreadable = workspace.write("inner/clrs.mod", 'module = "m"\n')
        unreadable.chmod(0)
        self.addCleanup(unreadable.chmod, 0o644)
        nested = workspace.write("inner/main.clrs", "Module main\n")
        if os.access(unreadable, os.R_OK):
            self.skipTest("running as a user who can read mode 000 files")
        fault = self.fault(nested)
        self.assertEqual(fault.path, str(unreadable))
        self.assertIsInstance(fault.cause, PermissionError)


class AliasTest(ImportCase):
    def test_qualified_call_reaches_a_shadowed_import(self) -> None:
        workspace = Workspace(self)
        workspace.sorting()
        source = (
            "Module demo\nimport Clrs.Sorting as Sort\n\n"
            "InsertionSort(A)\n\treturn 42\n\n"
            "Run(A)\n\tSort.InsertionSort(A)\n\treturn A\n"
        )
        entry = workspace.write("cmd/demo/main.clrs", source)
        engine = Engine()
        engine.load_entry(entry)
        result = engine.run(f"Run({UNSORTED})")
        assert isinstance(result, ClrsArray)
        self.assertEqual(result.items(), (1, 2, 3, 4, 5, 6))


class ShadowTest(ImportCase):
    def test_a_local_definition_hides_the_imported_one(self) -> None:
        workspace = Workspace(self)
        workspace.sorting()
        local = "Module demo\nimport Clrs.Sorting\n\nInsertionSort(A)\n\treturn 42\n"
        entry = workspace.write("cmd/demo/main.clrs", local)
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.run("InsertionSort([2, 1])"), 42)
        self.assertNotIn("InsertionSort", engine.listing("Clrs.Sorting"))
        self.assertEqual(engine.compiled_text().count(".proc InsertionSort\n"), 1)

    def test_shadowing_reaches_transitive_imports(self) -> None:
        workspace = Workspace(self)
        workspace.write("lib/heap/h.clrs", "Module Clrs.Heap\n\nOne()\n\treturn 1\n\nTwo()\n\treturn 2\n")
        workspace.write("lib/sorting/s.clrs", "Module Clrs.Sorting\nimport Clrs.Heap\n\nOne()\n\treturn 10\n")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Sorting\n\nTwo()\n\treturn 20\n")
        engine = Engine()
        engine.load_entry(entry)
        self.assertEqual(engine.run("One() + Two()"), 30)
        self.assertNotIn(".proc", engine.listing("Clrs.Heap"))

    def test_unrelated_modules_may_not_share_a_name(self) -> None:
        manifest = MANIFEST + '"Left" = "lib/left"\n'
        workspace = Workspace(self, manifest)
        workspace.write("lib/heap/h.clrs", "Module Clrs.Heap\n\nOne()\n\treturn 1\n")
        left = workspace.write("lib/left/l.clrs", "Module Left\n\nOne()\n\treturn 2\n")
        entry = workspace.write("main.clrs", "Module main\nimport Clrs.Heap\nimport Left\n")
        fault = self.fault(entry)
        self.assertEqual(fault.path, str(left))
        self.assertIsInstance(fault.cause, LinkError)
        self.assertEqual(str(fault.cause), "One in Left is already defined.")


class CommandLineImportTest(unittest.TestCase):
    def run_cli(self, command: type, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        status = command(out, err, DecisionLog()).execute(list(argv))
        return status, out.getvalue(), err.getvalue()

    def demo(self) -> tuple[Workspace, Path]:
        workspace = Workspace(self)
        workspace.sorting()
        return workspace, workspace.write("cmd/demo/main.clrs", DEMO)

    def test_run_resolves_imports_from_the_entry_alone(self) -> None:
        _, entry = self.demo()
        result = self.run_cli(RunCommand, "run", str(entry), "--", f"Run({UNSORTED})")
        self.assertEqual(result, (0, "[1, 2, 3, 4, 5, 6]\n", ""))

    def test_a_listed_dependency_is_not_loaded_twice(self) -> None:
        workspace, entry = self.demo()
        sort = str(workspace.root / "lib" / "sorting" / "insertion-sort.clrs")
        result = self.run_cli(RunCommand, "run", str(entry), sort, "--", "Run([2, 1])")
        self.assertEqual(result, (0, "[1, 2]\n", ""))

    def test_extra_files_still_load_after_the_graph(self) -> None:
        _, entry = self.demo()
        extra = str(EXAMPLES / "bubblesort.clrs")
        result = self.run_cli(RunCommand, "run", str(entry), extra, "--", "A ← [2, 1]; BubbleSort(A); A")
        self.assertEqual(result, (0, "[1, 2]\n", ""))

    def test_a_dependency_fault_is_labelled_with_its_file(self) -> None:
        workspace, entry = self.demo()
        stray = workspace.write("lib/sorting/stray.clrs", "Module Other\n")
        message = "1:1: This file declares Module Other, but clrs.mod maps its directory to Clrs.Sorting."
        result = self.run_cli(RunCommand, "run", str(entry), "--", "1")
        self.assertEqual(result, (1, "", f"{stray}: compile error: {message}\n"))

    def test_compile_writes_the_whole_graph(self) -> None:
        _, entry = self.demo()
        status, out, err = self.run_cli(CompileCommand, "compile", str(entry))
        self.assertEqual((status, err), (0, ""))
        self.assertLess(out.index("▷ Module Clrs.Sorting\n"), out.index("▷ Module demo\n"))
        self.assertIn(".proc InsertionSort\n", out)
        self.assertIn(".proc Run\n", out)

    def test_compile_reports_an_unknown_import(self) -> None:
        workspace = Workspace(self)
        entry = workspace.write("main.clrs", "Module main\nimport Gone\n")
        status, out, err = self.run_cli(CompileCommand, "compile", str(entry))
        message = "2:1: unknown module Gone (not in clrs.mod of test.io/ws)."
        self.assertEqual((status, out, err), (1, "", f"{entry}: compile error: {message}\n"))

    def test_python_dash_m_run_from_the_workspace(self) -> None:
        workspace, _ = self.demo()
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONWARNINGS="ignore")
        argv = [sys.executable, "-m", "clrs", "run", "cmd/demo/main.clrs", "--", f"Run({UNSORTED})"]
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", env=env, cwd=workspace.root)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "[1, 2, 3, 4, 5, 6]\n", ""))


if __name__ == "__main__":
    unittest.main()
