"""Pattern: Specification. Checks every CALL against its callee's parameter count before a run."""

from clrs.bytecode import Opcode
from clrs.bytecode import Routine
from clrs.common.decisions import DecisionLog


class Linker:
    """Pattern: Specification. A CALL links only when its argument count equals the callee's .param count.

    A callee that is not loaded is left to the machine, which faults only if the call runs.
    """

    def __init__(self, log: DecisionLog) -> None:
        self._log = log

    def link(self, routines: dict[str, Routine], driver: Routine) -> None:
        for routine in (*routines.values(), driver):
            self._check(routines, routine)

    def _check(self, routines: dict[str, Routine], caller: Routine) -> None:
        for instruction in caller.instructions:
            if instruction.opcode is not Opcode.CALL:
                continue
            name = str(instruction.operands[0])
            count = int(instruction.operands[1])  # type: ignore[call-overload]
            if name not in routines:
                self._log.record("link", "deferred")
                continue
            takes = len(routines[name].parameters)
            if count != takes:
                who = caller.name or "the driver"
                message = f"{who} calls {name} with {count} argument(s), but {name} takes {takes}."
                self._log.unlinked("arity", message)
            self._log.record("link", "call")
