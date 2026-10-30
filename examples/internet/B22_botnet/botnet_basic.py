#!/usr/bin/env python3
# encoding: utf-8
#
# Purpose: build the B22 botnet example. Inputs are standard TestRunner CLI
# arguments. Outputs are Docker compiler files under --output.

from __future__ import annotations

import argparse
import random
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.internet.B00_mini_internet import mini_internet
from seedemu.compiler import Docker, Platform
from seedemu.core import Action, Binding, Emulator, Filter
from seedemu.services import BotnetClientService, BotnetService
from seedemu.containerBundle import InternetMap


BOT_CONTROLLER_IP = "10.150.0.66"
BOT_CANDIDATE_ASNS = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B22 botnet example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument("--bot-count", type=int, default=6)
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def select_bot_asns(bot_count: int, seed: int) -> list[int]:
    if bot_count > len(BOT_CANDIDATE_ASNS):
        raise ValueError("bot_count cannot exceed {}".format(len(BOT_CANDIDATE_ASNS)))
    rng = random.Random(seed)
    return rng.sample(BOT_CANDIDATE_ASNS, bot_count)


def build_emulator(hosts_per_as: int = 2, bot_count: int = 6, seed: int = 22) -> Emulator:
    base_component = SCRIPT_DIR / "base_internet.bin"
    mini_internet.run(dumpfile=str(base_component), hosts_per_as=hosts_per_as)

    emu = Emulator()
    emu.load(str(base_component))

    bot = BotnetService()
    bot_client = BotnetClientService()

    bot.install("bot-controller")
    emu.getVirtualNode("bot-controller").setDisplayName("Bot-Controller")
    ddos_script = (SCRIPT_DIR / "ddos.py").read_text(encoding="utf-8")
    emu.getVirtualNode("bot-controller").setFile(content=ddos_script, path="/tmp/ddos.py")

    for counter, asn in enumerate(select_bot_asns(bot_count, seed)):
        vnode = "bot-node-{:03d}".format(counter)
        bot_client.install(vnode).setServer("bot-controller")
        emu.getVirtualNode(vnode).setDisplayName("Bot-{:03d}".format(counter))
        emu.addBinding(
            Binding(
                vnode,
                filter=Filter(asn=asn, nodeName=vnode),
                action=Action.NEW,
            )
        )

    emu.addBinding(
        Binding(
            "bot-controller",
            filter=Filter(ip=BOT_CONTROLLER_IP, nodeName="bot-controller"),
            action=Action.NEW,
        )
    )

    emu.addLayer(bot)
    emu.addLayer(bot_client)
    return emu


def run(
    dumpfile=None,
    hosts_per_as: int = 2,
    bot_count: int = 6,
    seed: int = 22,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
):
    emu = build_emulator(hosts_per_as=hosts_per_as, bot_count=bot_count, seed=seed)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    docker = Docker(platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, output or str(SCRIPT_DIR / "output"), override=override)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        bot_count=args.bot_count,
        seed=args.seed,
        output=str(output_dir),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())