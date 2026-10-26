"""Pattern: Builder. Follows `import` lines through clrs.mod into a dependency-first load plan."""

from dataclasses import dataclass
from pathlib import Path

from clrs.common.decisions import DecisionLog
from clrs.common.errors import CompileError
from clrs.common.errors import SourceFault
from clrs.front.ast import Import
from clrs.front.ast import Module
from clrs.front.parser import Parser
from clrs.run.manifest import MANIFEST
from clrs.run.manifest import Manifest
from clrs.run.manifest import ManifestFinder
from clrs.run.manifest import MissingManifest


@dataclass(frozen=True)
class SourceFile:
    """Pattern: Value Object. One parsed .clrs file and the label its faults are reported under."""

    path: Path
    label: str
    source: str
    module: Module


@dataclass(frozen=True)
class SourceUnit:
    """Pattern: Value Object. Every file of one logical module: the entry file alone, or a mapped directory."""

    name: str
    files: tuple[SourceFile, ...]

    def imports(self) -> tuple[str, ...]:
        paths: list[str] = []
        for file in self.files:
            paths.extend(request.path for request in file.module.imports if request.path not in paths)
        return tuple(paths)

    def names(self) -> frozenset[str]:
        return frozenset(
            definition.name  # type: ignore[attr-defined]
            for file in self.files
            for definition in file.module.definitions
        )


class LoadPlan:
    """Pattern: Value Object. Units with dependencies first and the entry last, plus the names each must yield.

    A module's definitions shadow those of every module it imports, directly or transitively.
    Linking stays flat and unqualified, so a shadowed definition is dropped before it compiles.
    """

    def __init__(self, units: tuple[SourceUnit, ...]) -> None:
        self.units = units
        self._hidden: dict[str, frozenset[str]] = {unit.name: frozenset() for unit in units}
        for unit in reversed(units):
            shadow = unit.names() | self._hidden[unit.name]
            for name in unit.imports():
                self._hidden[name] = self._hidden[name] | shadow

    def hidden(self, unit: SourceUnit) -> frozenset[str]:
        return self._hidden[unit.name]

    def dependencies(self) -> tuple[Path, ...]:
        return tuple(file.path.resolve() for unit in self.units[:-1] for file in unit.files)


class ImportGraph:
    """Pattern: Builder. Walks imports depth first from an entry file, rejecting unknown modules and cycles."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._manifest: Manifest | MissingManifest = MissingManifest(Path("."))
        self._stack: list[str] = []
        self._done: set[str] = set()
        self._order: list[SourceUnit] = []

    def resolve(self, entry: Path, label: str) -> LoadPlan:
        self._manifest = ManifestFinder(self._log).find(entry)
        file = self._read(entry, label)
        self._check_header(file, self._manifest.keys_for(entry.resolve().parent))
        self._visit(SourceUnit(file.module.name, (file,)))
        return LoadPlan(tuple(self._order))

    def _visit(self, unit: SourceUnit) -> None:
        self._stack.append(unit.name)
        for file in unit.files:
            for request in file.module.imports:
                self._follow(file, request)
        self._stack.pop()
        self._done.add(unit.name)
        self._order.append(unit)

    def _follow(self, file: SourceFile, request: Import) -> None:
        if request.path in self._done:
            self._log.record("import", "seen")
            return
        try:
            directory = self._directory(request)
        except CompileError as error:
            raise SourceFault(file.label, error) from error
        self._log.record("import", "module")
        paths = sorted(directory.glob("*.clrs"))
        members = tuple(self._member(path, (request.path,)) for path in paths)
        self._visit(SourceUnit(request.path, members))

    def _directory(self, request: Import) -> Path:
        if request.path in self._stack:
            cycle = [*self._stack[self._stack.index(request.path) :], request.path]
            message = f"Import cycle: {' → '.join(cycle)}."
            self._log.reject("cycle", message, request.line, request.column)
        directory = self._manifest.directory(request, self._log)
        if not any(directory.glob("*.clrs")):
            message = f"{request.path} maps to {directory} in {MANIFEST}, which holds no .clrs files."
            self._log.reject("import", message, request.line, request.column)
        return directory

    def _member(self, path: Path, keys: tuple[str, ...]) -> SourceFile:
        file = self._read(path, str(path))
        self._check_header(file, keys)
        return file

    def _check_header(self, file: SourceFile, keys: tuple[str, ...]) -> None:
        if len(keys) == 0 or file.module.name in keys:
            return
        module = file.module
        message = f"This file declares Module {module.name}, but {MANIFEST} maps its directory to {keys[0]}."
        try:
            self._log.reject("header", message, module.line, module.column)
        except CompileError as error:
            raise SourceFault(file.label, error) from error

    def _read(self, path: Path, label: str) -> SourceFile:
        try:
            source = path.read_text(encoding="utf-8")
            module = Parser().parse_module(source)
        except (CompileError, OSError) as error:
            raise SourceFault(label, error) from error
        return SourceFile(path, label, source, module)
