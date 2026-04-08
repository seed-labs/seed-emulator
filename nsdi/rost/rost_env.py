#!/usr/bin/env python3
# encoding: utf-8

import os
from pathlib import Path
import random
import re
import sys

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Hook
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers


# Fraction of eligible ASes that should be marked as adopting ASes.
ADOPTION_RATE = 0.4

# Seed used when choosing adopting ASes.
RANDOM_SEED = 7

# AS that will later host the repository component.
REPO_AS = 154

# Transit ASes that should statically withhold selected prefixes on export.
SUPPRESSOR_ASES = [3]

# Prefixes affected by suppressor export withholding.
SUPPRESSOR_TARGET_PREFIXES = ["10.155.0.0/24"]

# Minimal repository service settings for the demo repository host.
REPO_SERVICE_PORT = 18080
REPO_SERVICE_PATH = "/root/repo_server.py"
AGENT_SCRIPT_PATH = "/root/agent.py"
ROUTER_HELPER_PORT = 18081
ROUTER_HELPER_PATH = "/root/router_helper.py"
ROST_POLICY_PATH = "/etc/bird/rost_policy.conf"


class SuppressorPolicyHook(Hook):
    """Patch rendered BIRD config for suppressor anchor routers."""

    def __init__(self, suppressor_asns, target_prefixes):
        self._suppressor_asns = sorted(suppressor_asns)
        self._target_prefixes = sorted(target_prefixes)

    def getName(self):
        return "SuppressorPolicyHook"

    def getTargetLayer(self):
        # Run after iBGP has rendered so the full router bird.conf is present.
        return "Ibgp"

    def postrender(self, emulator):
        base = emulator.getRegistry().get("seedemu", "layer", "Base")

        for asn in self._suppressor_asns:
            as_obj = base.getAutonomousSystem(asn)
            router = _get_component_anchor_router(as_obj)
            bird_conf = _get_node_file_content(router, "/etc/bird/bird.conf")
            patched_conf = _patch_suppressor_bird_conf(bird_conf, self._target_prefixes)

            router.setAttribute("rost_role", "suppressor-anchor")
            router.setAttribute("rost_suppressor_bird_patched", True)
            router.setAttribute("rost_suppressor_prefixes", list(self._target_prefixes))
            router.setFile("/etc/bird/bird.conf", patched_conf)


class RostBirdPolicyHook(Hook):
    """Patch rendered BIRD config for adopting-AS anchor routers."""

    def __init__(self, adopting_ases):
        self._adopting_ases = sorted(adopting_ases)

    def getName(self):
        return "RostBirdPolicyHook"

    def getTargetLayer(self):
        # Run after iBGP has rendered so the full router bird.conf is present.
        return "Ibgp"

    def postrender(self, emulator):
        base = emulator.getRegistry().get("seedemu", "layer", "Base")

        for asn in self._adopting_ases:
            as_obj = base.getAutonomousSystem(asn)
            router = _get_component_anchor_router(as_obj)
            bird_conf = _get_node_file_content(router, "/etc/bird/bird.conf")
            patched_conf = _patch_rost_bird_conf(bird_conf)

            router.setAttribute("rost_role", "adopting-anchor")
            router.setAttribute("rost_bird_patched", True)
            router.setFile("/etc/bird/bird.conf", patched_conf)
            router.setFile(ROST_POLICY_PATH, _build_rost_policy_conf())


def _get_node_file_content(node, path):
    file_path, content = node.getFile(path).get()
    assert file_path == path, f"unexpected file handle for {path}: {file_path}"
    return content


