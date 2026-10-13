"""Pattern: Facade. Loads .clrs files and runs a driver through lex, parse, .clrsa, load, and execute."""

from pathlib import Path

from clrs.bytecode import DatatypeRecord
from clrs.bytecode import Routine
from clrs.bytecode.compiler import Compiler
from clrs.common.decisions import DecisionLog
from clrs.bytecode.loader import Loader
from clrs.vm.machine import Machine
from clrs.run.linker import Linker
from clrs.run.modules import ModuleRepository
from clrs.front.parser import Parser


class Engine:
    """Pattern: Facade. One entry point over the parser, compiler, loader, and machine."""

    def __init__(self) -> None:
        self._log = DecisionLog()
        self._modules = ModuleRepository(self._log)

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

    def listing(self, module: str) -> str:
        return self._modules.listing(module)

    def compiled_text(self) -> str:
        """Return merged module bytecode and any driver block compiled on this engine."""
        return self._modules.bundle()

    def modules(self) -> tuple[str, ...]:
        return self._modules.modules()

    def datatype(self, name: str) -> DatatypeRecord:
        return self._modules.datatype(name)
