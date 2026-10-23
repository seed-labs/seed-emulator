#!/usr/bin/env python3

import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

NODE = "as150h-Cardano-Node-1-10.150.0.71"

DURATION = 300
INTERVAL = 2

results = Path("data/performance-test/results")
results.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime(
    "%Y%m%dT%H%M%SZ"
)

filename = results / f"blocks_{timestamp}.csv"


def query_tip():
    command = [
        "docker", "exec", NODE,
        "cardano-cli", "query", "tip",
        "--testnet-magic", "4242",
        "--socket-path", "/cardano/node.socket",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )

    return json.loads(result.stdout)


print("Monitoring Cardano block production...")
print("Node:", NODE)
print("Duration:", DURATION, "seconds")
print("Output:", filename)

previous_hash = None
previous_slot = None

with filename.open("w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "timestamp_utc",
        "block",
        "slot",
        "block_hash",
        "slot_interval",
    ])

    start = time.monotonic()

    while time.monotonic() - start < DURATION:

        tip = query_tip()

        block_hash = tip.get("hash")
        block = tip.get("block")
        slot = tip.get("slot")

        if block_hash and block_hash != previous_hash:

            slot_interval = ""

            if previous_slot is not None:
                slot_interval = slot - previous_slot

            observed_at = datetime.now(
                timezone.utc
            ).isoformat()

            writer.writerow([
                observed_at,
                block,
                slot,
                block_hash,
                slot_interval,
            ])

            f.flush()

            print(
                f"Block: {block} | "
                f"Slot: {slot} | "
                f"Interval: {slot_interval}"
            )

            previous_hash = block_hash
            previous_slot = slot

        time.sleep(INTERVAL)
print("\nMonitoring completed.")
print("Results:", filename)
