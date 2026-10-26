"""Pattern: Repository. Merges loaded module programs into one table of procedures and datatypes."""

from clrs.bytecode import DatatypeRecord
from clrs.bytecode import HEADER
from clrs.bytecode import PACKED_VERSION
from clrs.bytecode import Program
from clrs.bytecode import Routine
from clrs.common.decisions import DecisionLog


class ModuleRepository:
    """Pattern: Repository. Holds each module's .clrsa text and every procedure and datatype."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._listings: dict[str, list[str]] = {}
        self._routines: dict[str, Routine] = {}
        self._datatypes: dict[str, DatatypeRecord] = {}
        self._driver_text: str | None = None

    def merge(self, module: str, text: str, program: Program) -> None:
        if module in self._listings:
            self._log.record("module", "merge")
        else:
            self._log.record("module", "open")
        for block in program.blocks:
            self._add(module, block)
        self._listings.setdefault(module, []).append(text)

    def _add(self, module: str, block: object) -> None:
        if isinstance(block, DatatypeRecord):
            self._claim(module, block.name)
            self._log.record("module", "datatype")
            self._datatypes[block.name] = block
            return
        routine: Routine = block  # type: ignore[assignment]
        self._claim(module, routine.name)
        self._routines[routine.name] = routine

    def _claim(self, module: str, name: str) -> None:
        if name in self._routines or name in self._datatypes:
            self._log.unlinked("duplicate", f"{name} in {module} is already defined.")

    def routines(self) -> dict[str, Routine]:
        return dict(self._routines)

    def datatype(self, name: str) -> DatatypeRecord:
        if name not in self._datatypes:
            self._log.unlinked("datatype", f"{name} is not a loaded datatype.")
        return self._datatypes[name]

    def listing(self, module: str) -> str:
        if module not in self._listings:
            self._log.unlinked("module", f"{module} is not a loaded module.")
        return "".join(self._listings[module])

    def modules(self) -> tuple[str, ...]:
        return tuple(self._listings)

    def remember_driver(self, text: str) -> None:
        self._driver_text = text

    def bundle(self) -> str:
        parts = [self.listing(name) for name in self.modules()]
        if self._driver_text is not None:
            parts.append(self._driver_text)
        return "".join(parts)

    def packed(self, entry: str) -> str:
        """The bundle behind a version header, a `.module` line per module, and `.entry` before its routine."""
        named = entry in self._routines
        if named and self._driver_text is not None:
            self._log.unlinked("entry", f"entry {entry} names both a procedure and the driver.")
        if not named and self._driver_text is None:
            self._log.unlinked("entry", f"entry {entry} is not a loaded procedure, and there is no driver.")
        parts = [f"{HEADER} {PACKED_VERSION}\n"]
        for name in self.modules():
            parts.append(f".module {name}\n")
            parts.append(mark_entry(self.listing(name), f".proc {entry}", entry))
        if self._driver_text is not None:
            self._log.record("pack", "driver")
            parts.append(f".entry {entry}\n{self._driver_text}")
        else:
            self._log.record("pack", "procedure")
        return "".join(parts)


def mark_entry(text: str, header: str, entry: str) -> str:
    lines = [f".entry {entry}\n{line}" if line == header else line for line in text.split("\n")]
    return "\n".join(lines)
