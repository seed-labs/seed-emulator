#!/usr/bin/env python3
"""Build a benchmark-local mini Internet image with iptables on the target."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "examples/internet/B00_mini_internet/mini_internet.py"
OUTPUT = REPO_ROOT / "benchmarks/generated/firewall_mini_internet/output"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

spec = spec_from_file_location("seedemu_b00_mini_internet", SOURCE)
source_module = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(source_module)

from seedemu.compiler import Docker, Platform


def main() -> None:
    emulator = source_module.build_emulator()
    base = emulator.getLayer("Base")
    base.getAutonomousSystem(151).getHost("host_0").addSoftware("iptables")
    emulator.render()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    emulator.compile(
        Docker(platform=Platform.AMD64),
        str(OUTPUT),
        override=True,
    )


if __name__ == "__main__":
    main()
