#!/usr/bin/env python3
# encoding: utf-8

import os
from pathlib import Path
import random
import sys

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Hook, ScopedRegistry
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers


# Fraction of eligible ASes that should be marked as adopting ASes.
ADOPTION_RATE = 0.4

# Seed used when choosing adopting ASes.
RANDOM_SEED = 7

# AS that will later host the repository component.
REPO_AS = 154

# Central AS reserved for future suppressor-specific routing behavior.
SUPPRESSOR_AS = 3

# Minimal repository service settings for the demo repository host.
REPO_SERVICE_PORT = 18080
REPO_SERVICE_PATH = "/root/repo_server.py"
AGENT_SCRIPT_PATH = "/root/agent.py"
ROUTER_HELPER_PORT = 18081
ROUTER_HELPER_PATH = "/root/router_helper.py"


class SuppressorPolicyHook(Hook):
    """SEED-native hook point for future suppressor-specific BGP policy."""

    def __init__(self, suppressor_asn):
        self._suppressor_asn = suppressor_asn

    def getName(self):
        return f"SuppressorPolicyAs{self._suppressor_asn}"

    def getTargetLayer(self):
        return "Ebgp"

    def postrender(self, emulator):
        # This follows the SEED-native pattern used by
        # seedemu/components/BgpAttackerComponent.py: modify router/BIRD state
        # after the Ebgp layer has created the baseline BGP configuration.
        reg = emulator.getRegistry()
        scoped = ScopedRegistry(str(self._suppressor_asn), reg)
        suppressor_routers = scoped.getByType("brdnode")

        for router in suppressor_routers:
            router.setAttribute("rost_role", "suppressor")
            router.setAttribute("rost_policy_hook_ready", True)

            # Keep this draft behavior-neutral. The hook intentionally does not
            # change routing yet, but it records the precise place where future
            # work should inject BIRD filters, tables, or protocol changes.
            router.appendFile(
                "/etc/bird/bird.conf",
                "\n# RoST suppressor hook placeholder\n"
                "# Future work should add suppressor-specific BGP policy here,\n"
                "# for example export/import filters or route-processing logic\n"
                "# on AS{} border routers.\n".format(self._suppressor_asn),
            )


def _ensure_component_network(as_obj):
    """Return an existing local network for RoST component hosts.

    Phase 1 must be topology-neutral, so this helper only reuses an existing
    AS-local network that is already attached to the anchor router. It must not
    create a new router-facing network or alter router interface membership.
    """

    # Reuse `net0` when present. This matches the normal stub-AS layout used
    # by many SEED examples and avoids placing component hosts directly onto
    # transit inter-router networks.
    if "net0" in as_obj.getNetworks():
        return "net0"

    anchor_router = _get_component_anchor_router(as_obj)
    anchor_pending_nets = {
        netname
        for (netname, _address) in getattr(anchor_router, "_Node__pending_nets", [])
    }

    for netname in as_obj.getNetworks():
        if netname in anchor_pending_nets:
            return netname

    raise AssertionError(
        "RoST component deployment requires an existing AS-local network on the anchor router"
    )


def _deploy_component_host(as_obj, host_name):
    """Create or reuse a host for a RoST software component in an AS."""

    network_name = _ensure_component_network(as_obj)

    if host_name in as_obj.getHosts():
        return as_obj.getHost(host_name)

    return as_obj.createHost(host_name).joinNetwork(network_name)


def _get_component_anchor_router(as_obj):
    """Return the anchor router used for Phase 1 RoST components in an AS."""

    router_names = as_obj.getRouters()
    assert len(router_names) > 0, "RoST component deployment requires at least one router"
    return as_obj.getRouter(router_names[0])


def _load_example_asset(filename):
    """Load a file shipped alongside this example."""

    return Path(__file__).with_name(filename).read_text(encoding="utf-8")


