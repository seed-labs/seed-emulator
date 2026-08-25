"""CLI for safe and explicitly isolated unsafe natural-language generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generator.nl.catalog import build_capability_catalog
from generator.nl.provider import (
    DeterministicLLMProvider, MiMoProvider, OpenAICompatibleProvider,
)
from generator.mcp.profile import builtin_profile
from generator.mcp.provider import MCPProvider
from generator.nl.session import NaturalLanguageExecutor, NaturalLanguagePlanner
from generator.nl.scene_provider import DeterministicSceneProvider
from generator.nl.scene_session import (
    NaturalLanguageSceneDeliverer, NaturalLanguageScenePlanner,
)
from generator.nl.unsafe_provider import DeterministicUnsafeProvider
from generator.nl.unsafe_session import (
    UnsafeNaturalLanguageExecutor, UnsafeNaturalLanguagePlanner,
)


BENCHMARKS_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_ROOT = BENCHMARKS_DIR / "reports/nl_sessions"


PROVIDER_CHOICES = ("deterministic", "openai-compatible", "mimo", "mcp")
MCP_PROFILE_CHOICES = ("mimo", "openai-compatible")


def _add_mcp_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mcp-profile", choices=MCP_PROFILE_CHOICES, default="mimo",
        help="trusted MCP Gateway profile used when --provider=mcp",
    )
    parser.add_argument(
        "--mcp-fallback-profile", choices=MCP_PROFILE_CHOICES,
        help="fallback only for MCP transport failures; never schema/policy rejection",
    )


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
    plan.add_argument(
        "--provider", choices=PROVIDER_CHOICES,
        default="deterministic",
    )
    plan.add_argument("--model")
    plan.add_argument("--base-url")
    plan.add_argument("--api-key-env")
    plan.add_argument("--timeout", type=int, default=60)
    plan.add_argument("--session-id")
    plan.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    _add_mcp_arguments(plan)
    generate = commands.add_parser("nl-generate", help="execute an approved intent once")
    generate.add_argument("--intent", type=Path, required=True)
    generate.add_argument("--approval-token", required=True)
    generate.add_argument("--release-version", default="1.0.0")
    scene_plan = commands.add_parser(
        "nl-scene-plan",
        help="translate an arbitrary scene into a safe declarative topology plan",
    )
    scene_plan.add_argument("--text", required=True)
    scene_plan.add_argument("--seed", default="natural-language-scene-v1")
    scene_plan.add_argument(
        "--provider", choices=PROVIDER_CHOICES,
        default="deterministic",
    )
    scene_plan.add_argument("--model")
    scene_plan.add_argument("--base-url")
    scene_plan.add_argument("--api-key-env")
    scene_plan.add_argument("--timeout", type=int, default=120)
    scene_plan.add_argument("--session-id")
    scene_plan.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    _add_mcp_arguments(scene_plan)
    scene_generate = commands.add_parser(
        "nl-scene-generate",
        help="register, compile, and deliver an approved scene capability manifest",
    )
    scene_generate.add_argument("--scene", type=Path, required=True)
    scene_generate.add_argument("--approval-token", required=True)
    unsafe_plan = commands.add_parser(
        "nl-unsafe-plan",
        help="generate a container-scoped arbitrary-code plan without Docker changes",
    )
    unsafe_plan.add_argument("--text", required=True)
    unsafe_plan.add_argument("--seed", default="unsafe-natural-language-v1")
    unsafe_plan.add_argument(
        "--provider", choices=PROVIDER_CHOICES,
        default="deterministic",
    )
    unsafe_plan.add_argument("--model")
    unsafe_plan.add_argument("--base-url")
    unsafe_plan.add_argument("--api-key-env")
    unsafe_plan.add_argument("--timeout", type=int, default=120)
    unsafe_plan.add_argument("--session-id")
    unsafe_plan.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    _add_mcp_arguments(unsafe_plan)
    unsafe_plan.add_argument(
        "--unsafe-base-image", default="debian:bookworm-slim",
        help="base image used only by the deterministic unsafe fixture provider",
    )
    unsafe_generate = commands.add_parser(
        "nl-unsafe-generate",
        help="execute an approved unsafe plan in its isolated Compose project",
    )
    unsafe_generate.add_argument("--plan", type=Path, required=True)
    unsafe_generate.add_argument("--approval-token", required=True)
    unsafe_generate.add_argument(
        "--acknowledge-arbitrary-code", action="store_true", required=True,
    )
    commands.add_parser("catalog", help="print the current capability snapshot")
    return parser


def _provider(args, *, unsafe: bool = False, scene: bool = False):
    if args.provider == "deterministic":
        if unsafe:
            return DeterministicUnsafeProvider(
                args.model or "deterministic-unsafe-v1",
                args.unsafe_base_image,
            )
        if scene:
            return DeterministicSceneProvider(
                args.model or "deterministic-scene-v2"
            )
        return DeterministicLLMProvider(args.model or "deterministic-nl-v1")
    if args.provider == "mcp":
        primary = builtin_profile(
            args.mcp_profile,
            model_id=args.model,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            timeout_seconds=args.timeout,
        )
        fallbacks = ()
        if args.mcp_fallback_profile:
            if args.mcp_fallback_profile == args.mcp_profile:
                raise ValueError("MCP primary and fallback profiles must differ")
            fallbacks = (builtin_profile(
                args.mcp_fallback_profile,
                timeout_seconds=args.timeout,
            ),)
        return MCPProvider(
            primary,
            working_directory=BENCHMARKS_DIR,
            fallbacks=fallbacks,
        )
    if args.provider == "mimo":
        return MiMoProvider(
            model_id=args.model or "mimo-v2.5-pro",
            base_url=args.base_url or "https://api.xiaomimimo.com/v1",
            api_key_env=args.api_key_env or "MIMO_API_KEY",
            timeout_seconds=args.timeout,
        )
    return OpenAICompatibleProvider(
        model_id=args.model or "gpt-4.1-mini",
        base_url=args.base_url or "https://api.openai.com/v1",
        api_key_env=args.api_key_env or "BENCHMARK_LLM_API_KEY",
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
            return {
                "ready": 0,
                "needs_clarification": 2,
                "extension_required": 2,
                "blocked": 3,
                "provider_error": 4,
            }[result["status"]]
        if args.command == "nl-scene-plan":
            root = _under_session_root(args.session_root)
            result = NaturalLanguageScenePlanner(BENCHMARKS_DIR, root).plan(
                args.text,
                provider=_provider(args, scene=True),
                seed=args.seed,
                session_id=args.session_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return {
                "ready": 0,
                "needs_clarification": 2,
                "extension_required": 2,
                "blocked": 3,
                "provider_error": 4,
                "schema_rejected": 6,
                "policy_rejected": 6,
            }[result["status"]]
        if args.command == "nl-scene-generate":
            scene = _under_session_root(args.scene)
            result = NaturalLanguageSceneDeliverer(
                BENCHMARKS_DIR, DEFAULT_SESSION_ROOT
            ).deliver(scene, args.approval_token)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result["status"] == "delivered" else 5
        if args.command == "nl-unsafe-plan":
            root = _under_session_root(args.session_root)
            result = UnsafeNaturalLanguagePlanner(BENCHMARKS_DIR, root).plan(
                args.text,
                provider=_provider(args, unsafe=True),
                seed=args.seed,
                session_id=args.session_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return {
                "ready": 0,
                "blocked": 3,
                "provider_error": 4,
                "policy_rejected": 6,
                "schema_rejected": 6,
            }[result["status"]]
        if args.command == "nl-unsafe-generate":
            plan = _under_session_root(args.plan)
            result = UnsafeNaturalLanguageExecutor(
                BENCHMARKS_DIR, DEFAULT_SESSION_ROOT
            ).execute(
                plan,
                args.approval_token,
                acknowledge_arbitrary_code=args.acknowledge_arbitrary_code,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result["status"] == "complete" else 5
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
