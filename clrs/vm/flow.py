"""Pattern: Command. Executors for JUMP, JUMP_IF_FALSE, CALL, and RET on the frame stack."""

from clrs.bytecode import Instruction
from clrs.bytecode import Target
from clrs.vm.frames import Frame
from clrs.vm.values import is_boolean
from clrs.vm.values import kind


class Jump:
    """Pattern: Command. JUMP moves the program counter to a resolved label."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        target: Target = instruction.operands[0]  # type: ignore[assignment]
        frame.jump(target.index)


class JumpIfFalse:
    """Pattern: Command. JUMP_IF_FALSE pops a boolean and jumps only when it is False."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        log = machine.log  # type: ignore[attr-defined]
        test = frame.pop()
        if not is_boolean(test):
            log.fault("condition", f"A condition must be a boolean, not {kind(test)}.")
        if test:
            log.record("branch", "through")
            return
        log.record("branch", "taken")
        target: Target = instruction.operands[0]  # type: ignore[assignment]
        frame.jump(target.index)


class Call:
    """Pattern: Command. CALL pushes a new frame; arguments bind the callee's parameters."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        name = str(instruction.operands[0])
        arity = int(instruction.operands[1])  # type: ignore[call-overload]
        routine = machine.routine(name)  # type: ignore[attr-defined]
        if arity != len(routine.parameters):
            message = f"{name} takes {len(routine.parameters)} argument(s), not {arity}."
            machine.log.fault("arity", message)  # type: ignore[attr-defined]
        arguments = frame.pop_many(arity)
        machine.log.record("call", "procedure")  # type: ignore[attr-defined]
        machine.enter(routine, arguments)  # type: ignore[attr-defined]


class Return:
    """Pattern: Command. RET pops this frame and hands its value to the caller or the driver."""

    def execute(self, machine: object, frame: Frame, instruction: Instruction) -> None:
        machine.leave(frame.pop())  # type: ignore[attr-defined]