def _sanitize_bird_identifier(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


def _build_filter_definition(filter_name, body_lines):
    indented = "\n".join(f"    {line}" for line in body_lines)
    return f"filter {filter_name} {{\n{indented}\n}}\n"


def _build_function_definition(function_name, body_lines):
    indented = "\n".join(f"    {line}" for line in body_lines)
    return f"function {function_name}()\n{{\n{indented}\n}}\n"


def _build_rost_policy_conf():
    return """# Managed by the RoST router helper.
# This file carries dynamic RoST state only. The main /etc/bird/bird.conf
# remains static after rost_env.py injects the wrapper filters.

# Enable/disable switch for all RoST controls. The helper will change this
# function body and then run `birdc configure`.
function rost_is_enabled()
{
    return false;
}

# Export-side suppression predicate. The helper will replace the body with
# prefix-specific checks such as `if net ~ [ 203.0.113.0/24 ] then return true;`.
function rost_export_is_suppressed()
{
    return false;
}

# Export-side allow predicate. When RoST is enabled, only prefixes that match
# this predicate will be exported.
function rost_export_is_allowed()
{
    return false;
}

# Export-side attribute mutation hook. The helper can add a BGP community here
# to simulate RouteID insertion before the route is announced.
function rost_apply_export_attributes()
{
}

# Import-side invalid-route predicate. The helper will replace the body with
# route or prefix-specific rejection tests so BGP re-selects another path.
function rost_import_is_invalid()
{
    return false;
}
"""


def _translate_export_expression(export_expr):
    expr = export_expr.strip()
    if expr == "all":
        return "true"
    if expr == "none":
        return "false"
    if expr.startswith("where "):
        return expr[len("where ") :].strip()
    return expr


def _insert_rost_policy_include(bird_conf):
    include_line = f'include "{ROST_POLICY_PATH}";'
    if include_line in bird_conf:
        return bird_conf

    define_matches = list(
        re.finditer(r"^define\s+[A-Z_]+\s*=\s*\([^)]+\);\s*$", bird_conf, flags=re.MULTILINE)
    )
    if define_matches:
        insert_at = define_matches[-1].end()
        return bird_conf[:insert_at] + "\n" + include_line + bird_conf[insert_at:]

    first_bgp = bird_conf.find("protocol bgp ")
    if first_bgp >= 0:
        return bird_conf[:first_bgp] + include_line + "\n" + bird_conf[first_bgp:]

    return bird_conf.rstrip() + "\n" + include_line + "\n"


def _insert_after_defines(bird_conf, snippet):
    define_matches = list(
        re.finditer(r"^define\s+[A-Z_]+\s*=\s*\([^)]+\);\s*$", bird_conf, flags=re.MULTILINE)
    )
    if define_matches:
        insert_at = define_matches[-1].end()
        return bird_conf[:insert_at] + "\n" + snippet + bird_conf[insert_at:]

    first_bgp = bird_conf.find("protocol bgp ")
    if first_bgp >= 0:
        return bird_conf[:first_bgp] + snippet + "\n" + bird_conf[first_bgp:]

    return bird_conf.rstrip() + "\n" + snippet + "\n"


def _wrap_ebgp_protocol(protocol_name, local_asn, peer_asn, import_body, export_expr):
    tag = _sanitize_bird_identifier(protocol_name)
    import_filter_name = f"rost_import_base_{tag}"
    export_filter_name = f"rost_export_base_{tag}"
    export_guard = _translate_export_expression(export_expr)

    import_lines = ["if rost_is_enabled() && rost_import_is_invalid() then reject;"]
    import_lines.extend(line.strip() for line in import_body.strip().splitlines())
    export_lines = [
        f"if !({export_guard}) then reject;",
        "if !rost_is_enabled() then accept;",
        "if !rost_export_is_allowed() then reject;",
        "if rost_is_enabled() && rost_export_is_suppressed() then reject;",
        "rost_apply_export_attributes();",
        "accept;",
    ]

    filter_defs = (
        "\n"
        + _build_filter_definition(import_filter_name, import_lines)
        + _build_filter_definition(export_filter_name, export_lines)
    )

    protocol_body = f"""protocol bgp {protocol_name} {{
    ipv4 {{
        table t_bgp;
        import filter {import_filter_name};
        export filter {export_filter_name};
        next hop self;
    }};
    local {local_asn[0]} as {local_asn[1]};
    neighbor {peer_asn[0]} as {peer_asn[1]};
}}"""
    return filter_defs + protocol_body


def _build_suppressor_policy_functions(target_prefixes):
    lines = []
    if target_prefixes:
        lines.append(f'if net ~ [ {", ".join(target_prefixes)} ] then return true;')
    lines.append("return false;")
    return _build_function_definition("rost_static_suppressor_match", lines)


def _wrap_suppressor_ebgp_protocol(protocol_name, local_asn, peer_asn, import_body, export_expr):
    tag = _sanitize_bird_identifier(protocol_name)
    import_filter_name = f"rost_suppressor_import_base_{tag}"
    export_filter_name = f"rost_suppressor_export_base_{tag}"
    export_guard = _translate_export_expression(export_expr)

    import_lines = [line.strip() for line in import_body.strip().splitlines()]
    export_lines = [
        f"if !({export_guard}) then reject;",
        "if rost_static_suppressor_match() then reject;",
        "accept;",
    ]

    filter_defs = (
        "\n"
        + _build_filter_definition(import_filter_name, import_lines)
        + _build_filter_definition(export_filter_name, export_lines)
    )

    protocol_body = f"""protocol bgp {protocol_name} {{
    ipv4 {{
        table t_bgp;
        import filter {import_filter_name};
        export filter {export_filter_name};
        next hop self;
    }};
    local {local_asn[0]} as {local_asn[1]};
    neighbor {peer_asn[0]} as {peer_asn[1]};
}}"""
    return filter_defs + protocol_body


def _patch_rost_bird_conf(bird_conf):
    bird_conf = _insert_rost_policy_include(bird_conf)

    protocol_pattern = re.compile(
        r"""protocol\s+bgp\s+(?P<name>\S+)\s*\{
\s*ipv4\s*\{
\s*table\s+t_bgp;
\s*import\s+filter\s*\{
(?P<import_body>.*?)
\s*\};
\s*export\s+(?P<export_expr>.*?);
\s*next\s+hop\s+self;
\s*\};
\s*local\s+(?P<local_addr>\S+)\s+as\s+(?P<local_asn>\d+);
\s*neighbor\s+(?P<peer_addr>\S+)\s+as\s+(?P<peer_asn>\d+);
\s*\}""",
        flags=re.DOTALL,
    )

    def replace_protocol(match):
        local_asn = match.group("local_asn")
        peer_asn = match.group("peer_asn")
        if local_asn == peer_asn:
            return match.group(0)

        return _wrap_ebgp_protocol(
            protocol_name=match.group("name"),
            local_asn=(match.group("local_addr"), local_asn),
            peer_asn=(match.group("peer_addr"), peer_asn),
            import_body=match.group("import_body"),
            export_expr=match.group("export_expr"),
        )

    return protocol_pattern.sub(replace_protocol, bird_conf)


def _patch_suppressor_bird_conf(bird_conf, target_prefixes):
    function_name = "rost_static_suppressor_match"
    if f"function {function_name}()" not in bird_conf:
        bird_conf = _insert_after_defines(
            bird_conf,
            _build_suppressor_policy_functions(target_prefixes).rstrip(),
        )

    protocol_pattern = re.compile(
        r"""protocol\s+bgp\s+(?P<name>\S+)\s*\{
\s*ipv4\s*\{
\s*table\s+t_bgp;
\s*import\s+filter\s*\{
(?P<import_body>.*?)
\s*\};
\s*export\s+(?P<export_expr>.*?);
\s*next\s+hop\s+self;
\s*\};
\s*local\s+(?P<local_addr>\S+)\s+as\s+(?P<local_asn>\d+);
\s*neighbor\s+(?P<peer_addr>\S+)\s+as\s+(?P<peer_asn>\d+);
\s*\}""",
        flags=re.DOTALL,
    )

    def replace_protocol(match):
        local_asn = match.group("local_asn")
        peer_asn = match.group("peer_asn")
        if local_asn == peer_asn:
            return match.group(0)

        return _wrap_suppressor_ebgp_protocol(
            protocol_name=match.group("name"),
            local_asn=(match.group("local_addr"), local_asn),
            peer_asn=(match.group("peer_addr"), peer_asn),
            import_body=match.group("import_body"),
            export_expr=match.group("export_expr"),
        )

    return protocol_pattern.sub(replace_protocol, bird_conf)


def _ensure_component_network(as_obj):
    """Return an existing local network for RoST component hosts.

    This example stays topology-neutral by reusing an existing AS-local network
    that is already attached to the anchor router. It must not create a new
    router-facing network or alter router interface membership.
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
    """Return the anchor router used for RoST components in an AS."""

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
    ebgp.addPrivatePeerings(103, [3], [154, 155], PeerRelationship.Provider)

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
    suppressor_ases = sorted(SUPPRESSOR_ASES)
    suppressor_set = set(suppressor_ases)

    assert REPO_AS in all_asns, "REPO_AS must exist in the topology"
    assert len(suppressor_ases) > 0, "at least one suppressor AS must be configured"
    assert REPO_AS not in suppressor_set, "REPO_AS cannot also be a suppressor AS"
    assert suppressor_set <= all_asns, "all suppressor ASNs must exist in the topology"
    assert suppressor_set <= set(topology["transit_asns"]), (
        "suppressor ASes should be central/transit-like ASes in this demo topology"
    )

    # Adoption is assigned independently of topology construction. For this
    # revision, any non-repository and non-suppressor AS may adopt.
    eligible = sorted(all_asns - {REPO_AS} - suppressor_set)

    rng = random.Random(RANDOM_SEED)
    adopting = []
    for asn in eligible:
        if rng.random() < ADOPTION_RATE:
            adopting.append(asn)

    return {
        "repo_as": REPO_AS,
        "suppressor_ases": suppressor_ases,
        "suppressor_target_prefixes": sorted(SUPPRESSOR_TARGET_PREFIXES),
        "eligible_adopters": eligible,
        "adopting_ases": sorted(adopting),
        "ordinary_ases": sorted(all_asns - {REPO_AS} - suppressor_set - set(adopting)),
    }


def deploy_rost_components(topology, roles):
    """Deploy minimal RoST component hosts and start the repository service."""

    base = topology["base"]

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
        # Agent execution stays manual so users can drive the demo explicitly.
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
    """Apply static suppressor policy and dynamic adopting-AS policy hooks."""

    emu = topology["emu"]
    adopting_ases = roles["adopting_ases"]
    emu.addHook(
        SuppressorPolicyHook(
            roles["suppressor_ases"],
            roles["suppressor_target_prefixes"],
        )
    )
    emu.addHook(RostBirdPolicyHook(adopting_ases))


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
