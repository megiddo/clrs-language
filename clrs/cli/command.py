"""Pattern: Command. `clrs run <files> -- <driver>` loads modules, runs a driver, and prints it."""

import sys
from collections.abc import Callable
from typing import TextIO

from clrs.common.decisions import DecisionLog
from clrs.run.engine import Engine
from clrs.common.errors import CompileError
from clrs.common.errors import LinkError
from clrs.common.errors import LoadError
from clrs.common.errors import RuntimeFault
from clrs.cli.printer import ValuePrinter

USAGE = "usage: python -m clrs run <files...> -- <driver>"

FAULTS: dict[type[Exception], tuple[str, str]] = {
    CompileError: ("compile", "compile error"),
    LoadError: ("load", "load error"),
    LinkError: ("link", "link error"),
    RuntimeFault: ("runtime", "runtime fault"),
}


class UsageError(Exception):
    """Pattern: Value Object. A command line that does not match the usage line."""


class Invocation:
    """Pattern: Value Object. The files and the driver named on one command line."""

    def __init__(self, files: tuple[str, ...], driver: str) -> None:
        self.files = files
        self.driver = driver

    @classmethod
    def parse(cls, argv: list[str]) -> "Invocation":
        if argv[:1] != ["run"] or "--" not in argv:
            raise UsageError(USAGE)
        split = argv.index("--")
        rest = argv[split + 1 :]
        if len(rest) != 1:
            raise UsageError(USAGE)
        return cls(tuple(argv[1:split]), rest[0])


class Stage:
    """Pattern: Command. One step of a run, labelled with the file or driver it reads."""

    def __init__(self, label: str, action: Callable[[], object]) -> None:
        self.label = label
        self.action = action


class RunCommand:
    """Pattern: Command. Runs the stages in order and turns the first fault into exit 1."""

    def __init__(self, out: TextIO, err: TextIO, log: DecisionLog) -> None:
        self._out = out
        self._err = err
        self._log = log

    def execute(self, argv: list[str]) -> int:
        try:
            invocation = Invocation.parse(argv)
        except UsageError as error:
            self._log.record("cli", "usage")
            self._err.write(f"{error}\n")
            return 2
        self._log.record("cli", "run")
        return self._stages(invocation, Engine())

    def _stages(self, invocation: Invocation, engine: Engine) -> int:
        stages = [Stage(path, lambda path=path: engine.load_file(path)) for path in invocation.files]
        stages.append(Stage("driver", lambda: engine.run(invocation.driver)))
        result: object = None
        for stage in stages:
            try:
                result = stage.action()
            except OSError as error:
                return self._fail("file", f"{stage.label}: cannot read: {error.strerror}")
            except tuple(FAULTS) as error:
                outcome, title = FAULTS[type(error)]
                return self._fail(outcome, f"{stage.label}: {title}: {error}")
        self._out.write(ValuePrinter(self._log).render(result) + "\n")
        return 0

    def _fail(self, outcome: str, message: str) -> int:
        self._log.record("cli", outcome)
        self._err.write(message + "\n")
        return 1


def main(argv: list[str]) -> int:
    return RunCommand(sys.stdout, sys.stderr, DecisionLog()).execute(argv)
