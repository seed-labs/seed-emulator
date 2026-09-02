"""Tests for the config-driven candidate wiring (no vendor hardcoding)."""

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from benchmark_agent.config import BenchmarkConfig
from benchmark_agent.scenario import load_scenario

_SCENARIO = Path(__file__).with_name("fixtures") / "runtime_scenario.json"

_CONFIG = {
    "candidate": {
        "provider_name": "mimo",
        "model": "mimo-v2.5",
        "base_url": "https://api.xiaomimimo.com/v1",
        "api_key_env": "MIMO_API_KEY",
    },
    "inspect_model": "openai/mimo-v2.5",
}


class BenchmarkConfigTests(unittest.TestCase):
    def test_load_reads_candidate_and_inspect_settings(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(_CONFIG), encoding="utf-8")
            config = BenchmarkConfig.load(path)
        self.assertEqual(config.candidate.provider_name, "mimo")
        self.assertEqual(config.candidate.model, "mimo-v2.5")
        self.assertEqual(config.candidate.base_url, "https://api.xiaomimimo.com/v1")
        self.assertEqual(config.candidate.api_key_env, "MIMO_API_KEY")
        self.assertEqual(config.inspect_model, "openai/mimo-v2.5")

    def test_load_uses_repo_config_by_default(self) -> None:
        config = BenchmarkConfig.load()
        self.assertTrue(config.candidate.model)
        self.assertTrue(config.candidate.base_url.startswith("https://"))
        self.assertTrue(config.candidate.api_key_env)
        self.assertTrue(config.inspect_model)

    def test_load_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            BenchmarkConfig.load(Path("/nonexistent/config.json"))


class DefaultProviderTests(unittest.TestCase):
    def test_default_provider_is_built_from_config(self) -> None:
        from benchmark_agent.workflow import _default_provider

        with patch.dict(os.environ, {"MIMO_API_KEY": "test-key"}):
            provider = _default_provider(load_scenario(_SCENARIO))
        # The native default provider must carry the config file wiring.
        self.assertEqual(provider.__self__.name, "mimo")
        self.assertEqual(provider.__self__._model, "mimo-v2.5")
        self.assertEqual(provider.__self__._base, "https://api.xiaomimimo.com/v1")

    def test_default_provider_requires_key(self) -> None:
        from benchmark_agent.workflow import _default_provider

        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            _default_provider(load_scenario(_SCENARIO))


if __name__ == "__main__":
    unittest.main()
