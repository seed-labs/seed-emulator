#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional, Sequence

if __package__:
    from .registry import create_runner
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from registry import create_runner


COMMANDS = ["clean", "compile", "build", "up", "readiness", "probe", "test", "down", "all"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a standardized SEED Emulator test manifest.")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("manifest", type=Path, help="Path to a test manifest YAML file.")
    parser.add_argument("--artifact-dir", type=Path, help="Optional directory for command logs and summaries.")
    parser.add_argument(
        "--runner",
        choices=["generic", "internet", "satellite", "blockchain"],
        help="Runner type. Defaults to the manifest's runner field, then generic.",
    )
    args = parser.parse_args(argv)

    runner = create_runner(args.manifest, artifact_dir=args.artifact_dir, runner=args.runner)
    return getattr(runner, args.command)()


if __name__ == "__main__":
    raise SystemExit(main())
