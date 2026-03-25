#!/usr/bin/env python3
# encoding: utf-8

import argparse
from web3 import Web3
import json


def extract_ip(addr: str | None):
    if not addr:
        return None
    return addr.rsplit(":", 1)[0]


def main():
    parser = argparse.ArgumentParser(description="Query peer list from an Ethereum node")
    parser.add_argument(
        "--node",
        type=str,
        default="http://10.152.0.71:8545",
        help="Ethereum node RPC URL"
    )
    args = parser.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.node))
    peers = w3.provider.make_request("admin_peers", [])

    result = {}

    for p in peers.get("result", []):
        network = p.get("network", {})
        local_ip = extract_ip(network.get("localAddress"))
        remote_ip = extract_ip(network.get("remoteAddress"))

        if not local_ip or not remote_ip:
            continue

        if local_ip not in result:
            result[local_ip] = {
                "peers": [],
                "count": 0
            }

        result[local_ip]["peers"].append(remote_ip)
        result[local_ip]["count"] += 1

    # ---- JSON only output ----
    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()

