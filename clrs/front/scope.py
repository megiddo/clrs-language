"""Pattern: Repository. Names declared in one procedure or method."""


class Scope:
    """Pattern: Repository. Names declared in one procedure or method."""

    def __init__(self) -> None:
        self._names: list[str] = []

    def declare(self, name: str) -> None:
        if name not in self._names:
            self._names.append(name)

    def is_local(self, name: str) -> bool:
        return name in self._names
