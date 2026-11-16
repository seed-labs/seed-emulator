#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.compiler import Docker, Platform
from seedemu.services import DomainNameCachingService
from seedemu.services.DomainNameCachingService import DomainNameCachingServer
from seedemu.layers import Base
from examples.internet.B00_mini_internet import mini_internet
from examples.internet.B01_dns_component import dns_component
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B02 mini Internet with DNS example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator() -> Emulator:
    emuA = Emulator()
    emuB = Emulator()

    # Run the pre-built components
    base_component = SCRIPT_DIR / "base_internet.bin"
    dns_component_file = SCRIPT_DIR / "dns_component.bin"
    mini_internet.run(dumpfile=str(base_component))
    dns_component.run(dumpfile=str(dns_component_file))
    
    # Load and merge the pre-built components 
    emuA.load(str(base_component))
    emuB.load(str(dns_component_file))
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    
    
    #####################################################################################
    # Bind the virtual nodes in the DNS infrastructure layer to physical nodes.
    # Action.FIRST will look for the first acceptable node that satisfies the filter rule.
    # There are several other filters types that are not shown in this example.
    
    emu.addBinding(Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST))
    emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('a-com-server', filter=Filter(asn=151), action=Action.FIRST))
    emu.addBinding(Binding('b-com-server', filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding('a-net-server', filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding('a-edu-server', filter=Filter(asn=153), action=Action.FIRST))
    emu.addBinding(Binding('ns-twitter-com', filter=Filter(asn=161), action=Action.FIRST))
    emu.addBinding(Binding('ns-google-com', filter=Filter(asn=162), action=Action.FIRST))
    emu.addBinding(Binding('ns-example-net', filter=Filter(asn=163), action=Action.FIRST))
    emu.addBinding(Binding('ns-syr-edu', filter=Filter(asn=164), action=Action.FIRST))
    
    #####################################################################################
    # Create two local DNS servers (virtual nodes).
    ldns = DomainNameCachingService()
    global_dns_1:DomainNameCachingServer = ldns.install('global-dns-1')
    global_dns_2:DomainNameCachingServer = ldns.install('global-dns-2')
    
    # Customize the display name (for visualization purpose)
    emu.getVirtualNode('global-dns-1').setDisplayName('Global DNS-1')
    emu.getVirtualNode('global-dns-2').setDisplayName('Global DNS-2')
    
    # Create two new host in AS-152 and AS-153, use them to host the local DNS server.
    # We can also host it on an existing node.
    base: Base = emu.getLayer('Base')
    as152 = base.getAutonomousSystem(152)
    as152.createHost('local-dns-1').joinNetwork('net0', address = '10.152.0.53')
    as153 = base.getAutonomousSystem(153)
    as153.createHost('local-dns-2').joinNetwork('net0', address = '10.153.0.53')
    
    # Bind the Local DNS virtual nodes to physical nodes
    emu.addBinding(Binding('global-dns-1', filter = Filter(asn=152, nodeName="local-dns-1")))
    emu.addBinding(Binding('global-dns-2', filter = Filter(asn=153, nodeName="local-dns-2")))
    
    # Add 10.152.0.53 as the local DNS server for AS-160 and AS-170
    # Add 10.153.0.53 as the local DNS server for all the other nodes
    global_dns_1.setNameServerOnNodesByAsns(asns=[160, 170])
    global_dns_2.setNameServerOnAllNodes()
    
    # Add the ldns layer
    emu.addLayer(ldns)
    return emu


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
):
    emu = build_emulator()
    if dumpfile is not None:
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
        return

    # Rendering compilation
    if render:
        emu.render()
    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, str(output_dir), override=override)


def main() -> int:
    args = parse_args()
    run(
        dumpfile=args.dumpfile,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())