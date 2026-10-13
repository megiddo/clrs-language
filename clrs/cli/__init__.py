"""Pattern: Facade. Command-line entry for running CLRS drivers."""

from clrs.cli.command import RunCommand
from clrs.cli.command import USAGE
from clrs.cli.command import main

__all__ = ["RunCommand", "USAGE", "main"]
