"""Pattern: Factory Method. Finds the clrs.mod above an entry file and maps dotted module paths to directories."""

import re
import tomllib
from pathlib import Path

from clrs.common.decisions import DecisionLog
from clrs.common.errors import CompileError
from clrs.common.errors import SourceFault
from clrs.front.ast import Import

MANIFEST = "clrs.mod"
DOTTED = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


class Manifest:
    """Pattern: Value Object. The workspace name, [paths], and optional require/replace/exclude tables."""

    def __init__(
        self,
        name: str,
        paths: dict[str, Path],
        required: frozenset[str],
        excluded: frozenset[str],
    ) -> None:
        self.name = name
        self._paths = paths
        self._required = required
        self._excluded = excluded

    def directory(self, request: Import, log: DecisionLog) -> Path:
        if request.path in self._excluded:
            message = f"module {request.path} is excluded in {MANIFEST} of {self.name}."
            log.reject("exclude", message, request.line, request.column)
        if request.path not in self._paths:
            message = f"unknown module {request.path} (not in {MANIFEST} of {self.name})."
            log.reject("import", message, request.line, request.column)
        return self._paths[request.path]

    def keys_for(self, directory: Path) -> tuple[str, ...]:
        return tuple(key for key, mapped in self._paths.items() if mapped == directory)


class MissingManifest:
    """Pattern: Null Object. Stands in for clrs.mod when none is found, so any import is a compile error."""

    def __init__(self, start: Path) -> None:
        self._start = start

    def directory(self, request: Import, log: DecisionLog) -> Path:
        message = f"No {MANIFEST} in {self._start} or above it, so {request.path} cannot be imported."
        log.reject("manifest", message, request.line, request.column)

    def keys_for(self, directory: Path) -> tuple[str, ...]:
        return ()


class ManifestFinder:
    """Pattern: Factory Method. Walks up from an entry file to the nearest clrs.mod and reads it."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log

    def find(self, entry: Path) -> Manifest | MissingManifest:
        start = entry.resolve().parent
        for directory in (start, *start.parents):
            candidate = directory / MANIFEST
            if candidate.is_file():
                self._log.record("import", "manifest")
                return self.read(candidate)
        self._log.record("import", "standalone")
        return MissingManifest(start)

    def read(self, path: Path) -> Manifest:
        try:
            return self._parse(path.parent, path.read_text(encoding="utf-8"))
        except (CompileError, OSError) as error:
            raise SourceFault(str(path), error) from error

    def _parse(self, root: Path, text: str) -> Manifest:
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            self._log.reject("manifest", f"{MANIFEST} is not valid TOML: {error}.", 1, 1)
        name = data.get("module")
        if not isinstance(name, str):
            self._log.reject("manifest", f'{MANIFEST} needs a line module = "…".', 1, 1)
        table = data.get("paths", {})
        if not isinstance(table, dict):
            self._log.reject("manifest", f"[paths] in {MANIFEST} must be a table.", 1, 1)
        paths = self._paths(root, table)
        replace = data.get("replace", {})
        if not isinstance(replace, dict):
            self._log.reject("manifest", f"[replace] in {MANIFEST} must be a table.", 1, 1)
        paths.update(self._paths(root, replace))
        required = self._module_keys(data.get("require", {}), "require")
        excluded = self._module_keys(data.get("exclude", {}), "exclude")
        for key in required:
            if key not in paths:
                message = f"[require] lists {key}, but [paths] and [replace] do not map it."
                self._log.reject("manifest", message, 1, 1)
        return Manifest(name, paths, required, excluded)

    def _module_keys(self, table: object, section: str) -> frozenset[str]:
        if table == {}:
            return frozenset()
        if not isinstance(table, dict):
            self._log.reject("manifest", f"[{section}] in {MANIFEST} must be a table.", 1, 1)
        keys: set[str] = set()
        for key in table:
            if DOTTED.fullmatch(key) is None:
                message = f"[{section}] entry {key!r} must be a dotted module path."
                self._log.reject("manifest", message, 1, 1)
            keys.add(key)
        return frozenset(keys)

    def _paths(self, root: Path, table: dict[str, object]) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for key, value in table.items():
            if DOTTED.fullmatch(key) is None or not isinstance(value, str):
                message = f"[paths] entry {key!r} must map a dotted module path to a directory string."
                self._log.reject("manifest", message, 1, 1)
            paths[key] = (root / str(value)).resolve()
        return paths
