#!/usr/bin/env python3
"""Change Docker CPU and memory limits at runtime and restore their original values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def docker(command: list[str]) -> str:
    result = subprocess.run(["docker", *command], capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"docker {' '.join(command)} failed: {detail}")
    return result.stdout


def inspect_limits(container: str) -> dict[str, int]:
    host_config = json.loads(docker(["inspect", "--format", "{{json .HostConfig}}", container]))
    return {
        "nano_cpus": int(host_config.get("NanoCpus", 0)),
        "memory": int(host_config.get("Memory", 0)),
        "memory_swap": int(host_config.get("MemorySwap", 0)),
    }


def default_state_path(container: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", container)
    return Path(f".traffic-visualizer-capacity-{safe_name}.json")


def format_limits(container: str, limits: dict[str, int]) -> dict[str, object]:
    return {
        "container": container,
        "cpus": round(limits["nano_cpus"] / 1_000_000_000, 3) if limits["nano_cpus"] else "unlimited",
        "memory_bytes": limits["memory"] or "unlimited",
        "memory_swap_bytes": limits["memory_swap"] if limits["memory_swap"] else "unlimited",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Control a running Docker container's capacity.")
    parser.add_argument("command", choices=["show", "set", "restore"])
    parser.add_argument("--container", required=True)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--cpus", type=float, help="CPU quota, such as 0.5")
    parser.add_argument("--memory", help="Docker memory value, such as 256m")
    parser.add_argument("--memory-swap", help="Docker memory+swap value, such as 256m or -1")
    args = parser.parse_args()
    state_path = args.state_file or default_state_path(args.container)

    try:
        if args.command == "show":
            print(json.dumps(format_limits(args.container, inspect_limits(args.container)), indent=2))
            return 0

        if args.command == "set":
            if args.cpus is None and args.memory is None and args.memory_swap is None:
                parser.error("set requires --cpus, --memory, or --memory-swap")
            if args.cpus is not None and args.cpus <= 0:
                parser.error("--cpus must be greater than zero")
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if state.get("container") != args.container:
                    raise RuntimeError("saved state belongs to a different container")
            else:
                state = {
                    "container": args.container,
                    "limits": inspect_limits(args.container),
                    "changed": [],
                }

            changed = set(state.get("changed", []))
            if args.cpus is not None:
                changed.add("cpus")
            if args.memory is not None or args.memory_swap is not None:
                changed.add("memory")
            state["changed"] = sorted(changed)
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            update = ["update"]
            if args.cpus is not None:
                update.extend(["--cpus", str(args.cpus)])
            if args.memory is not None:
                update.extend(["--memory", args.memory])
            if args.memory_swap is not None:
                update.extend(["--memory-swap", args.memory_swap])
            update.append(args.container)
            docker(update)
            print(json.dumps(format_limits(args.container, inspect_limits(args.container)), indent=2))
            print(f"original limits saved in {state_path}")
            return 0

        if not state_path.exists():
            raise RuntimeError(f"restore state does not exist: {state_path}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("container") != args.container:
            raise RuntimeError("restore state belongs to a different container")
        limits = state["limits"]
        changed = set(state.get("changed", ["cpus", "memory"]))
        update = ["update"]
        if "cpus" in changed:
            cpus = limits["nano_cpus"] / 1_000_000_000 if limits["nano_cpus"] else 0
            update.extend(["--cpus", str(cpus)])
        if "memory" in changed:
            memory = f"{limits['memory']}b" if limits["memory"] else "0"
            memory_swap = (
                f"{limits['memory_swap']}b"
                if limits["memory_swap"] > 0
                else str(limits["memory_swap"])
            )
            update.extend(["--memory", memory, "--memory-swap", memory_swap])
        update.append(args.container)
        docker(update)
        print(json.dumps(format_limits(args.container, inspect_limits(args.container)), indent=2))
        print(f"restored original limits from {state_path}")
    except (RuntimeError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"container control error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
