#!/usr/bin/env python3

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "data/performance-test/results"
METADATA = BASE / "data/metadata-test/sensor_hash_002.json"

FIELDS = [
    "sequence",
    "type",
    "run_id",
    "status",
    "txhash",
    "cbor_size_bytes",
    "fee_lovelace",
    "submit_seconds",
    "confirmation_seconds",
    "confirmed_nodes_count",
]


def cbor_size(path):
    """Calculate actual serialized transaction size."""
    envelope = json.loads(path.read_text())
    return len(bytes.fromhex(envelope["cborHex"]))


def execute_transaction(sequence, with_metadata):

    tx_type = "metadata" if with_metadata else "baseline"

    print(f"\n{'=' * 60}", flush=True)
    print(f"Transaction {sequence}: {tx_type}", flush=True)
    print(f"{'=' * 60}", flush=True)

    command = [
        sys.executable,
        str(BASE / "cardano_transaction.py"),
        "--node", "150",
        "--from", "1",
        "--to", "2",
        "--amount", "2",
        "--timeout", "180",
        "--execute",
    ]

    if with_metadata:
        command.extend(["--metadata", str(METADATA)])

    result = subprocess.run(
        command,
        cwd=BASE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout, flush=True)

    # Find the result file reported by the transaction script.
    match = re.search(
        r"Recorded:\s+(.+?/result\.json)\s+and\s+",
        result.stdout,
    )

    if not match:
        raise RuntimeError(
            f"Transaction {sequence}: result file not found"
        )

    result_path = Path(match.group(1))

    if not result_path.is_absolute():
        result_path = BASE / result_path

    record = json.loads(result_path.read_text())

    if result.returncode != 0:
        raise RuntimeError(
            f"Transaction {sequence} exited with code "
            f"{result.returncode}"
        )

    if record["status"] != "CONFIRMED_ALL":
        raise RuntimeError(
            f"Transaction {sequence}: {record['status']}"
        )

    signed_file = result_path.parent / "tx.signed"

    return {
        "sequence": sequence,
        "type": tx_type,
        "run_id": record["run_id"],
        "status": record["status"],
        "txhash": record["txhash"],
        "cbor_size_bytes": cbor_size(signed_file),
        "fee_lovelace": record["fee_lovelace_estimated"],
        "submit_seconds": record["submit_seconds"],
        "confirmation_seconds": record["confirmation_seconds"],
        "confirmed_nodes_count": len(
            record.get("confirmed_nodes", {})
        ),
    }


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pairs",
        type=int,
        default=1,
        help="Number of baseline/metadata pairs",
    )
    args = parser.parse_args()

    if not 1 <= args.pairs <= 10:
        parser.error("--pairs must be between 1 and 10")

    if not METADATA.is_file():
        parser.error(f"Metadata file missing: {METADATA}")

    RESULTS.mkdir(parents=True, exist_ok=True)

    experiment_id = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    output = RESULTS / f"benchmark_{experiment_id}.csv"

    with output.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for sequence in range(1, args.pairs * 2 + 1):

            with_metadata = sequence % 2 == 0

            try:
                record = execute_transaction(
                    sequence,
                    with_metadata,
                )

            except Exception as error:
                print(f"\nBENCHMARK STOPPED: {error}")
                print(f"Completed results: {output}")
                return 1

            writer.writerow(record)
            f.flush()

    print("\nBENCHMARK COMPLETED")
    print(f"Results saved to: {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
