"""Import, manifest, and shadowing decision logs only. These tests do not assert any program result."""

import contextlib
import logging
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from clrs import CompileError
from clrs import Engine
from clrs import parse_module
from clrs.common.errors import SourceFault

MANIFEST = 'module = "test.io/ws"\n\n[paths]\n"A" = "a"\n"B" = "b"\n'
KINDS = {"import", "reject", "module", "parse"}


class ImportDecisionLogTest(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name).resolve()

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def decisions(self, action: Callable[[], object]) -> list[str]:
        with self.assertLogs("clrs", level="INFO") as captured:
            with contextlib.suppress(SourceFault, CompileError):
                action()
        for record in captured.records:
            self.assertEqual((record.name, record.levelno), ("clrs", logging.INFO))
        messages = [record.getMessage() for record in captured.records]
        return [m for m in messages if m.split()[0] in KINDS and m != "parse module"]

    def load(self, entry: str, *extras: Path) -> list[str]:
        path = self.write("main.clrs", entry)

        def action() -> None:
            engine = Engine()
            engine.load_entry(path)
            for extra in extras:
                engine.load_extra(extra)

        return self.decisions(action)

    def test_parse_import_and_reject_late_import(self) -> None:
        self.assertEqual(self.decisions(lambda: parse_module("Module M\nimport A\n")), ["parse import"])
        late = self.decisions(lambda: parse_module("Module M\nP()\n\treturn 1\nimport A\n"))
        self.assertEqual(late, ["reject import"])

    def test_standalone_entry(self) -> None:
        self.assertEqual(self.load("Module main\n")[:1], ["import standalone"])
        self.assertEqual(self.load("Module main\nimport A\n")[-1], "reject manifest")

    def test_manifest_module_and_seen(self) -> None:
        self.write("clrs.mod", MANIFEST)
        self.write("a/a.clrs", "Module A\n\nP()\n\treturn 1\n")
        self.write("b/b.clrs", "Module B\nimport A\n")
        outcomes = self.load("Module main\nimport A\nimport B\n")
        self.assertEqual(outcomes[0], "import manifest")
        imports = [m for m in outcomes if m.startswith("import ")]
        self.assertEqual(imports, ["import manifest", "import module", "import module", "import seen"])

    def test_rejections(self) -> None:
        self.write("clrs.mod", MANIFEST)
        self.assertEqual(self.load("Module main\nimport Z\n")[-1], "reject import")
        self.write("a/a.clrs", "Module Other\n")
        self.assertEqual(self.load("Module main\nimport A\n")[-1], "reject header")
        self.write("a/a.clrs", "Module A\nimport B\n")
        self.write("b/b.clrs", "Module B\nimport A\n")
        self.assertEqual(self.load("Module main\nimport A\n")[-1], "reject cycle")
        self.write("clrs.mod", "module = 1\n")
        self.assertEqual(self.load("Module main\n")[-1], "reject manifest")

    def test_shadow_and_skip(self) -> None:
        self.write("clrs.mod", MANIFEST)
        dependency = self.write("a/a.clrs", "Module A\n\nP()\n\treturn 1\n")
        outcomes = self.load("Module main\nimport A\n\nP()\n\treturn 2\n", dependency)
        modules = [m for m in outcomes if m.startswith("module ")]
        self.assertEqual(modules, ["module shadow", "module open", "module open", "module skip"])


if __name__ == "__main__":
    unittest.main()
