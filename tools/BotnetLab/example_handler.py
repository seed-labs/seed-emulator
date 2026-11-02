#!/usr/bin/env python3
"""Harmless reference handler demonstrating the BotnetLab task contract."""

from __future__ import annotations

import json
import sys
import time


def main() -> int:
    task = json.load(sys.stdin)
    parameters = task.get("parameters", {})
    message = str(parameters.get("message", "hello from BotnetLab"))[:256]
    try:
        delay = float(parameters.get("delay_seconds", 0))
    except (TypeError, ValueError):
        print("delay_seconds must be a number", file=sys.stderr, flush=True)
        return 2
    if not 0 <= delay <= 5:
        print("delay_seconds must be between 0 and 5", file=sys.stderr, flush=True)
        return 2
    time.sleep(delay)
    print(
        json.dumps(
            {
                "message": message,
                "command_id": task.get("command_id"),
                "task_type": task.get("task_type"),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
