"""Pattern: Visitor. Lowers a module or driver syntax tree to textual bytecode."""

from clrs.ast import AttributeDefault
from clrs.ast import Datatype
from clrs.ast import Driver
from clrs.ast import Method
from clrs.ast import Module
from clrs.ast import Procedure
from clrs.bytecode import COMMENT
from clrs.bytecode import NilConstant
from clrs.bytecode import Opcode
from clrs.control import StatementLowering
from clrs.decisions import DecisionLog
from clrs.errors import DEFAULT_MESSAGE
from clrs.listing import RoutineListing
from clrs.locals import LocalNames
from clrs.lowering import LITERALS


class Compiler:
    """Pattern: Visitor. Lowers modules, procedures, datatypes, and drivers to .clrsa lines."""

    def __init__(self, source: str, log: DecisionLog) -> None:
        self._source = tuple(source.splitlines())
        self._log = log

    def compile(self, node: Module | Driver) -> str:
        lines: list[str] = node.accept(self)  # type: ignore[assignment]
        return "".join(f"{line}\n" for line in lines)

    def visit_module(self, node: Module) -> list[str]:
        self._log.record("compile", "module")
        lines = [f"{COMMENT} Module {node.name}"]
        for definition in node.definitions:
            lines.extend(definition.accept(self))  # type: ignore[attr-defined]
        return lines

    def visit_procedure(self, node: Procedure) -> list[str]:
        self._log.record("routine", "procedure")
        return self._routine(f".proc {node.name}", node.parameters, node.body)

    def visit_method(self, node: Method) -> list[str]:
        self._log.record("routine", "method")
        return self._routine(f".proc {node.name}", node.parameters, node.body)

    def _routine(
        self,
        header: str,
        parameters: tuple[str, ...],
        body: tuple[object, ...],
    ) -> list[str]:
        listing = RoutineListing(header, LocalNames(parameters).collect(body))
        StatementLowering(listing, self._source, self._log).lower(body)
        listing.op(Opcode.CONST, NilConstant())
        listing.op(Opcode.RET)
        return listing.lines()

    def visit_datatype(self, node: Datatype) -> list[str]:
        defaults = [m for m in node.members if isinstance(m, AttributeDefault)]
        methods = [m for m in node.members if not isinstance(m, AttributeDefault)]
        lines = [f".datatype {node.name} {node.base}"]
        for default in defaults:
            lines.extend(default.accept(self))
        lines.append(".end")
        for method in methods:
            lines.extend(method.accept(self))  # type: ignore[attr-defined]
        return lines

    def visit_attributedefault(self, node: AttributeDefault) -> list[str]:
        if type(node.value) not in LITERALS:
            self._log.reject("default", DEFAULT_MESSAGE, node.line, node.column)
        self._log.record("datatype", "default")
        constant = LITERALS[type(node.value)](node.value)  # type: ignore[index]
        return [f".default {node.name} {constant.text()}"]

    def visit_driver(self, node: Driver) -> list[str]:
        self._log.record("compile", "driver")
        listing = RoutineListing(".driver", LocalNames(()).collect(node.statements))
        statements = StatementLowering(listing, self._source, self._log)
        statements.lower(node.statements)
        statements.comment(node.result)
        statements.expressions().lower(node.result)
        listing.op(Opcode.RET)
        return listing.lines()
