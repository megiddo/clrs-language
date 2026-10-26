"""Pattern: Repository. Names declared in one procedure or method."""


class Scope:
    """Pattern: Repository. Names declared in one procedure or method."""

    def __init__(self, import_aliases: frozenset[str] = frozenset()) -> None:
        self._names: list[str] = []
        self._import_aliases = import_aliases

    def declare(self, name: str) -> None:
        if name not in self._names:
            self._names.append(name)

    def is_local(self, name: str) -> bool:
        return name in self._names

    def is_import_alias(self, name: str) -> bool:
        return name in self._import_aliases
