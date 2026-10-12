"""Pattern: Repository. Merges loaded module programs into one table of procedures and datatypes."""

from clrs.bytecode import DatatypeRecord
from clrs.bytecode import Program
from clrs.bytecode import Routine
from clrs.decisions import DecisionLog


class ModuleRepository:
    """Pattern: Repository. Holds each module's .clrsa text and every procedure and datatype."""

    def __init__(self, log: DecisionLog) -> None:
        self._log = log
        self._listings: dict[str, list[str]] = {}
        self._routines: dict[str, Routine] = {}
        self._datatypes: dict[str, DatatypeRecord] = {}

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
