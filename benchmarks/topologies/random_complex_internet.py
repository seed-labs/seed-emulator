#!/usr/bin/env python3
"""Build a reproducible randomized large Internet for AI diagnosis benchmarks."""
from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers

DEFAULT_SEED = 20260724
IX_IDS = list(range(200, 208))
TRANSIT_ASNS = list(range(20, 26))
STUB_ASNS = list(range(100, 118))

def build_emulator(seed: int, hosts_per_stub: int = 3):
    rng = random.Random(seed)
    emu, base, ebgp = Emulator(), Base(), Ebgp()
    for ix_id in IX_IDS:
        base.createInternetExchange(ix_id).getPeeringLan().setDisplayName(f"RND-IX-{ix_id}")
    transit_ixs = {}
    for offset, asn in enumerate(TRANSIT_ASNS):
        anchors = {IX_IDS[offset], IX_IDS[(offset + 3) % len(IX_IDS)]}
        joined = sorted(anchors | set(rng.sample([x for x in IX_IDS if x not in anchors], 2)))
        edges = [(joined[i], joined[i + 1]) for i in range(3)] + [(joined[0], joined[-1])]
        Makers.makeTransitAs(base, asn, joined, edges)
        transit_ixs[asn] = joined
    providers = {ix: [asn for asn, ixs in transit_ixs.items() if ix in ixs] for ix in IX_IDS}
    for ix, asns in providers.items():
        if len(asns) >= 2: ebgp.addRsPeers(ix, asns)
    stubs = []
    usable_ixs = [ix for ix in IX_IDS if providers[ix]]
    for asn in STUB_ASNS:
        ix = rng.choice(usable_ixs)
        provider = rng.choice(providers[ix])
        Makers.makeStubAsWithHosts(emu, base, asn, ix, hosts_per_stub)
        ebgp.addPrivatePeerings(ix, [provider], [asn], PeerRelationship.Provider)
        stubs.append({"asn": asn, "ix": ix, "provider_asn": provider})
    for layer in (base, Routing(), ebgp, Ibgp(), Ospf()): emu.addLayer(layer)
    source, destination = rng.sample(stubs, 2)
    base.getAutonomousSystem(source["asn"]).getRouter("router0").addSoftware("iptables")
    manifest = {
        "schema_version": 1, "seed": seed, "hosts_per_stub": hosts_per_stub,
        "ix_ids": IX_IDS,
        "transit_ases": [{"asn": a, "ix_ids": transit_ixs[a]} for a in TRANSIT_ASNS],
        "stub_ases": stubs,
        "fault": {"source_asn": source["asn"], "destination_asn": destination["asn"],
                  "category": "randomized_transit_acl_shadowing"},
        "minimum_expected_containers": 104,
    }
    return emu, manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--hosts-per-stub", type=int, default=3)
    parser.add_argument("--platform", choices=["amd", "arm"], default="amd")
    parser.add_argument("--output", default=str(REPO_ROOT / "benchmarks/generated/random_complex/output"))
    args = parser.parse_args()
    if args.hosts_per_stub < 2: raise SystemExit("--hosts-per-stub must be at least 2")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    emu, manifest = build_emulator(args.seed, args.hosts_per_stub)
    emu.render()
    platform = Platform.AMD64 if args.platform == "amd" else Platform.ARM64
    emu.compile(Docker(platform=platform), str(output), override=True)
    (output / "benchmark_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"seed={args.seed} minimum_containers={manifest['minimum_expected_containers']} output={output}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
