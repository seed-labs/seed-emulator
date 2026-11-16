from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, eq=False)
class SystemProfile:
    """Compiler-neutral identifier and inheritance link for a runtime system."""

    name: str
    subset: Optional["SystemProfile"] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("system profile name must be a non-empty string")
        if self.name != self.name.strip():
            raise ValueError("system profile name must not contain surrounding whitespace")
        if self.subset is not None and not isinstance(self.subset, SystemProfile):
            raise TypeError("system profile subset must be a SystemProfile or None")

    @property
    def value(self) -> str:
        """Return the stable profile name."""
        return self.name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SystemProfile):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def contains(self, other: "SystemProfile") -> bool:
        """Return whether this profile transitively contains another profile."""
        if not isinstance(other, SystemProfile):
            raise TypeError("other must be a SystemProfile")

        current = self.subset
        visited = {self.name}
        while current is not None:
            if current.name in visited:
                raise ValueError("system profile inheritance contains a cycle")
            if current == other:
                return True
            visited.add(current.name)
            current = current.subset
        return False
