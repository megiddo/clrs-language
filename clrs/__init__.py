"""Pattern: Facade. Lex and parse CLRS modules and drivers."""

from clrs.ast import Driver
from clrs.ast import Module
from clrs.errors import CompileError
from clrs.parser import Parser

__all__ = ["CompileError", "Driver", "Module", "Parser", "parse_driver", "parse_module"]


def parse_module(source: str) -> Module:
    return Parser().parse_module(source)


def parse_driver(source: str) -> Driver:
    return Parser().parse_driver(source)
