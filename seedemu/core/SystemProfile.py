from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


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

    @staticmethod
    def validateProfiles(profiles: Iterable["SystemProfile"]) -> None:
        """Require one consistent definition per alias, including its ancestors.

        Equal definitions can be referenced repeatedly. Validation is scoped to
        the supplied profiles, without a process-wide registration table.
        """
        definitions = {}
        for profile in profiles:
            if not isinstance(profile, SystemProfile):
                raise TypeError("profiles must contain SystemProfile objects")
            visited = set()
            current = profile
            while current is not None:
                if current.name in visited:
                    raise ValueError("system profile inheritance contains a cycle at {}".format(current.name))
                visited.add(current.name)
                parent = current.subset.name if current.subset is not None else None
                if current.name in definitions and definitions[current.name] != parent:
                    raise ValueError(
                        "Conflicting system profile definitions for {}: subset {} versus {}".format(
                            current.name, definitions[current.name], parent))
                definitions[current.name] = parent
                current = current.subset

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
