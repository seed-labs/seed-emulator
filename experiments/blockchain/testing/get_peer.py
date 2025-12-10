#!/usr/bin/env python3
# encoding: utf-8

import argparse
from web3 import Web3
from datetime import datetime
import json

def main():
    # ---- Command-line arguments ----
    parser = argparse.ArgumentParser(description="Query peer list from an Ethereum node")
    parser.add_argument(
        "--node",
        type=str,
        default="http://10.152.0.71:8545",
        help="Ethereum node RPC URL (default: http://10.152.0.71:8545)"
    )
    args = parser.parse_args()

    node_url = args.node
    print(f"Connecting to node: {node_url}\n")

    # ---- Connect to Ethereum RPC ----
    w3 = Web3(Web3.HTTPProvider(node_url))

    # ---- Request peer list (requires admin API enabled) ----
    peers = w3.provider.make_request("admin_peers", [])

    # ---- Print raw JSON ----
    print("===== Raw Peers JSON =====")
    print(json.dumps(peers, indent=4))

    print("\n===== Extracted Addresses =====")

    # ---- Extract localAddress and remoteAddress from peers ----
    for p in peers.get("result", []):
        network = p.get("network", {})
        local_addr = network.get("localAddress")
        remote_addr = network.get("remoteAddress")

        print(f"local: {local_addr},   remote: {remote_addr}")


if __name__ == "__main__":
    main()

