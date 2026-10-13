"""Pattern: Facade. Loads .clrs files and runs a driver through lex, parse, .clrsa, load, and execute."""

from dataclasses import replace
from pathlib import Path

from clrs.bytecode import DatatypeRecord
from clrs.bytecode import Program
from clrs.bytecode import Routine
from clrs.bytecode.compiler import Compiler
from clrs.common.decisions import DecisionLog
from clrs.common.errors import CompileError
from clrs.common.errors import LinkError
from clrs.common.errors import LoadError
from clrs.common.errors import SourceFault
from clrs.bytecode.loader import Loader
from clrs.front.ast import Module
from clrs.vm.machine import Machine
from clrs.run.imports import ImportGraph
from clrs.run.imports import SourceFile
from clrs.run.linker import Linker
from clrs.run.modules import ModuleRepository
from clrs.front.parser import Parser


def is_driver(block: object) -> bool:
    return isinstance(block, Routine) and block.directive == ".driver"


class Engine:
    """Pattern: Facade. One entry point over the parser, compiler, loader, and machine.

    `load_file` loads exactly one file and ignores its imports. `load_entry` follows imports through clrs.mod.
    `packed_text` writes a packed .clrsa; `run_entry` runs one without a driver.
    """

    def __init__(self) -> None:
        self._log = DecisionLog()
        self._modules = ModuleRepository(self._log)
        self._dependencies: set[Path] = set()

    @classmethod
    def of(cls, *paths: Path | str) -> "Engine":
        engine = cls()
        for path in paths:
            engine.load_file(path)
        return engine

    def load_file(self, path: Path | str) -> None:
        self.load_source(Path(path).read_text(encoding="utf-8"))

    def load_source(self, source: str) -> None:
        module = Parser().parse_module(source)
        text = Compiler(source, self._log).compile(module)
        self._modules.merge(module.name, text, Loader().load(text))

    def load_entry(self, path: Path | str) -> None:
        """Load an entry file and, dependencies first, every module it imports. Faults name their file."""
        plan = ImportGraph(self._log).resolve(Path(path), str(path))
        for unit in plan.units:
            hidden = plan.hidden(unit)
            for file in unit.files:
                self._load_parsed(file, hidden)
        self._dependencies.update(plan.dependencies())

    def load_extra(self, path: Path | str) -> None:
        """Load one more listed file, unless the import graph already loaded it as a dependency."""
        if Path(path).resolve() in self._dependencies:
            self._log.record("module", "skip")
            return
        self.load_file(path)

    def _load_parsed(self, file: SourceFile, hidden: frozenset[str]) -> None:
        module = self._without(file.module, hidden)
        try:
            text = Compiler(file.source, self._log).compile(module)
            self._modules.merge(module.name, text, Loader().load(text))
        except (CompileError, LoadError, LinkError) as error:
            raise SourceFault(file.label, error) from error

    def _without(self, module: Module, hidden: frozenset[str]) -> Module:
        kept: list[object] = []
        for definition in module.definitions:
            if definition.name in hidden:  # type: ignore[attr-defined]
                self._log.record("module", "shadow")
                continue
            kept.append(definition)
        return replace(module, definitions=tuple(kept))

    def compile_driver(self, source: str) -> str:
        text = Compiler(source, self._log).compile(Parser().parse_driver(source))
        self._modules.remember_driver(text)
        return text

    def run(self, source: str) -> object:
        program = Loader().load(self.compile_driver(source))
        driver: Routine = program.blocks[0]  # type: ignore[assignment]
        routines = self._modules.routines()
        Linker(self._log).link(routines, driver)
        return Machine(routines, self._log).run(driver)

    def packed_text(self, entry: str) -> str:
        """Return the loaded modules and driver as a packed .clrsa whose `.entry` names `entry`."""
        text = self._modules.packed(entry)
        routines = self._modules.routines()
        if entry in routines:
            self._check_entry(routines[entry])
        return text

    def load_packed(self, path: Path | str) -> Program:
        return Loader().load(Path(path).read_text(encoding="utf-8"))

    def run_entry(self, program: Program) -> object:
        """Link every procedure and datatype of a packed program, then run its `.entry` with no driver."""
        if program.entry is None:
            self._log.unlinked("entry", "There is no .entry to run; write one with clrs pack.")
        entry = program.entry_routine()
        library = tuple(block for block in program.blocks if not is_driver(block))
        self._modules.merge("packed", program.text(), Program(library))
        self._check_entry(entry)
        routines = self._modules.routines()
        Linker(self._log).link(routines, entry)
        return Machine(routines, self._log).run(entry)

    def _check_entry(self, entry: Routine) -> None:
        if entry.parameters:
            count = len(entry.parameters)
            self._log.unlinked("entry", f"entry {entry.name} takes {count} argument(s), but an entry takes none.")

    def listing(self, module: str) -> str:
        return self._modules.listing(module)

    def compiled_text(self) -> str:
        """Return merged module bytecode and any driver block compiled on this engine."""
        return self._modules.bundle()

    def modules(self) -> tuple[str, ...]:
        return self._modules.modules()

    def datatype(self, name: str) -> DatatypeRecord:
        return self._modules.datatype(name)
