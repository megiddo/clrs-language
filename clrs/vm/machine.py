"""Pattern: Command. A loop over an explicit frame stack that dispatches one command per opcode."""

import operator

from clrs.vm.arithmetic import Arithmetic
from clrs.vm.arithmetic import Compare
from clrs.vm.arithmetic import FloorDivision
from clrs.bytecode import Opcode
from clrs.bytecode import Routine
from clrs.common.decisions import DecisionLog
from clrs.vm.flow import Call
from clrs.vm.flow import Jump
from clrs.vm.flow import JumpIfFalse
from clrs.vm.flow import Return
from clrs.vm.frames import Frame
from clrs.vm.frames import FrameStack
from clrs.vm.storage import Allocate
from clrs.vm.storage import Constant
from clrs.vm.storage import Load
from clrs.vm.storage import LoadAttribute
from clrs.vm.storage import LoadIndex
from clrs.vm.storage import Pack
from clrs.vm.storage import Pop
from clrs.vm.storage import Store
from clrs.vm.storage import StoreAttribute
from clrs.vm.storage import StoreIndex
from clrs.vm.values import NIL

COMMANDS = {
    Opcode.CONST: Constant(),
    Opcode.LOAD: Load(),
    Opcode.STORE: Store(),
    Opcode.LOAD_IDX: LoadIndex(),
    Opcode.STORE_IDX: StoreIndex(),
    Opcode.LOAD_ATTR: LoadAttribute(),
    Opcode.STORE_ATTR: StoreAttribute(),
    Opcode.ADD: Arithmetic("+", operator.add),
    Opcode.SUB: Arithmetic("-", operator.sub),
    Opcode.MUL: Arithmetic("*", operator.mul),
    Opcode.FLOORDIV: FloorDivision(),
    Opcode.CMP: Compare(),
    Opcode.JUMP: Jump(),
    Opcode.JUMP_IF_FALSE: JumpIfFalse(),
    Opcode.CALL: Call(),
    Opcode.RET: Return(),
    Opcode.ALLOC: Allocate(),
    Opcode.PACK: Pack(),
    Opcode.POP: Pop(),
}


class Machine:
    """Pattern: Command. Fetches from the top frame and runs that opcode's command object."""

    def __init__(self, routines: dict[str, Routine], log: DecisionLog) -> None:
        self.log = log
        self._routines = routines
        self._frames = FrameStack(log)
        self._result: object = NIL

    def routine(self, name: str) -> Routine:
        if name not in self._routines:
            self.log.fault("procedure", f"{name} is not a loaded procedure.")
        return self._routines[name]

    def enter(self, routine: Routine, arguments: tuple[object, ...]) -> None:
        self._frames.push(Frame(routine, arguments, self.log))

    def leave(self, value: object) -> None:
        self._frames.pop()
        if self._frames.empty():
            self._result = value
            return
        self._frames.top().push(value)

    def run(self, driver: Routine) -> object:
        self.log.record("run", "driver")
        self.enter(driver, ())
        while not self._frames.empty():
            frame = self._frames.top()
            instruction = frame.fetch()
            COMMANDS[instruction.opcode].execute(self, frame, instruction)
        return self._result
