"""Deterministic graph, ASN, address, and resource planning."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import random
import re
from typing import List, Set, Tuple

from generator.topology.models import (
    AutonomousSystemPlan,
    ExternalLinkPlan,
    ResourceEstimate,
    TopologyPlan,
    TopologyRequest,
)
from generator.software import validate_software_specs


ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
EDGE_POLICIES = {"tree", "ring", "mesh", "random_connected", "explicit"}


def _graph_edges(request: TopologyRequest) -> Tuple[Tuple[int, int], ...]:
    count = request.as_count
    if request.edge_policy == "explicit":
        edges = set()
        for edge in request.explicit_edges:
            if len(edge) != 2:
                raise ValueError("each explicit edge must have two AS indexes")
            left, right = edge
            if left == right or not (0 <= left < count and 0 <= right < count):
                raise ValueError("explicit edge endpoint is invalid")
            normalized = tuple(sorted((left, right)))
            if normalized in edges:
                raise ValueError("duplicate explicit edge")
            edges.add(normalized)
    elif count == 1:
        return ()
    elif request.edge_policy == "tree":
        edges = {(index, (index - 1) // 2) for index in range(1, count)}
    elif request.edge_policy == "ring":
        edges = {(0, 1)} if count == 2 else {
            tuple(sorted((index, (index + 1) % count))) for index in range(count)
        }
    elif request.edge_policy == "mesh":
        edges = {(left, right) for left in range(count) for right in range(left + 1, count)}
    else:
        rng = random.Random(request.master_seed)
        order = list(range(count))
        rng.shuffle(order)
        edges = {
            tuple(sorted((order[index], order[rng.randrange(index)])))
            for index in range(1, count)
        }

    possible = [
        (left, right)
        for left in range(count)
        for right in range(left + 1, count)
        if (left, right) not in edges
    ]
    rng = random.Random(f"{request.master_seed}:extra-links")
    rng.shuffle(possible)
    if request.extra_links > len(possible):
        raise ValueError("extra_links exceeds the remaining simple graph capacity")
    edges.update(possible[:request.extra_links])
    return tuple(sorted(edges))


def _subnets(pool_text: str, prefixlen: int, count: int):
    pool = ipaddress.ip_network(pool_text, strict=True)
    if pool.version != 4 or prefixlen < pool.prefixlen or prefixlen > 30:
        raise ValueError(f"invalid IPv4 allocation pool {pool_text}/{prefixlen}")
    capacity = 1 << (prefixlen - pool.prefixlen)
    if count > capacity:
        raise ValueError(f"address pool {pool} has {capacity} subnets, requires {count}")
    iterator = pool.subnets(new_prefix=prefixlen)
    return tuple(next(iterator) for _ in range(count))


def _assert_connected(count: int, edges: Tuple[Tuple[int, int], ...]) -> None:
    if count <= 1:
        return
    adjacency = {index: set() for index in range(count)}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    visited, pending = set(), [0]
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        pending.extend(adjacency[node] - visited)
    if len(visited) != count:
        raise ValueError("generated AS graph is disconnected")


def _validate_request(request: TopologyRequest) -> None:
    if not ID_PATTERN.fullmatch(request.topology_id):
        raise ValueError("topology_id must be 3-48 lowercase snake_case characters")
    if not request.master_seed:
        raise ValueError("master_seed must not be empty")
    if not 1 <= request.as_count <= request.budget.max_ases:
        raise ValueError("as_count exceeds resource budget")
    if not 1 <= request.hosts_per_as <= 200:
        raise ValueError("hosts_per_as must be between 1 and 200")
    if request.edge_policy not in EDGE_POLICIES:
        raise ValueError(f"unsupported edge_policy={request.edge_policy}")
    if request.extra_links < 0:
        raise ValueError("extra_links must be non-negative")
    if request.edge_policy != "explicit" and request.explicit_edges:
        raise ValueError("explicit_edges requires edge_policy=explicit")
    if request.platform not in {"amd", "arm"}:
        raise ValueError("platform must be amd or arm")
    if request.asn_start < 1 or request.asn_start + request.as_count - 1 > 4294967294:
        raise ValueError("ASN allocation exceeds the 32-bit range")
    validate_software_specs(
        request.software,
        asns=tuple(range(request.asn_start, request.asn_start + request.as_count)),
        hosts_per_as=request.hosts_per_as,
    )
    lan_pool = ipaddress.ip_network(request.lan_pool, strict=True)
    ix_pool = ipaddress.ip_network(request.ix_pool, strict=True)
    loopback_pool = ipaddress.ip_network(request.loopback_pool, strict=True)
    pools = (("LAN", lan_pool), ("IX", ix_pool), ("loopback", loopback_pool))
    if any(network.version != 4 for _name, network in pools):
        raise ValueError("all topology address pools must be IPv4")
    for index, (left_name, left) in enumerate(pools):
        for right_name, right in pools[index + 1:]:
            if left.overlaps(right):
                raise ValueError(f"{left_name} and {right_name} pools must not overlap")
    if request.as_count > max(0, loopback_pool.num_addresses - 2):
        raise ValueError("loopback pool cannot hold all routers")
    usable = (1 << (32 - request.lan_prefixlen)) - 2
    if request.hosts_per_as + 2 > usable:
        raise ValueError(
            "LAN prefix cannot hold Docker gateway, router, and requested hosts"
        )
    ix_usable = (1 << (32 - request.ix_prefixlen)) - 2
    if ix_usable < 3:
        raise ValueError("IX prefix cannot hold Docker gateway and two router endpoints")


def plan_topology(request: TopologyRequest) -> TopologyPlan:
    _validate_request(request)
    edges = _graph_edges(request)
    _assert_connected(request.as_count, edges)
    if len(edges) > request.budget.max_links:
        raise ValueError("external link count exceeds resource budget")
    lan_subnets = _subnets(request.lan_pool, request.lan_prefixlen, request.as_count)
    ix_subnets = _subnets(request.ix_pool, request.ix_prefixlen, len(edges))
    loopback_network = ipaddress.ip_network(request.loopback_pool, strict=True)

    systems: List[AutonomousSystemPlan] = []
    for index, subnet in enumerate(lan_subnets):
        addresses = list(subnet.hosts())
        systems.append(
            AutonomousSystemPlan(
                index=index,
                asn=request.asn_start + index,
                lan_prefix=str(subnet),
                # Docker Compose reserves the first usable address for its
                # bridge gateway. SEED assets start at the second address.
                router_address=str(addresses[1]),
                loopback_address=str(loopback_network[index + 1]),
                host_addresses=tuple(
                    str(addresses[offset])
                    for offset in range(2, request.hosts_per_as + 2)
                ),
            )
        )
    links: List[ExternalLinkPlan] = []
    for index, ((left, right), subnet) in enumerate(zip(edges, ix_subnets)):
        addresses = list(subnet.hosts())
        links.append(
            ExternalLinkPlan(
                index=index,
                ix_id=1000 + index,
                left_asn=systems[left].asn,
                right_asn=systems[right].asn,
                prefix=str(subnet),
                left_address=str(addresses[1]),
                right_address=str(addresses[2]),
            )
        )

    estimate = ResourceEstimate(
        # SEED's Docker compiler adds two image dependency dummies. The
        # optional Internet Map is disabled to avoid host-port collisions.
        containers=request.as_count * (request.hosts_per_as + 1) + 2,
        networks=request.as_count + len(links),
        # Admission estimate for idle benchmark nodes. Runtime preflight keeps
        # an additional host reserve and does not treat this as a Docker limit.
        memory_mb=request.as_count * (128 + request.hosts_per_as * 64),
        cpu_cores=round(request.as_count * (0.10 + request.hosts_per_as * 0.05), 2),
        ases=request.as_count,
        links=len(links),
    )
    budget = request.budget
    violations = []
    for field in ("containers", "networks", "memory_mb", "cpu_cores", "ases", "links"):
        limit = getattr(budget, f"max_{field}")
        value = getattr(estimate, field)
        if value > limit:
            violations.append(f"{field}={value}>{limit}")
    if violations:
        raise ValueError("resource budget exceeded: " + ", ".join(violations))

    request_dict = request.to_dict()
    content = {
        "topology_id": request.topology_id,
        "topology_name": f"DECLARATIVE_{request.topology_id}",
        "master_seed": request.master_seed,
        "edge_policy": request.edge_policy,
        "platform": request.platform,
        "request": request_dict,
        "autonomous_systems": [item.__dict__ for item in systems],
        "external_links": [item.__dict__ for item in links],
        "resource_estimate": estimate.__dict__,
    }
    fingerprint = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TopologyPlan(
        topology_id=request.topology_id,
        topology_name=f"DECLARATIVE_{request.topology_id}",
        master_seed=request.master_seed,
        edge_policy=request.edge_policy,
        platform=request.platform,
        request=request_dict,
        autonomous_systems=tuple(systems),
        external_links=tuple(links),
        resource_estimate=estimate,
        fingerprint=fingerprint,
    )


def validate_topology_plan(plan: TopologyPlan) -> None:
    rebuilt = plan_topology(TopologyRequest.from_dict(plan.request))
    if rebuilt.to_dict() != plan.to_dict():
        raise ValueError("topology plan fingerprint or allocations have drifted")
