"""Candidate-agent provider contract (design principle 12)."""

from collections.abc import Callable
from typing import Any, Protocol

# Every provider turns the conversation into one validated candidate action plus
# provider metadata. All providers speak the same Adapter action protocol, so the
# evaluation loop never depends on which vendor produced the decision.
ActionProvider = Callable[[list[dict[str, str]]], tuple[dict[str, str], dict[str, Any]]]


class CandidateProvider(Protocol):
    """Interface implemented by every candidate-agent provider."""

    name: str

    def decide(
        self, messages: list[dict[str, str]]
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Return (action, provider_metadata) for the current conversation."""

        ...
