#!/usr/bin/env python3

import json
from pathlib import Path

OUTPUT = Path("config/private-testnet")
OUTPUT.mkdir(parents=True, exist_ok=True)

NODES = {
    1: "10.150.0.71",
    2: "10.151.0.71",
    3: "10.152.0.71",
    4: "10.153.0.71",
}

PORT = 3001

for node_id, local_ip in NODES.items():

    # Each node connects to all other Cardano nodes.
    peers = [
        {
            "address": ip,
            "port": PORT
        }
        for peer_id, ip in NODES.items()
        if peer_id != node_id
    ]

    topology = {
        "bootstrapPeers": None,
        "localRoots": [
            {
                "accessPoints": peers,
                "advertise": False,
                "trustable": True,
                "valency": len(peers)
            }
        ],
        "publicRoots": [],
        "useLedgerAfterSlot": -1
    }

    path = OUTPUT / f"topology-node{node_id}.json"

    with path.open("w") as f:
        json.dump(topology, f, indent=2)

    print(f"Created {path}")
