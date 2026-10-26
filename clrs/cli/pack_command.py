"""Pattern: Command. `clrs pack` links an entry's import graph into one runnable .clrsa with an `.entry`."""

from pathlib import Path
from typing import TextIO

from clrs.common.decisions import DecisionLog
from clrs.run.engine import Engine
from clrs.cli.command import STAGE_FAULTS
from clrs.cli.command import Stage
from clrs.cli.command import UsageError
from clrs.cli.command import describe
from clrs.cli.command import file_stages

PACK_USAGE = "usage: python -m clrs pack <entry.clrs> [files...] [-- <driver>] [-o app.clrsa] [--entry name]"
OPTIONS = {"--": "driver", "-o": "output", "--entry": "entry"}
DEFAULT_ENTRY = "main"


class PackInvocation:
    """Pattern: Value Object. Input files and the driver, output, and entry options, each given at most once."""

    def __init__(self, files: tuple[str, ...], options: dict[str, str]) -> None:
        self.files = files
        self.options = options
        self.entry = options.get("entry", DEFAULT_ENTRY)

    @classmethod
    def parse(cls, argv: list[str]) -> "PackInvocation":
        if argv[:1] != ["pack"]:
            raise UsageError(PACK_USAGE)
        rest = argv[1:]
        files: list[str] = []
        options: dict[str, str] = {}
        index = 0
        while index < len(rest):
            token = rest[index]
            if token not in OPTIONS:
                files.append(token)
                index += 1
                continue
            if index + 1 == len(rest) or OPTIONS[token] in options:
                raise UsageError(PACK_USAGE)
            options[OPTIONS[token]] = rest[index + 1]
            index += 2
        invocation = cls(tuple(files), options)
        if not files or invocation.entry.split() != [invocation.entry]:
            raise UsageError(PACK_USAGE)
        return invocation


class PackCommand:
    """Pattern: Command. Loads the entry's graph, compiles the driver, and writes the packed text."""

    def __init__(self, out: TextIO, err: TextIO, log: DecisionLog) -> None:
        self._out = out
        self._err = err
        self._log = log

    def execute(self, argv: list[str]) -> int:
        try:
            invocation = PackInvocation.parse(argv)
        except UsageError as error:
            self._log.record("cli", "usage")
            self._err.write(f"{error}\n")
            return 2
        self._log.record("cli", "pack")
        engine = Engine()
        stages = file_stages(invocation.files, engine)
        if "driver" in invocation.options:
            stages.append(Stage("driver", lambda: engine.compile_driver(invocation.options["driver"])))
        stages.append(Stage("pack", lambda: engine.packed_text(invocation.entry)))
        text: object = ""
        for stage in stages:
            try:
                text = stage.action()
            except STAGE_FAULTS as error:
                return self._fail(*describe(stage.label, error))
        if "output" in invocation.options:
            Path(invocation.options["output"]).write_text(str(text), encoding="utf-8")
        else:
            self._out.write(str(text))
        return 0

    def _fail(self, outcome: str, message: str) -> int:
        self._log.record("cli", outcome)
        self._err.write(message + "\n")
        return 1
