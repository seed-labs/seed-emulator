"""Benchmark agent configuration loaded from benchmarks/config.json.

Candidate-model settings live here so vendors can be swapped without code
changes (design principle 12). API keys are never stored in the config file:
each entry only names the environment variable that carries the secret.
"""

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


@dataclass(frozen=True)
class CandidateConfig:
    """Endpoint, model, and credential channel for the native candidate provider."""

    provider_name: str
    model: str
    base_url: str
    api_key_env: str


@dataclass(frozen=True)
class BenchmarkConfig:
    """Single source of truth for candidate-model wiring."""

    candidate: CandidateConfig
    inspect_model: str

    @classmethod
    def load(cls, path: Path | None = None) -> "BenchmarkConfig":
        config_path = path or DEFAULT_CONFIG_PATH
        if not config_path.exists():
            raise FileNotFoundError(f"benchmark config not found: {config_path}")
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        candidate = raw["candidate"]
        return cls(
            candidate=CandidateConfig(
                provider_name=candidate["provider_name"],
                model=candidate["model"],
                base_url=candidate["base_url"],
                api_key_env=candidate["api_key_env"],
            ),
            inspect_model=raw["inspect_model"],
        )
