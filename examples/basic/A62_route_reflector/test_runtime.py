#!/usr/bin/env python3
#
# Purpose: validate the running A62 IPv4/BIRD Route Reflector example after
# TestRunner starts Docker Compose. Inputs come from TestRunner environment
# variables and generated docker-compose.yml labels. Outputs are JSON runtime
# summaries. Side effects are limited to read-only protocol checks.

from __future__ import annotations

from pathlib import Path
import sys
from typing import List


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest, ComposeService
from seedemu.testing.runtime import ADDRESS_LABEL, ASN_LABEL, NODE_LABEL


EXPECTED_ROUTER_COUNT = 31

BIRD_PROTOCOL_HEALTH_COMMAND = (
    "birdc show protocols | awk '"
    "NR <= 2 { next } "
    "$4 != \"up\" { print; bad=1 } "
    "$2 == \"BGP\" && $NF != \"Established\" { print; bad=1 } "
    "END { exit bad }"
    "'"
)

RR_IBGP_NAME_COMMAND = (
    "birdc show protocols | awk '"
    "NR <= 2 { next } "
    "$2 == \"BGP\" && $1 ~ /^Ibgp/ { seen=1; if (tolower($1) !~ /rr/) { print; bad=1 } } "
    "END { if (!seen) { print \"no iBGP protocols found\"; exit 1 } exit bad }"
    "'"
)


def discover_routers(test: ComposeRuntimeTest) -> List[ComposeService]:
    """Return generated router services sorted by AS and node name."""
    services: List[ComposeService] = []

    for name, service in test.compose.get("services", {}).items():
        if not (str(name).startswith("brdnode_") or str(name).startswith("rnode_")):
            continue

        labels = dict(service.get("labels", {}))
        address = str(labels.get(ADDRESS_LABEL, "")).split("/", 1)[0]
        services.append(ComposeService(name=str(name), address=address, labels=labels))

    services.sort(
        key=lambda service: (
            int(str(service.labels.get(ASN_LABEL, "0"))),
            str(service.labels.get(NODE_LABEL, service.name)),
        )
    )
    return services


def service_label(service: ComposeService) -> str:
    """Return a compact AS/node label for a generated service."""
    return "AS{} {}".format(service.labels.get(ASN_LABEL, "?"), service.labels.get(NODE_LABEL, service.name))


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    routers = discover_routers(test)
    test.structural_check(
        "A62 generates all router services",
        len(routers) == EXPECTED_ROUTER_COUNT,
        "found {} router services".format(len(routers)),
    )

    for router in routers:
        test.exec_check(
            "{} BIRD protocols are healthy".format(service_label(router)),
            router,
            BIRD_PROTOCOL_HEALTH_COMMAND,
            retries=40,
            interval=3,
            timeout=60,
        )

    rr_targets = [
        (3, "r100"),
        (3, "r103"),
        (3, "r104"),
        (3, "r105"),
        (3, "r110"),
        (3, "r111"),
        (3, "r112"),
        (3, "r113"),
        (12, "r101"),
        (12, "r104"),
    ]
    for asn, node in rr_targets:
        router = test.find_service(asn, node)
        if router:
            test.exec_check(
                "{} RR iBGP protocol names contain rr".format(service_label(router)),
                router,
                RR_IBGP_NAME_COMMAND,
                retries=20,
                interval=3,
                timeout=45,
            )
        else:
            test.structural_check(
                "AS{} {} is available for RR protocol checks".format(asn, node),
                False,
                "service for AS{} node {} not found".format(asn, node),
            )

    test.write_summary("a62-route-reflector-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
