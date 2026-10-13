#!/usr/bin/env python3
# Read generated Compose labels and inspect live protocols/routes on all routers.
# Inputs: TestRunner paths; output: b51-runtime-test.json. Containers stay unchanged.

from __future__ import annotations

import shlex
from ipaddress import IPv4Interface

from seedemu.testing import ComposeRuntimeTest
from seedemu.testing.runtime import ASN_LABEL, NODE_LABEL, ComposeService


META = "org.seedsecuritylabs.seedemu.meta."


def discoverRouters(test: ComposeRuntimeTest):
    """Find OSPF and RIP routers from generated protocol labels."""
    routers = []
    for name, service in test.compose.get("services", {}).items():
        labels = service.get("labels", {})
        if labels.get(META + "seedemu_igp") not in {"rip", "ospf"}:
            continue
        routers.append(ComposeService(str(name), "", dict(labels)))
    return sorted(routers, key=lambda item: (int(item.labels[ASN_LABEL]), item.labels[NODE_LABEL]))


def checkRouter(test: ComposeRuntimeTest, router: ComposeService, peers) -> None:
    """Verify the declared IGP, own-AS learned loopbacks, and BGP sessions."""
    igp = str(router.labels[META + "seedemu_igp"])
    protocol = igp.upper()
    backend = router.labels.get(META + "seedemu_bgp_backend", "bird")
    if backend == "bird":
        test.exec_check(
            router.name + " has healthy BIRD protocols",
            router,
            "birdc show protocols | awk '{ print } "
            "$2 == \"" + protocol + "\" { igp++; if ($4 != \"up\") bad=1 } "
            "$2 ~ /^(OSPF|RIP)$/ && $2 != \"" + protocol + "\" { bad=1 } "
            "$2 == \"BGP\" { if ($4 != \"up\" || $6 != \"Established\") bad=1 } "
            "$2 ~ /^(Device|Direct|Kernel|Pipe)$/ { if ($4 != \"up\") bad=1 } "
            "END { exit (igp != 1 || bad) }'",
            retries=30, interval=3,
        )
        for peer in peers:
            loopback = str(peer.labels[META + "loopback_addr"])
            test.exec_check(
                "{} learns {} loopback through {}".format(router.name, peer.name, protocol),
                router,
                "birdc 'show route table t_{} {}/32' | grep -q '\\[{}1 '".format(igp, loopback, igp),
                retries=20, interval=2,
            )
    else:
        status = "show ip rip status" if igp == "rip" else "show ip ospf"
        test.exec_check(
            router.name + " runs FRR " + protocol, router,
            "pgrep -x {}d >/dev/null && vtysh -c {}".format(igp, shlex.quote(status)),
            retries=30, interval=3,
        )
        check_bgp = (
            "import json,subprocess; "
            "data=json.loads(subprocess.check_output(['vtysh','-c','show bgp ipv4 unicast summary json'])); "
            "peers=data.get('ipv4Unicast',data).get('peers',{}); "
            "assert peers and all(p.get('state') == 'Established' for p in peers.values()), peers"
        )
        test.exec_check(router.name + " has established BGP sessions", router, "python3 -c " + shlex.quote(check_bgp), retries=30, interval=3)
        for peer in peers:
            loopback = str(peer.labels[META + "loopback_addr"])
            check_route = (
                "import json,subprocess; "
                "data=json.loads(subprocess.check_output(['vtysh','-c',{}])); "
                "assert any(r.get('protocol') == {} for routes in data.values() for r in routes), data"
            ).format(repr("show ip route {}/32 json".format(loopback)), repr(igp))
            test.exec_check(
                "{} learns {} loopback through {}".format(router.name, peer.name, protocol),
                router, "python3 -c " + shlex.quote(check_route), retries=20, interval=2,
            )


def checkDirectionalMetric(test: ComposeRuntimeTest, router: ComposeService, peer: ComposeService, metric: int) -> None:
    """Check router's receive metric to peer's discovered loopback against metric."""
    loopback = str(peer.labels[META + "loopback_addr"])
    if router.labels.get(META + "seedemu_bgp_backend", "bird") == "bird":
        command = "birdc 'show route table t_rip {}/32 all' | grep -Eq 'RIP.metric: +{}$'".format(loopback, metric)
    else:
        check = (
            "import json,subprocess; "
            "data=json.loads(subprocess.check_output(['vtysh','-c',{}])); "
            "assert any(r.get('protocol') == 'rip' and r.get('metric') == {} "
            "for routes in data.values() for r in routes), data"
        ).format(repr("show ip route {}/32 json".format(loopback)), metric)
        command = "python3 -c " + shlex.quote(check)
    test.exec_check(
        "{} receives {} loopback with RIP metric {}".format(router.name, peer.name, metric),
        router, command, retries=20, interval=2,
    )


def checkReachability(test: ComposeRuntimeTest, routers) -> None:
    """Ping every other host/router physical interface using the default source."""
    hosts = [
        ComposeService(str(name), "", dict(service.get("labels", {})))
        for name, service in test.compose.get("services", {}).items()
        if service.get("labels", {}).get(META + "role") == "Host"
    ]
    test.structural_check("hosts are discovered for ordinary ping", bool(hosts), "found {} hosts".format(len(hosts)))
    sources = sorted(hosts + routers, key=lambda node: node.name)
    targets = []
    for node in sources:
        for key, address in node.labels.items():
            if key.startswith(META + "net.") and key.endswith(".address"):
                targets.append((node.name, str(IPv4Interface(str(address)).ip)))
    for source in sources:
        addresses = [(name, ip) for name, ip in targets if name != source.name]
        commands = [
            "ping -n -c 1 -W 1 -w 2 {} >/dev/null 2>&1 || {{ printf '%s\\n' {}; exit 1; }}".format(
                shlex.quote(ip), shlex.quote("unreachable: {}/{}".format(name, ip)),
            ) for name, ip in addresses
        ]
        commands.append("printf '%s\\n' '{}'".format("{} interface targets reachable".format(len(addresses))))
        test.exec_check(
            "{} reaches all {} other node interface addresses".format(source.name, len(addresses)),
            source, "\n".join(commands), retries=3, interval=2,
            timeout=max(45, len(addresses) * 3),
        )


def validateRuntime() -> int:
    """Check both IGPs, BGP and full physical-interface reachability."""
    test = ComposeRuntimeTest(__file__)
    routers = discoverRouters(test)
    test.structural_check("IGP routers are discovered", len(routers) == 27, "found {} routers; B00 topology has 27".format(len(routers)))
    protocols = {str(router.labels[META + "seedemu_igp"]) for router in routers}
    test.structural_check("OSPF and RIP both have routers", protocols == {"ospf", "rip"}, str(sorted(protocols)))
    for router in routers:
        peers = [peer for peer in routers if peer.labels[ASN_LABEL] == router.labels[ASN_LABEL] and peer.name != router.name]
        checkRouter(test, router, peers)
    indexed = {(int(router.labels[ASN_LABEL]), router.labels[NODE_LABEL]): router for router in routers}
    west, east = indexed.get((2, "r100")), indexed.get((2, "r101"))
    if west and east:
        # Advertised connected routes start at metric 1; receive increments are 2 and 4.
        checkDirectionalMetric(test, west, east, 3)
        checkDirectionalMetric(test, east, west, 5)
    checkReachability(test, routers)
    test.write_summary("b51-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(validateRuntime())
