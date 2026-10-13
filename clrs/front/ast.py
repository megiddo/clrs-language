"""Pattern: Value Object. Frozen syntax trees a later visitor can walk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Import:
    """Pattern: Value Object. One `import Clrs.Sorting` line naming a module by its dotted path."""

    path: str
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_import(self)


@dataclass(frozen=True)
class Module:
    """Pattern: Value Object. A module file that does not run on its own."""

    name: str
    definitions: tuple[object, ...]
    line: int
    column: int
    imports: tuple[Import, ...] = ()

    def accept(self, visitor: object) -> object:
        return visitor.visit_module(self)


@dataclass(frozen=True)
class Procedure:
    """Pattern: Value Object. A named procedure and its body."""

    name: str
    parameters: tuple[str, ...]
    body: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_procedure(self)


@dataclass(frozen=True)
class Datatype:
    """Pattern: Value Object. A datatype, its base, and its members."""

    name: str
    base: str
    members: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_datatype(self)


@dataclass(frozen=True)
class AttributeDefault:
    """Pattern: Value Object. A datatype attribute and its recorded default."""

    name: str
    value: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_attributedefault(self)


@dataclass(frozen=True)
class Method:
    """Pattern: Value Object. A bracket method on a datatype."""

    name: str
    parameters: tuple[str, ...]
    body: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_method(self)


@dataclass(frozen=True)
class Driver:
    """Pattern: Value Object. Statements followed by a final expression."""

    statements: tuple[object, ...]
    result: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_driver(self)


@dataclass(frozen=True)
class Assign:
    """Pattern: Value Object. An assignment to a name, index, or attribute."""

    target: object
    value: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_assign(self)


@dataclass(frozen=True)
class Exchange:
    """Pattern: Value Object. An exchange of two addresses."""

    left: object
    right: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_exchange(self)


@dataclass(frozen=True)
class Return:
    """Pattern: Value Object. A return of one expression."""

    value: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_return(self)


@dataclass(frozen=True)
class ExprStmt:
    """Pattern: Value Object. A call used as a statement."""

    expression: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_exprstmt(self)


@dataclass(frozen=True)
class ForLoop:
    """Pattern: Value Object. A for loop with a direction strategy."""

    variable: str
    start: object
    direction: object
    end: object
    body: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_forloop(self)


@dataclass(frozen=True)
class WhileLoop:
    """Pattern: Value Object. A while loop and its body."""

    test: object
    body: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_whileloop(self)


@dataclass(frozen=True)
class If:
    """Pattern: Value Object. A conditional with a consequent and an alternate."""

    test: object
    consequent: tuple[object, ...]
    alternate: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_if(self)


@dataclass(frozen=True)
class Name:
    """Pattern: Value Object. A variable, procedure, or attribute name."""

    text: str
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_name(self)


@dataclass(frozen=True)
class IntegerLiteral:
    """Pattern: Value Object. An integer literal."""

    value: int
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_integerliteral(self)


@dataclass(frozen=True)
class BooleanLiteral:
    """Pattern: Value Object. The literal True or False."""

    value: bool
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_booleanliteral(self)


@dataclass(frozen=True)
class NilLiteral:
    """Pattern: Value Object. The nil literal, which is not an integer."""

    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_nilliteral(self)


@dataclass(frozen=True)
class InfinityLiteral:
    """Pattern: Value Object. The infinity literal."""

    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_infinityliteral(self)


@dataclass(frozen=True)
class And:
    """Pattern: Value Object. A short-circuit conjunction, looser than comparison."""

    left: object
    right: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_and(self)


@dataclass(frozen=True)
class Comparison:
    """Pattern: Value Object. One comparison. Comparisons do not chain."""

    operator: str
    left: object
    right: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_comparison(self)


@dataclass(frozen=True)
class Binary:
    """Pattern: Value Object. A left-associative arithmetic operation."""

    operator: str
    left: object
    right: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_binary(self)


@dataclass(frozen=True)
class UnaryMinus:
    """Pattern: Value Object. Arithmetic negation of one expression."""

    operand: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_unaryminus(self)


@dataclass(frozen=True)
class FloorDiv:
    """Pattern: Value Object. Floor of a division."""

    left: object
    right: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_floordiv(self)


@dataclass(frozen=True)
class Call:
    """Pattern: Value Object. A parenthesized or bracket call."""

    name: str
    arguments: tuple[object, ...]
    form: str
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_call(self)


@dataclass(frozen=True)
class Index:
    """Pattern: Value Object. An index of a local."""

    target: object
    index: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_index(self)


@dataclass(frozen=True)
class Attribute:
    """Pattern: Value Object. An attribute read such as length or contains."""

    name: str
    owner: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_attribute(self)


@dataclass(frozen=True)
class Alloc:
    """Pattern: Value Object. An array allocation of one size expression."""

    size: object
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_alloc(self)


@dataclass(frozen=True)
class ArrayLiteral:
    """Pattern: Value Object. An array literal, including a trailing comma."""

    elements: tuple[object, ...]
    line: int
    column: int

    def accept(self, visitor: object) -> object:
        return visitor.visit_arrayliteral(self)
