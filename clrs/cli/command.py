"""Pattern: Command. `clrs run` executes drivers or a packed .clrsa; `clrs compile` and `clrs pack` write .clrsa."""

import sys
from collections.abc import Callable
from typing import TextIO

from clrs.common.decisions import DecisionLog
from clrs.run.engine import Engine
from clrs.common.errors import CompileError
from clrs.common.errors import LinkError
from clrs.common.errors import LoadError
from clrs.common.errors import RuntimeFault
from clrs.common.errors import SourceFault
from clrs.cli.printer import ValuePrinter

RUN_USAGE = "usage: python -m clrs run [<entry.clrs> [files...]] -- <driver> | <app.clrsa>"
USAGE = RUN_USAGE

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
            raise UsageError(RUN_USAGE)
        split = argv.index("--")
        rest = argv[split + 1 :]
        if len(rest) != 1:
            raise UsageError(RUN_USAGE)
        return cls(tuple(argv[1:split]), rest[0])


def is_packed(argv: list[str]) -> bool:
    """`run app.clrsa` with no other argument runs the packed file's .entry."""
    return len(argv) == 2 and argv[0] == "run" and argv[1].endswith(".clrsa")


class Stage:
    """Pattern: Command. One step of a run, labelled with the file or driver it reads."""

    def __init__(self, label: str, action: Callable[[], object]) -> None:
        self.label = label
        self.action = action


STAGE_FAULTS = (OSError, SourceFault, *FAULTS)


def file_stages(files: tuple[str, ...], engine: Engine) -> list[Stage]:
    """The first file is the entry and pulls in its imports; later files are loaded one by one."""
    entry = [Stage(path, lambda path=path: engine.load_entry(path)) for path in files[:1]]
    extras = [Stage(path, lambda path=path: engine.load_extra(path)) for path in files[1:]]
    return entry + extras


def describe(label: str, error: Exception) -> tuple[str, str]:
    """Return the decision outcome and the stderr line for a fault raised by a stage."""
    if isinstance(error, SourceFault):
        return describe(error.path, error.cause)
    if isinstance(error, OSError):
        return "file", f"{label}: cannot read: {error.strerror}"
    outcome, title = FAULTS[type(error)]
    return outcome, f"{label}: {title}: {error}"


class RunCommand:
    """Pattern: Command. Runs the stages in order and turns the first fault into exit 1."""

    def __init__(self, out: TextIO, err: TextIO, log: DecisionLog) -> None:
        self._out = out
        self._err = err
        self._log = log

    def execute(self, argv: list[str]) -> int:
        if is_packed(argv):
            return self._packed(argv[1])
        try:
            invocation = Invocation.parse(argv)
        except UsageError as error:
            self._log.record("cli", "usage")
            self._err.write(f"{error}\n")
            return 2
        self._log.record("cli", "run")
        engine = Engine()
        stages = file_stages(invocation.files, engine)
        stages.append(Stage("driver", lambda: engine.run(invocation.driver)))
        return self._stages(stages)

    def _packed(self, path: str) -> int:
        self._log.record("cli", "packed")
        engine = Engine()
        return self._stages([Stage(path, lambda: engine.run_entry(engine.load_packed(path)))])

    def _stages(self, stages: list[Stage]) -> int:
        result: object = None
        for stage in stages:
            try:
                result = stage.action()
            except STAGE_FAULTS as error:
                return self._fail(*describe(stage.label, error))
        self._out.write(ValuePrinter(self._log).render(result) + "\n")
        return 0

    def _fail(self, outcome: str, message: str) -> int:
        self._log.record("cli", outcome)
        self._err.write(message + "\n")
        return 1


def main(argv: list[str]) -> int:
    from clrs.cli.compile_command import COMPILE_USAGE
    from clrs.cli.compile_command import CompileCommand
    from clrs.cli.pack_command import PACK_USAGE
    from clrs.cli.pack_command import PackCommand

    log = DecisionLog()
    commands = {"run": RunCommand, "compile": CompileCommand, "pack": PackCommand}
    if argv[:1] and argv[0] in commands:
        return commands[argv[0]](sys.stdout, sys.stderr, log).execute(argv)
    sys.stderr.write(RUN_USAGE + "\n" + COMPILE_USAGE + "\n" + PACK_USAGE + "\n")
    log.record("cli", "usage")
    return 2
