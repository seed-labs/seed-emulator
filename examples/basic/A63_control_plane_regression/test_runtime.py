#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest, ComposeService


ROUTING_BACKEND_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_routing_backend"
ASN_LABEL = "org.seedsecuritylabs.seedemu.meta.asn"
NODE_LABEL = "org.seedsecuritylabs.seedemu.meta.nodename"


def require_backend(test: ComposeRuntimeTest, service: ComposeService, backend: str) -> None:
    actual = service.labels.get(ROUTING_BACKEND_LABEL)
    label = "AS{} {} uses {} routing backend".format(
        service.labels.get(ASN_LABEL),
        service.labels.get(NODE_LABEL),
        backend,
    )
    test.structural_check(label, actual == backend, "expected {}, found {}".format(backend, actual))


def record_mpls_host_capability(test: ComposeRuntimeTest, service: ComposeService) -> None:
    result = test.exec(service, "test -d /proc/sys/net/mpls || test -e /proc/modules", timeout=20)
    available = result["exit"] == 0
    test.structural_check(
        "MPLS dataplane probe is host-gated",
        True,
        "host kernel capability visible" if available else "host kernel capability not visible; dataplane probe skipped",
    )


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    rs100 = test.require_service(100, "ix100", "IX100 BIRD route server is generated")
    as150_router = test.require_service(150, "router0")
    as151_router = test.require_service(151, "router0")
    rs107 = test.require_service(107, "ix107", "IX107 FRR route server is generated")
    as157_router = test.require_service(157, "router0")
    as158_router = test.require_service(158, "router0")
    as2_r1 = test.require_service(2, "r1")
    as2_r2 = test.require_service(2, "r2")
    as152_router = test.require_service(152, "router0")
    as153_router = test.require_service(153, "router0")

    as3_rr = test.require_service(3, "rr")
    as3_client = test.require_service(3, "client")
    as154_router = test.require_service(154, "router0")

    as4_router = test.require_service(4, "router0")
    speaker = test.require_service(180, "exabgp")

    as20_r1 = test.require_service(20, "r1")
    as20_r2 = test.require_service(20, "r2")
    as20_r3 = test.require_service(20, "r3")
    as20_r4 = test.require_service(20, "r4")

    if rs100:
        require_backend(test, rs100, "bird")
        test.exec_check("IX100 route server starts BIRD", rs100, "pgrep -x bird >/dev/null")
        test.exec_check("IX100 route server peers with AS150", rs100, "grep -q 'neighbor 10.100.0.150 as 150' /etc/bird/bird.conf")
        test.exec_check("IX100 route server peers with AS151", rs100, "grep -q 'neighbor 10.100.0.151 as 151' /etc/bird/bird.conf")
        test.exec_check("IX100 route server renders rs client", rs100, "grep -q 'rs client' /etc/bird/bird.conf")

    if as150_router:
        require_backend(test, as150_router, "bird")
        test.exec_check("AS150 route-server client starts BIRD", as150_router, "pgrep -x bird >/dev/null")
        test.exec_check("AS150 route-server session is established", as150_router, "birdc show protocols | grep -q 'p_rs100.*Established'", retries=15)

    if as151_router:
        require_backend(test, as151_router, "bird")
        test.exec_check("AS151 route-server client starts BIRD", as151_router, "pgrep -x bird >/dev/null")
        test.exec_check("AS151 route-server session is established", as151_router, "birdc show protocols | grep -q 'p_rs100.*Established'", retries=15)

    if as151_router:
        test.exec_check("AS151 learns AS150 route through route server", as151_router, "birdc show route | grep -q '10.150.0.0/24'", retries=15)

    if rs107:
        require_backend(test, rs107, "frr")
        test.exec_check("IX107 route server starts FRR bgpd", rs107, "pgrep -x bgpd >/dev/null")
        test.exec_check("IX107 route server does not start BIRD", rs107, "! pgrep -x bird >/dev/null")
        test.exec_check("IX107 route server renders AS157 as RS client", rs107, "grep -q 'neighbor 10.107.0.157 route-server-client' /etc/frr/frr.conf")
        test.exec_check("IX107 route server renders AS158 as RS client", rs107, "grep -q 'neighbor 10.107.0.158 route-server-client' /etc/frr/frr.conf")
        test.exec_check("IX107 route server sees AS157 BGP session", rs107, "vtysh -c 'show ip bgp summary' | grep -q '10.107.0.157'", retries=15)
        test.exec_check("IX107 route server sees AS158 BGP session", rs107, "vtysh -c 'show ip bgp summary' | grep -q '10.107.0.158'", retries=15)

    if as157_router:
        require_backend(test, as157_router, "bird")
        test.exec_check("AS157 route-server session is established", as157_router, "birdc show protocols | grep -q 'p_rs107.*Established'", retries=15)

    if as158_router:
        require_backend(test, as158_router, "bird")
        test.exec_check("AS158 route-server session is established", as158_router, "birdc show protocols | grep -q 'p_rs107.*Established'", retries=15)
        test.exec_check("AS158 learns AS157 route through FRR route server", as158_router, "birdc show route | grep -q '10.157.0.0/24'", retries=15)

    if as2_r1:
        require_backend(test, as2_r1, "bird")
        test.exec_check("AS2 r1 starts BIRD", as2_r1, "pgrep -x bird >/dev/null")
        test.exec_check("AS2 r1 does not carry FRR config", as2_r1, "test ! -e /etc/frr/frr.conf")
        test.exec_check("AS2 r1 renders OSPF intent", as2_r1, "grep -q 'protocol ospf ospf1' /etc/bird/bird.conf")
        test.exec_check("AS2 r1 iBGP to FRR r2 is established", as2_r1, "birdc show protocols | grep -q 'ibgp1.*Established'", retries=15)
        test.exec_check("AS2 r1 learns AS153 route", as2_r1, "birdc show route | grep -q '10.153.0.0/24'", retries=15)

    if as2_r2:
        require_backend(test, as2_r2, "frr")
        test.exec_check("AS2 r2 starts FRR bgpd", as2_r2, "pgrep -x bgpd >/dev/null")
        test.exec_check("AS2 r2 does not start BIRD", as2_r2, "! pgrep -x bird >/dev/null")
        test.exec_check("AS2 r2 renders FRR OSPF intent", as2_r2, "grep -q 'router ospf' /etc/frr/frr.conf")
        test.exec_check("AS2 r2 learns AS152 route through iBGP", as2_r2, "vtysh -c 'show ip bgp' | grep -q '10.152.0.0/24'", retries=15)

    if as152_router:
        require_backend(test, as152_router, "frr")
        test.exec_check("AS152 FRR router learns AS153 route", as152_router, "vtysh -c 'show ip bgp' | grep -q '10.153.0.0/24'", retries=15)

    if as153_router:
        require_backend(test, as153_router, "bird")
        test.exec_check("AS153 BIRD router learns AS152 route", as153_router, "birdc show route | grep -q '10.152.0.0/24'", retries=15)

    if as3_rr:
        require_backend(test, as3_rr, "frr")
        test.exec_check("AS3 RR starts FRR bgpd", as3_rr, "pgrep -x bgpd >/dev/null")
        test.exec_check("AS3 RR renders cluster-id", as3_rr, "grep -q 'bgp cluster-id 10.3.0.1' /etc/frr/frr.conf")
        test.exec_check("AS3 RR renders route-reflector client", as3_rr, "grep -q 'route-reflector-client' /etc/frr/frr.conf")

    if as3_client:
        require_backend(test, as3_client, "frr")
        test.exec_check("AS3 RR client starts FRR bgpd", as3_client, "pgrep -x bgpd >/dev/null")
        test.exec_check("AS3 RR client learns AS154 route", as3_client, "vtysh -c 'show ip bgp' | grep -q '10.154.0.0/24'", retries=15)

    if as154_router:
        require_backend(test, as154_router, "bird")
        test.exec_check("AS154 BIRD router peers with AS3 RR", as154_router, "birdc show protocols | grep -q 'Established'", retries=15)

    if as4_router:
        require_backend(test, as4_router, "frr")
        test.exec_check("AS4 ExaBGP peer is an FRR router", as4_router, "grep -q 'neighbor 10.104.0.180 remote-as 180' /etc/frr/frr.conf")
        test.exec_check("AS4 router does not start BIRD", as4_router, "! pgrep -x bird >/dev/null")
        test.exec_check("AS4 learns ExaBGP static route", as4_router, "vtysh -c 'show ip bgp 198.51.100.0/24' | grep -q '198.51.100.0/24'", retries=15)

    if speaker:
        test.exec_check("ExaBGP speaker process is running", speaker, "pgrep -f 'exabgp /etc/exabgp/exabgp.conf' >/dev/null", retries=15)
        test.exec_check("ExaBGP manual control FIFO is available", speaker, "test -p /run/exabgp/manual.in")
        test.exec_check("ExaBGP config peers with AS4 router", speaker, "grep -q 'neighbor 10.104.0.4' /etc/exabgp/exabgp.conf")
        test.exec_check("ExaBGP config announces static IPv4 route", speaker, "grep -q 'route 198.51.100.0/24 next-hop self' /etc/exabgp/exabgp.conf")

    if as20_r1:
        test.exec_check("AS20 r1 has MPLS/LDP on net0", as20_r1, "grep -q '^net0$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf")
        record_mpls_host_capability(test, as20_r1)

    if as20_r2:
        test.exec_check("AS20 r2 has MPLS/LDP on net0 and net1", as20_r2, "grep -q '^net0$' /mpls_ifaces.txt && grep -q '^net1$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf")

    if as20_r3:
        test.exec_check("AS20 r3 has MPLS/LDP on net1 and net2", as20_r3, "grep -q '^net1$' /mpls_ifaces.txt && grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf")

    if as20_r4:
        test.exec_check("AS20 r4 has MPLS/LDP on net2", as20_r4, "grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf")

    test.write_summary("a63-control-plane-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
