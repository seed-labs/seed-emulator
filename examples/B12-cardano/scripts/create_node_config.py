#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

GENESIS = PROJECT / "config/generated/testnet-01"
OUTPUT = PROJECT / "config/private-testnet"
REFERENCE = OUTPUT / "config-reference.json"

IMAGE = "output_hnode_150_host_0:latest"

# Genesis files used by Cardano Node 11.0.1
GENESIS_FILES = {
    "Byron": "byron-genesis.json",
    "Shelley": "shelley-genesis.json",
    "Alonzo": "alonzo-genesis.json",
    "Conway": "conway-genesis.json",
}

with REFERENCE.open() as f:
    config = json.load(f)

# Calculate hashes using Cardano CLI.

# Calculate genesis hashes using Cardano CLI.
for era, filename in GENESIS_FILES.items():

    # Byron uses a different genesis-hashing command.
    if era == "Byron":
        hash_args = [
            "byron",
            "genesis",
            "print-genesis-hash",
            "--genesis-json",
            f"/genesis/{filename}",
        ]

    else:
        hash_args = [
            "hash",
            "genesis-file",
            "--genesis",
            f"/genesis/{filename}",
        ]

    command = [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "cardano-cli",
        "-v",
        f"{GENESIS}:/genesis:ro",
        IMAGE,
    ] + hash_args

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    genesis_hash = result.stdout.strip()

    if len(genesis_hash) != 64:
        raise ValueError(
            f"Unexpected {era} genesis hash: {genesis_hash}"
        )

    config[f"{era}GenesisFile"] = filename
    config[f"{era}GenesisHash"] = genesis_hash

    print(f"{era} genesis hash: {genesis_hash}")

# Use Ouroboros Praos synchronization mode.
config["ConsensusMode"] = "PraosMode"

# Require Cardano testnet network magic.
config["RequiresNetworkMagic"] = "RequiresMagic"

# Keep the Cardano protocol.
config["Protocol"] = "Cardano"

# Initially use the existing reference hard-fork settings.
# Additional hard-fork overrides will be validated separately.

output_file = OUTPUT / "config.json"

with output_file.open("w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")

print(f"\nCreated: {output_file}")
