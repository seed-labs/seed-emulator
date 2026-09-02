"""Candidate-agent providers (design principle 12: provider-agnostic evaluation)."""

from benchmark_agent.providers.base import ActionProvider, CandidateProvider
from benchmark_agent.providers.openai_compat import OpenAICompatibleProvider

__all__ = ["ActionProvider", "CandidateProvider", "OpenAICompatibleProvider"]
