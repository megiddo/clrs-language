"""Pattern: Command. `clrs compile` lowers modules to .clrsa text without executing them."""

import sys
from pathlib import Path
from typing import TextIO

from clrs.common.decisions import DecisionLog
from clrs.common.errors import CompileError
from clrs.common.errors import LinkError
from clrs.common.errors import LoadError
from clrs.run.engine import Engine
from clrs.cli.command import FAULTS
from clrs.cli.command import Stage
from clrs.cli.command import UsageError

COMPILE_USAGE = "usage: python -m clrs compile <files...> [-o file.clrsa] [-- <driver>]"


class CompileInvocation:
    """Pattern: Value Object. Input files, optional output path, and optional driver source."""

    def __init__(
        self,
        files: tuple[str, ...],
        output: str | None,
        driver: str | None,
    ) -> None:
        self.files = files
        self.output = output
        self.driver = driver

    @classmethod
    def parse(cls, argv: list[str]) -> "CompileInvocation":
        if argv[:1] != ["compile"]:
            raise UsageError(COMPILE_USAGE)
        rest = argv[1:]
        if not rest:
            raise UsageError(COMPILE_USAGE)
        output: str | None = None
        files: list[str] = []
        index = 0
        while index < len(rest):
            token = rest[index]
            if token == "-o":
                if index + 1 >= len(rest):
                    raise UsageError(COMPILE_USAGE)
                output = rest[index + 1]
                index += 2
                continue
            if token == "--":
                driver = rest[index + 1 :]
                if len(driver) != 1:
                    raise UsageError(COMPILE_USAGE)
                if not files:
                    raise UsageError(COMPILE_USAGE)
                return cls(tuple(files), output, driver[0])
            files.append(token)
            index += 1
        if not files:
            raise UsageError(COMPILE_USAGE)
        return cls(tuple(files), output, None)


class CompileCommand:
    """Pattern: Command. Compiles each file, merges modules, and writes textual bytecode."""

    def __init__(self, out: TextIO, err: TextIO, log: DecisionLog) -> None:
        self._out = out
        self._err = err
        self._log = log

    def execute(self, argv: list[str]) -> int:
        try:
            invocation = CompileInvocation.parse(argv)
        except UsageError as error:
            self._log.record("cli", "usage")
            self._err.write(f"{error}\n")
            return 2
        self._log.record("cli", "compile")
        engine = Engine()
        stages = [Stage(path, lambda path=path: engine.load_file(path)) for path in invocation.files]
        if invocation.driver is not None:
            stages.append(Stage("driver", lambda: engine.compile_driver(invocation.driver)))
        for stage in stages:
            try:
                stage.action()
            except OSError as error:
                return self._fail("file", f"{stage.label}: cannot read: {error.strerror}")
            except tuple(FAULTS) as error:
                outcome, title = FAULTS[type(error)]
                return self._fail(outcome, f"{stage.label}: {title}: {error}")
        text = engine.compiled_text()
        if invocation.output is None:
            self._out.write(text)
        else:
            Path(invocation.output).write_text(text, encoding="utf-8")
        return 0

    def _fail(self, outcome: str, message: str) -> int:
        self._log.record("cli", outcome)
        self._err.write(message + "\n")
        return 1