def build_base_topology():
    """Build a small demo Internet topology without assigning RoST roles."""

    emu = Emulator()
    base = Base()
    ebgp = Ebgp()

    # Create a few IXes so the topology has multiple peering points.
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)

    ix100.getPeeringLan().setDisplayName("Metro-100")
    ix101.getPeeringLan().setDisplayName("Metro-101")
    ix102.getPeeringLan().setDisplayName("Metro-102")
    ix103.getPeeringLan().setDisplayName("Metro-103")

    # Central/transit-like ASes. One of these will later be marked as the
    # suppressor AS, so the transit portion of the graph should remain
    # meaningful for routing-policy experiments.
    Makers.makeTransitAs(base, 2, [100, 101, 102], [(100, 101), (101, 102)])
    Makers.makeTransitAs(base, 3, [100, 102, 103], [(100, 102), (102, 103)])
    Makers.makeTransitAs(base, 4, [101, 103], [(101, 103)])
    Makers.makeTransitAs(base, 10, [102, 103], [(102, 103)])

    # Edge/stub-like ASes. Keep one baseline host per AS so later experiments
    # can attach additional RoST-specific hosts without changing the topology.
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 1)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, 1)
    Makers.makeStubAsWithHosts(emu, base, 152, 101, 1)
    Makers.makeStubAsWithHosts(emu, base, 153, 102, 1)
    Makers.makeStubAsWithHosts(emu, base, 154, 103, 1)
    Makers.makeStubAsWithHosts(emu, base, 155, 103, 1)

    # Shared-route-server peerings between the more central ASes.
    ebgp.addRsPeers(100, [2, 3])
    ebgp.addRsPeers(101, [2, 4])
    ebgp.addRsPeers(102, [2, 3, 10])
    ebgp.addRsPeers(103, [3, 4, 10])

    # Provider/customer-style edge connectivity. This keeps the AS graph
    # connected while remaining simple and realistic for a demo topology.
    ebgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [4], [152], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [10], [153], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [3], [154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [10], [155], PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    return {
        "emu": emu,
        "base": base,
        "ebgp": ebgp,
        "transit_asns": [2, 3, 4, 10],
        "edge_asns": [150, 151, 152, 153, 154, 155],
        "all_asns": [2, 3, 4, 10, 150, 151, 152, 153, 154, 155],
    }


def assign_rost_roles(topology):
    """Assign RoST-related roles independently from topology construction."""

    all_asns = set(topology["all_asns"])

    assert REPO_AS in all_asns, "REPO_AS must exist in the topology"
    assert SUPPRESSOR_AS in all_asns, "SUPPRESSOR_AS must exist in the topology"
    assert REPO_AS != SUPPRESSOR_AS, "REPO_AS and SUPPRESSOR_AS must be different"
    assert SUPPRESSOR_AS in set(topology["transit_asns"]), (
        "SUPPRESSOR_AS should be a central/transit-like AS in this demo topology"
    )

    # Adoption is assigned independently of topology construction. For this
    # revision, any non-repository and non-suppressor AS may adopt.
    eligible = sorted(all_asns - {REPO_AS, SUPPRESSOR_AS})

    rng = random.Random(RANDOM_SEED)
    adopting = []
    for asn in eligible:
        if rng.random() < ADOPTION_RATE:
            adopting.append(asn)

    return {
        "repo_as": REPO_AS,
        "suppressor_as": SUPPRESSOR_AS,
        "eligible_adopters": eligible,
        "adopting_ases": sorted(adopting),
        "ordinary_ases": sorted(all_asns - {REPO_AS, SUPPRESSOR_AS} - set(adopting)),
    }


def deploy_rost_components(topology, roles):
    """Deploy minimal RoST component hosts and start the repository service."""

    base = topology["base"]

    # Future RoST code can replace these placeholders with real file injection,
    # startup commands, and service installation.
    for asn in roles["adopting_ases"]:
        as_obj = base.getAutonomousSystem(asn)
        agent_host = _deploy_component_host(as_obj, "rost-agent")
        agent_host.addSoftware("python3")
        agent_host.setFile(AGENT_SCRIPT_PATH, _load_example_asset("agent.py"))
        agent_host.appendStartCommand(f"chmod +x {AGENT_SCRIPT_PATH}")
        agent_host.appendStartCommand(
            'echo "RoST agent ready. Determine router-helper IP with: ip route show default"'
        )
        agent_host.appendStartCommand(
            'echo "Then run: /root/agent.py --repo-host <repo-ip> --repo-port {} --router-host <default-gateway-ip> --router-port {}"'.format(
                REPO_SERVICE_PORT,
                ROUTER_HELPER_PORT,
            )
        )
        # Keep first-agent execution manual. Later revisions can add explicit
        # startup orchestration once the repository/agent interaction evolves.
        anchor_router = _get_component_anchor_router(as_obj)
        anchor_router.addSoftware("python3")
        anchor_router.setFile(ROUTER_HELPER_PATH, _load_example_asset("router_helper.py"))
        anchor_router.appendStartCommand(f"chmod +x {ROUTER_HELPER_PATH}")
        anchor_router.appendStartCommand(
            "nohup {} --port {} >/var/log/rost_router_helper.log 2>&1".format(
                ROUTER_HELPER_PATH,
                ROUTER_HELPER_PORT,
            ),
            True,
        )

    repo_as = base.getAutonomousSystem(roles["repo_as"])
    repo_host = _deploy_component_host(repo_as, "rost-repo")
    repo_host.addSoftware("python3")
    repo_host.setFile(REPO_SERVICE_PATH, _load_example_asset("repo_server.py"))
    repo_host.appendStartCommand(f"chmod +x {REPO_SERVICE_PATH}")
    repo_host.appendStartCommand(
        "nohup {} --port {} >/var/log/rost_repo_server.log 2>&1 &".format(
            REPO_SERVICE_PATH,
            REPO_SERVICE_PORT,
        )
    )


def apply_special_policies(topology, roles):
    """Placeholder hook for future suppressor-specific routing behavior."""

    emu = topology["emu"]
    suppressor_as = roles["suppressor_as"]

    # The suppressor is not an application host. It is a network role that
    # should be realized by modifying the BGP behavior of routers in this AS.
    #
    # The most SEED-native extension point for this is a Hook that targets the
    # Ebgp layer and mutates the suppressor's border routers after the baseline
    # BIRD eBGP configuration has been generated. This is the same general
    # pattern used by seedemu/components/BgpAttackerComponent.py.
    emu.addHook(SuppressorPolicyHook(suppressor_as))


def main():
    """Build, annotate, and compile the demo RoST-style SEED environment."""

    script_name = os.path.basename(__file__)

    if len(sys.argv) == 1:
        platform = Platform.AMD64
    elif len(sys.argv) == 2:
        if sys.argv[1].lower() == "amd":
            platform = Platform.AMD64
        elif sys.argv[1].lower() == "arm":
            platform = Platform.ARM64
        else:
            print(f"Usage: {script_name} amd|arm")
            sys.exit(1)
    else:
        print(f"Usage: {script_name} amd|arm")
        sys.exit(1)

    topology = build_base_topology()
    roles = assign_rost_roles(topology)
    deploy_rost_components(topology, roles)
    apply_special_policies(topology, roles)

    emu = topology["emu"]
    emu.render()

    docker = Docker(platform=platform)
    emu.compile(docker, "./output", override=True)


if __name__ == "__main__":
    main()
