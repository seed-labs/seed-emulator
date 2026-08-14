"""CLI for safe natural-language planning and explicitly approved generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generator.nl.catalog import build_capability_catalog
from generator.nl.provider import DeterministicLLMProvider, OpenAICompatibleProvider
from generator.nl.session import NaturalLanguageExecutor, NaturalLanguagePlanner


BENCHMARKS_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_ROOT = BENCHMARKS_DIR / "reports/nl_sessions"


def _under_session_root(value: Path) -> Path:
    path = value.resolve()
    root = DEFAULT_SESSION_ROOT.resolve()
    if path != root and root not in path.parents:
        raise ValueError("NL paths must stay under benchmarks/reports/nl_sessions")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Natural-language Benchmark Generator v1")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("nl-plan", help="parse, clarify and compile plan-only evidence")
    plan.add_argument("--text", required=True)
    plan.add_argument("--seed", default="natural-language-v1")
    plan.add_argument("--provider", choices=("deterministic", "openai-compatible"), default="deterministic")
    plan.add_argument("--model", default="deterministic-nl-v1")
    plan.add_argument("--base-url", default="https://api.openai.com/v1")
    plan.add_argument("--api-key-env", default="BENCHMARK_LLM_API_KEY")
    plan.add_argument("--timeout", type=int, default=60)
    plan.add_argument("--session-id")
    plan.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    generate = commands.add_parser("nl-generate", help="execute an approved intent once")
    generate.add_argument("--intent", type=Path, required=True)
    generate.add_argument("--approval-token", required=True)
    generate.add_argument("--release-version", default="1.0.0")
    commands.add_parser("catalog", help="print the current capability snapshot")
    return parser


def _provider(args):
    if args.provider == "deterministic":
        return DeterministicLLMProvider(args.model)
    return OpenAICompatibleProvider(
        model_id=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        timeout_seconds=args.timeout,
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "catalog":
            print(json.dumps(build_capability_catalog(BENCHMARKS_DIR).to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "nl-plan":
            root = _under_session_root(args.session_root)
            result = NaturalLanguagePlanner(BENCHMARKS_DIR, root).plan(
                args.text,
                provider=_provider(args),
                seed=args.seed,
                session_id=args.session_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return {"ready": 0, "needs_clarification": 2, "extension_required": 2, "blocked": 3}[result["status"]]
        intent = _under_session_root(args.intent)
        result = NaturalLanguageExecutor(BENCHMARKS_DIR, DEFAULT_SESSION_ROOT).execute(
            intent, args.approval_token, release_version=args.release_version
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
