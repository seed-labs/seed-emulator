"""Inspect AI harness for candidate agents constrained by the Benchmark Adapter."""

import json
import os
from pathlib import Path
from typing import Any

from benchmark_agent.evaluation import post_action
from benchmark_agent.scenario import Scenario


def inspect_available() -> bool:
    """Return whether the optional Inspect AI dependency can be imported."""

    try:
        import inspect_ai  # noqa: F401
    except ImportError:
        return False
    return True


def run_inspect_candidate_evaluation(
    *,
    adapter_url: str,
    agent_view: dict[str, Any],
    log_dir: Path,
    scenario: Scenario,
    model: Any,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str | None = None,
    max_calls: int = 6,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one Inspect task whose only tools are Adapter-backed actions.

    Inspect owns model/tool orchestration and its replayable transcript. Tools
    are registered from the scenario action contract; the closures deliberately
    know only the Adapter URL and cannot address Docker or the Tool Service.
    """

    try:
        from inspect_ai import Task
        from inspect_ai import eval as inspect_eval
        from inspect_ai.dataset import Sample
        from inspect_ai.model import ChatMessageSystem, ChatMessageUser, get_model
        from inspect_ai.solver import generate, use_tools
        from inspect_ai.tool import tool
    except ImportError as error:
        raise RuntimeError(
            "Inspect AI is not installed; install benchmarks/requirements-inspect.txt"
        ) from error

    trace: list[dict[str, Any]] = []
    finished = False

    def invoke(action: str, reasoning: str) -> str:
        nonlocal finished
        if finished:
            # Completion was already declared; every later call is acknowledged
            # without consuming budget or becoming a rejection.
            return json.dumps({"finished": True}, ensure_ascii=False, sort_keys=True)
        if action == scenario.finish_action:
            # The terminal action is always allowed, even at the budget edge.
            finished = True
            observation: dict[str, Any] = {"finished": True}
        elif len(trace) >= max_calls:
            observation = {
                "rejected": True,
                "code": "candidate_call_budget_exhausted",
            }
        else:
            observation = post_action(
                adapter_url, {"action": action, "reasoning": reasoning}
            )
        trace.append(
            {
                "turn": len(trace),
                "action": action,
                "reasoning": reasoning,
                "observation": observation,
            }
        )
        return json.dumps(observation, ensure_ascii=False, sort_keys=True)

    def _make_tool(name: str, description: str) -> Any:
        """Register one scenario action as an Inspect tool."""

        def candidate_action() -> Any:
            """Execute one candidate action through the capability-scoped Adapter."""

            async def execute(reasoning: str) -> str:
                """Docstring is set dynamically below."""
                return invoke(name, reasoning)

            # Inspect reads the inner tool's docstring: the first line is the
            # tool description shown to the model, the Args section documents
            # the reasoning parameter.
            execute.__doc__ = (
                f"{description}\n\n"
                "Args:\n"
                "    reasoning: Concise reason for this candidate action.\n"
            )
            return execute

        candidate_action.__name__ = name
        return tool(name=name)(candidate_action)

    scenario_tools = [
        _make_tool(name, spec.description)() for name, spec in scenario.actions.items()
    ]

    key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
    selected_model = get_model(model, base_url=base_url, api_key=key)
    task = Task(
        dataset=[
            Sample(
                id=scenario.naming.sample_id,
                input=[
                    ChatMessageSystem(content=scenario.prompts.inspect_system),
                    ChatMessageUser(
                        content=json.dumps(
                            agent_view, ensure_ascii=False, sort_keys=True
                        )
                    ),
                ],
                metadata={"agent_view": agent_view},
            )
        ],
        solver=[
            use_tools(*scenario_tools),
            generate(tool_calls="loop", temperature=0),
        ],
        model=selected_model,
        name=scenario.naming.inspect_task_name,
        version=1,
        turn_limit=max_calls + 2,
        metadata={
            "security_boundary": "benchmark-adapter-only",
            "scenario": scenario.id,
        },
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    logs = inspect_eval(
        task,
        model=selected_model,
        log_dir=str(log_dir),
        log_format="json",
        display="none",
        fail_on_error=True,
    )
    if not logs or logs[0].status != "success":
        status = logs[0].status if logs else "missing"
        detail = logs[0].error.message if logs and logs[0].error else "unknown"
        raise RuntimeError(
            f"Inspect evaluation did not complete successfully: {status}: {detail}"
        )
    usage = logs[0].stats.model_usage if logs[0].stats else {}
    metadata = {
        "name": "inspect-ai",
        "model": model if isinstance(model, str) else selected_model.name,
        "usage": {name: value.model_dump(mode="json") for name, value in usage.items()},
        "inspect_log": logs[0].location,
        "inspect_status": logs[0].status,
    }
    return trace, metadata
