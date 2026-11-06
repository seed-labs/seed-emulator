#!/usr/bin/env python3
"""Validate B07's generated topology metadata and representative live paths."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import socket
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest


META = "org.seedsecuritylabs.seedemu.meta."
EXPECTED_NODE_COUNT = 150
EXPECTED_ROLE_COUNTS = {
    "ix-route-server": 20,
    "transit-router": 70,
    "stub-router": 20,
    "stub-host": 40,
}
STUB_ASNS = range(150, 170)


def _host_port(service: dict, container_port: int) -> int | None:
    """Return the published host port for a Compose port entry."""
    for entry in service.get("ports", []):
        if isinstance(entry, dict):
            if int(entry.get("target", -1)) == container_port:
                published = entry.get("published")
                if published is not None:
                    return int(published)
            continue
        value = str(entry).split("/", 1)[0]
        parts = value.rsplit(":", 1)
        if len(parts) == 2 and parts[1] == str(container_port):
            return int(parts[0].rsplit(":", 1)[-1])
    return None


def _probe_http(test: ComposeRuntimeTest, name: str, port: int) -> None:
    result = None
    for attempt in range(30):
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=3) as response:
                result = response.status
            break
        except (OSError, URLError) as exc:
            result = str(exc)
            if attempt < 29:
                time.sleep(2)
    test.structural_check(name, result == 200, f"host port {port}: {result}")


def _probe_tcp(test: ComposeRuntimeTest, name: str, port: int) -> None:
    error = "not attempted"
    for attempt in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3):
                test.structural_check(name, True, f"127.0.0.1:{port} accepted a connection")
                return
        except OSError as exc:
            error = str(exc)
            if attempt < 29:
                time.sleep(2)
    test.structural_check(name, False, f"127.0.0.1:{port}: {error}")


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    services = test.compose.get("services", {})
    emulated = {
        name: service
        for name, service in services.items()
        if f"{META}topology.role" in service.get("labels", {})
    }
    roles = Counter(
        str(service.get("labels", {}).get(f"{META}topology.role"))
        for service in emulated.values()
    )
    test.structural_check(
        "default topology contains the expected number of each node role",
        roles == EXPECTED_ROLE_COUNTS and len(emulated) == EXPECTED_NODE_COUNT,
        f"roles={dict(roles)}, total={len(emulated)}",
    )

    coordinates = set()
    invalid_geo = []
    by_asn_role = Counter()
    for name, service in emulated.items():
        labels = service.get("labels", {})
        role = str(labels.get(f"{META}topology.role", ""))
        asn = str(labels.get(f"{META}asn", ""))
        node = str(labels.get(f"{META}nodename", ""))
        by_asn_role[(asn, role)] += 1
        try:
            lat = float(labels[f"{META}geo.lat"])
            lon = float(labels[f"{META}geo.lon"])
            if not (-60 < lat < 66 and -180 <= lon <= 180):
                raise ValueError("coordinate outside configured bounds")
            coordinates.add((round(lat, 6), round(lon, 6)))
            for key in ("geo.city", "geo.country", "geo.region", "geo.source"):
                if not labels.get(f"{META}{key}"):
                    raise ValueError(f"missing {key}")
        except (KeyError, TypeError, ValueError) as exc:
            invalid_geo.append(f"{name}: {exc}")
        if not asn or not node or not labels.get(f"{META}net.0.address"):
            invalid_geo.append(f"{name}: missing ASN, node name, or first interface address")
    test.structural_check(
        "every emulated service has valid geographic and SeedEMU metadata",
        not invalid_geo,
        "; ".join(invalid_geo[:8])
        if invalid_geo
        else f"all {EXPECTED_NODE_COUNT} services have coordinates and metadata",
    )
    test.structural_check(
        "all emulated nodes have distinct geographic coordinates",
        len(coordinates) == len(emulated),
        f"{len(coordinates)} unique coordinates for {len(emulated)} nodes",
    )

    stub_errors = []
    for asn in STUB_ASNS:
        members = [
            (name, service, service.get("labels", {}))
            for name, service in emulated.items()
            if str(service.get("labels", {}).get(f"{META}asn")) == str(asn)
        ]
        routers = [(name, labels) for name, _, labels in members if labels.get(f"{META}topology.role") == "stub-router"]
        hosts = [(name, labels) for name, _, labels in members if labels.get(f"{META}topology.role") == "stub-host"]
        expected_ix = str(asn - 50)
        if len(routers) != 1 or len(hosts) != 2:
            stub_errors.append(f"AS{asn}: {len(routers)} routers, {len(hosts)} hosts")
            continue
        router_name, router = routers[0]
        if router.get(f"{META}geo.anchor_ix") != expected_ix:
            stub_errors.append(f"{router_name}: incorrect IX anchor")
        for host_name, host in hosts:
            if host.get(f"{META}geo.anchor_ix") != expected_ix:
                stub_errors.append(f"{host_name}: incorrect IX anchor")
            if host.get(f"{META}geo.anchor_router") != f"as{asn}/router0":
                stub_errors.append(f"{host_name}: incorrect parent router")
            if host.get(f"{META}geo.country") != router.get(f"{META}geo.country"):
                stub_errors.append(f"{host_name}: host and router are in different countries")
    test.structural_check(
        "each stub AS has one anchored router and two same-country hosts",
        not stub_errors,
        "; ".join(stub_errors[:8]) if stub_errors else "all 20 stub ASes satisfy the layout",
    )

    ix_networks = {
        name: network
        for name, network in test.compose.get("networks", {}).items()
        if network.get("labels", {}).get(f"{META}type") == "global"
        and network.get("labels", {}).get(f"{META}scope") == "ix"
    }
    ix_errors = []
    for ix in range(100, 120):
        matches = [
            (name, network)
            for name, network in ix_networks.items()
            if network.get("labels", {}).get(f"{META}name") == f"ix{ix}"
        ]
        if len(matches) != 1:
            ix_errors.append(f"IX{ix}: expected one labelled IX LAN, got {len(matches)}")
    test.structural_check(
        "all 20 global IX LANs carry geographic metadata",
        len(ix_networks) == 20 and not ix_errors
        and all(
            network.get("labels", {}).get(f"{META}geo.lat") is not None
            and network.get("labels", {}).get(f"{META}geo.lon") is not None
            for network in ix_networks.values()
        ),
        "; ".join(ix_errors[:8]) if ix_errors else f"found {len(ix_networks)} IX LANs with coordinates",
    )

    # Exercise route exchange across the provider/customer topology.
    host150 = test.require_service(150, "host_0")
    host169 = test.require_service(169, "host_0")
    if host150 and host169:
        test.exec_check(
            "AS150 reaches AS169 across the routed topology",
            host150,
            f"ping -c 3 -W 3 {host169.address} >/dev/null",
            retries=20,
            interval=5,
            timeout=20,
        )

    # Check both InternetMap UIs and the host-network observer on their configured ports.
    topology_name = "internetmap_toplogy.map.seed"
    geographic_name = "internetmap_geo.map.seed"
    observer_name = "traffic_observer.map.seed"
    topology_service = services.get(topology_name, {})
    geographic_service = services.get(geographic_name, {})
    topology_port = _host_port(topology_service, 80)
    geographic_port = _host_port(geographic_service, 80)
    test.structural_check("InternetMap topology service is present and publishes HTTP", topology_port is not None, str(topology_service.get("ports")))
    test.structural_check("InternetMap geographic service is present and publishes HTTP", geographic_port is not None, str(geographic_service.get("ports")))
    if topology_port is not None:
        _probe_http(test, "topology map HTTP endpoint responds", topology_port)
    if geographic_port is not None:
        _probe_http(test, "geographic map HTTP endpoint responds", geographic_port)

    observer = services.get(observer_name, {})
    observer_config = observer.get("environment", {}).get("TRAFFIC_CONTROL_ADDR", "")
    try:
        observer_port = int(str(observer_config).rsplit(":", 1)[-1])
    except ValueError:
        observer_port = None
    observer_valid = observer.get("network_mode") == "host" and observer_port is not None
    test.structural_check(
        "traffic observer uses host networking with a configured control port",
        observer_valid,
        f"network_mode={observer.get('network_mode')}, TRAFFIC_CONTROL_ADDR={observer_config}",
    )
    if observer_valid:
        _probe_tcp(test, "traffic observer control port accepts connections", observer_port)

    test.write_summary("b07-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
