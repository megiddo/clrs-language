"""Pattern: Value Object. Compile failures and the messages they carry."""

LENGTH_MESSAGE = "length cannot be shadowed or stored."
FOR_DIRECTION_MESSAGE = 'A for loop needs "to" or "downto" and an end expression.'
FOR_END_MESSAGE = "A for loop is missing an end expression."
OR_MESSAGE = "or is not a CLRS operator."
CEILING_MESSAGE = "Ceiling is not a CLRS operator."
FLOOR_MESSAGE = "A floor expression must be a division."
SLASH_MESSAGE = "/ is legal only as the operator inside a floor division."
CHAIN_MESSAGE = "Comparisons do not chain."
JUMP_MESSAGE = "Indent increased by more than one level."
ONE_SPACE_MESSAGE = "Indentation must be a tab or two spaces."
TAB_MIX_MESSAGE = "This file indents with tabs. This line uses spaces."
SPACE_MIX_MESSAGE = (
    "This file indents with two spaces. This line uses a tab or an odd number of spaces."
)
BACKTICK_MESSAGE = (
    "Backtick is not a CLRS token. Comments start with ▷ (type |>). "
    "Ceiling brackets are |^ and ^| with a caret, not a backtick."
)
TARGET_MESSAGE = "This value cannot be assigned."
BLOCK_INTRO = "which does not open a block."
DEFAULT_MESSAGE = "A datatype default must be a literal."


class CompileError(Exception):
    """Pattern: Value Object. A compile failure at one source position."""

    def __init__(self, message: str, line: int, column: int) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{line}:{column}: {message}")


class LoadError(Exception):
    """Pattern: Value Object. A .clrsa load failure on one line of text."""

    def __init__(self, message: str, line: int) -> None:
        self.message = message
        self.line = line
        super().__init__(f"{line}: {message}")


class RuntimeFault(Exception):
    """Pattern: Value Object. A failure while the machine executes loaded bytecode."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class LinkError(Exception):
    """Pattern: Value Object. Loaded modules that cannot be merged into one program."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
