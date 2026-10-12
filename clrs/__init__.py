"""Pattern: Facade. Lex, parse, lower, load, and run CLRS modules and drivers."""

from clrs.ast import Driver
from clrs.ast import Module
from clrs.bytecode import Program
from clrs.compiler import Compiler
from clrs.decisions import DecisionLog
from clrs.engine import Engine
from clrs.errors import CompileError
from clrs.errors import LinkError
from clrs.errors import LoadError
from clrs.errors import RuntimeFault
from clrs.loader import Loader
from clrs.parser import Parser

__all__ = [
    "CompileError",
    "Driver",
    "Engine",
    "LinkError",
    "LoadError",
    "Module",
    "Parser",
    "Program",
    "RuntimeFault",
    "compile_driver",
    "compile_module",
    "load_program",
    "parse_driver",
    "parse_module",
]


def parse_module(source: str) -> Module:
    return Parser().parse_module(source)


def parse_driver(source: str) -> Driver:
    return Parser().parse_driver(source)


def compile_module(source: str) -> str:
    return Compiler(source, DecisionLog()).compile(parse_module(source))


def compile_driver(source: str) -> str:
    return Compiler(source, DecisionLog()).compile(parse_driver(source))


def load_program(text: str) -> Program:
    return Loader().load(text)
