"""Pattern: Factory. Chooses whether a for loop counts up or down."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CountUp:
    """Pattern: Strategy. The for-loop variable counts up."""

    def label(self) -> str:
        return "up"


@dataclass(frozen=True)
class CountDown:
    """Pattern: Strategy. The for-loop variable counts down."""

    def label(self) -> str:
        return "down"


class Directions:
    """Pattern: Factory. Chooses whether a for loop counts up or down."""

    def choose(self, keyword: str) -> CountUp | CountDown:
        if keyword == "to":
            return CountUp()
        return CountDown()
