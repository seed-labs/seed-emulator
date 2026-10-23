#!/usr/bin/env python3

import json
import subprocess
import argparse
import shutil

from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT = Path(__file__).resolve().parent.parent

SOURCE = PROJECT / "config/generated/testnet-conway-v2"

TARGET = PROJECT / "config/private-testnet-conway-v2"

CLI = PROJECT / "resources/cardano-static/bin/cardano-cli"

GENESIS_FILES = {
    "Byron": "byron-genesis.json",
    "Shelley": "shelley-genesis.json",
    "Alonzo": "alonzo-genesis.json",
    "Conway": "conway-genesis.json",
}


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--minutes",
        type=int,
        default=30
    )

    args = parser.parse_args()

    if args.minutes < 5:
        raise SystemExit(
            "Start time must be at least 5 minutes ahead."
        )

    # Choose a future start time.
    start = (
        datetime.now(timezone.utc)
        + timedelta(minutes=args.minutes)
    ).replace(microsecond=0)

    iso_time = start.strftime("%Y-%m-%dT%H:%M:%SZ")

    unix_time = int(start.timestamp())

    print("New genesis start:", iso_time)

    # Ensure the new blockchain databases are empty.
    db_root = (
        Path.home()
        / "field-project/cardano-data/testnet-conway-113-v2"
    )

    for asn in (150, 151, 152, 153):

        db = db_root / f"as{asn}"

        if db.exists() and any(db.iterdir()):
            raise SystemExit(
                f"Database is not empty: {db}"
            )

    # Read the existing generated genesis files.
    with (SOURCE / "shelley-genesis.json").open() as f:
        shelley = json.load(f)

    with (SOURCE / "byron-genesis.json").open() as f:
        byron = json.load(f)

    shelley["systemStart"] = iso_time
    byron["startTime"] = unix_time

    # Write updated genesis files into our v2 configuration.
    TARGET.mkdir(parents=True, exist_ok=True)

    for era, filename in GENESIS_FILES.items():

        destination = TARGET / filename

        if era == "Shelley":

            with destination.open("w") as f:
                json.dump(shelley, f, indent=2)
                f.write("\n")

        elif era == "Byron":

            with destination.open("w") as f:
                json.dump(byron, f, indent=2)
                f.write("\n")

        else:

            shutil.copy2(
                SOURCE / filename,
                destination
            )

    config_path = TARGET / "config.json"

    with config_path.open() as f:
        config = json.load(f)

    # Calculate hashes of the final genesis files.
    for era, filename in GENESIS_FILES.items():

        genesis_file = TARGET / filename

        if era == "Byron":

            command = [
                str(CLI),
                "byron",
                "genesis",
                "print-genesis-hash",
                "--genesis-json",
                str(genesis_file)
            ]

        else:

            command = [
                str(CLI),
                "hash",
                "genesis-file",
                "--genesis",
                str(genesis_file)
            ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        genesis_hash = result.stdout.strip()

        if len(genesis_hash) != 64:
            raise RuntimeError(
                f"Unexpected {era} genesis hash"
            )

        config[f"{era}GenesisHash"] = genesis_hash

        print(f"{era}: {genesis_hash}")

    with config_path.open("w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print("\nGenesis preparation completed.")
    print("Network magic: 4242")
    print("Start time:", iso_time)


if __name__ == "__main__":
    main()
