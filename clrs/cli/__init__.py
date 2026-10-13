"""Pattern: Facade. Command-line entry for running, compiling, and packing CLRS programs."""

from clrs.cli.command import RunCommand
from clrs.cli.command import RUN_USAGE
from clrs.cli.command import USAGE
from clrs.cli.command import main
from clrs.cli.compile_command import COMPILE_USAGE
from clrs.cli.compile_command import CompileCommand
from clrs.cli.pack_command import PACK_USAGE
from clrs.cli.pack_command import PackCommand

__all__ = [
    "COMPILE_USAGE",
    "CompileCommand",
    "PACK_USAGE",
    "PackCommand",
    "RUN_USAGE",
    "RunCommand",
    "USAGE",
    "main",
]
