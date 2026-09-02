"""Command-line entry point for the benchmark agent."""

import argparse
import json
import os
from pathlib import Path

from benchmark_agent.config import BenchmarkConfig
from benchmark_agent.nl import (
    make_mimo_provider,
    plan_natural_language,
    plan_runtime_natural_language,
)
from benchmark_agent.scenario import load_scenario
from benchmark_agent.workflow import run_runtime_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SEED runtime benchmark authoring agent"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def configure_run(command: str, help_text: str):
        run = subparsers.add_parser(command, help=help_text)
        run.add_argument("--api-url", default="http://127.0.0.1:8000")
        run.add_argument("--output-root", type=Path, default=Path("benchmarks/runs"))
        run.add_argument(
            "--scenario",
            type=Path,
            required=True,
            help="Persistent Python-discovered or runtime-discovered scenario JSON",
        )
        run.add_argument(
            "--project", default=None, help="Compose project (default: scenario value)"
        )
        run.add_argument("--reuse-running", action="store_true")
        run.add_argument("--keep-topology", action="store_true")
        run.add_argument(
            "--candidate-runtime", choices=["native", "inspect"], default="native"
        )
        run.add_argument("--inspect-model", default=None)
        run.add_argument("--inspect-base-url", default=None)
        return run

    configure_run("run", "Run one scenario-driven runtime benchmark")
    plan = subparsers.add_parser(
        "nl-plan",
        help="Translate natural language into a validated scenario (plan-only)",
    )
    plan.add_argument("--text", required=True)
    plan.add_argument(
        "--topology", type=Path, required=True, help="SEED Python topology script"
    )
    plan.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Tool Service used for Python discovery; no direct Docker calls",
    )
    plan.add_argument("--provider", default="mimo")
    plan.add_argument("--output-root", type=Path, default=Path("benchmarks/nl_plans"))
    plan.add_argument("--seed-root", type=Path, default=Path.cwd())

    runtime_plan = subparsers.add_parser(
        "nl-runtime-plan",
        help="Discover one running Compose project through the Tool Service and plan from NL (plan-only)",
    )
    runtime_plan.add_argument("--text", required=True)
    runtime_plan.add_argument("--api-url", default="http://127.0.0.1:8000")
    runtime_plan.add_argument(
        "--project",
        required=True,
        help="Compose project to discover (com.docker.compose.project label)",
    )
    runtime_plan.add_argument("--provider", default="mimo")
    runtime_plan.add_argument(
        "--output-root", type=Path, default=Path("benchmarks/nl_plans")
    )

    projects = subparsers.add_parser(
        "runtime-projects",
        help="List Compose projects discoverable through the Tool Service",
    )
    projects.add_argument("--api-url", default="http://127.0.0.1:8000")

    args = parser.parse_args()
    if args.command in ("nl-plan", "nl-runtime-plan"):
        config = BenchmarkConfig.load().candidate
        if args.provider != config.provider_name:
            parser.error(
                f"configured provider is {config.provider_name!r}, not {args.provider!r}"
            )
        key = os.environ.get(config.api_key_env)
        if not key:
            parser.error(f"{config.api_key_env} is required")
        provider = make_mimo_provider(api_key=key)
        if args.command == "nl-plan":
            output = plan_natural_language(
                text=args.text,
                topology_path=args.topology,
                output_root=args.output_root,
                seed_root=args.seed_root,
                provider=provider,
                api_url=args.api_url,
            )
        else:
            output = plan_runtime_natural_language(
                text=args.text,
                project=args.project,
                api_url=args.api_url,
                output_root=args.output_root,
                provider=provider,
            )
        print(
            json.dumps(
                {
                    "status": "planned",
                    "plan_only": True,
                    "docker_changed": False,
                    "output": str(output),
                    "scenario": str(output / "scenario.json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "runtime-projects":
        from benchmark_agent.api import invoke_tool

        receipt = invoke_tool(
            args.api_url, "benchmark.runtime.projects", {}, timeout=300
        )
        print(json.dumps(receipt["result"], ensure_ascii=False, indent=2))
        return 0

    output = run_runtime_benchmark(
        api_url=args.api_url,
        output_root=args.output_root,
        project=args.project,
        materialize=not args.reuse_running,
        cleanup_topology=not args.keep_topology,
        candidate_runtime=args.candidate_runtime,
        inspect_model=args.inspect_model,
        inspect_base_url=args.inspect_base_url,
        scenario=load_scenario(args.scenario),
    )
    print(json.dumps({"status": "completed", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
