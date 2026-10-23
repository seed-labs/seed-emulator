#!/usr/bin/env python3

from pathlib import Path
import sys

from seedemu import *

# ==================================================
# B11 - Cardano Blockchain
# SEED Emulator Field Project
#
# Four Cardano nodes across four autonomous systems.
#
# AS150 -> Cardano Node 1 (Genesis Delegate / Block Producer)
# AS151 -> Cardano Node 2 (Genesis Delegate / Block Producer)
# AS152 -> Cardano Node 3 (Genesis Delegate / Block Producer)
# AS153 -> Cardano Node 4 (Relay)
#
# Cardano Node version: 11.0.1
# Network Magic: 4242
# P2P Port: 3001
# ==================================================


# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

CARDANO_NODE = (
    PROJECT_DIR / "resources/cardano-static/bin/cardano-node"
)

CARDANO_CLI = (
    PROJECT_DIR / "resources/cardano-static/bin/cardano-cli"
)

CONFIG_DIR = (
    PROJECT_DIR / "config/private-testnet-conway-v2"
)

OUTPUT_DIR = PROJECT_DIR / "output"


# --------------------------------------------------
# 2. Verify required files
# --------------------------------------------------

genesis_files = [
    "byron-genesis.json",
    "shelley-genesis.json",
    "alonzo-genesis.json",
    "conway-genesis.json",
]

required_files = [
    CARDANO_NODE,
    CARDANO_CLI,
    CONFIG_DIR / "config.json",
]

for filename in genesis_files:
    required_files.append(CONFIG_DIR / filename)

for index in range(1, 5):
    required_files.append(
        CONFIG_DIR / f"topology-node{index}.json"
    )

for filepath in required_files:

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Required file missing: {filepath}"
        )

print("All required Cardano files verified.")


# --------------------------------------------------
# 3. Platform configuration
# --------------------------------------------------

platform = sys.argv[1] if len(sys.argv) > 1 else "amd"

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64,
}

if platform not in platform_mapping:
    raise SystemExit(
        "Usage: python3 blockchain.py [amd|arm]"
    )

# The downloaded static Cardano binaries are AMD64.
# ARM requires separate ARM-compatible binaries.

if platform == "arm":
    raise SystemExit(
        "The current Cardano binaries are AMD64. "
        "Install ARM64-compatible binaries before "
        "compiling for ARM."
    )

print(f"Selected platform: {platform}")


# --------------------------------------------------
# 4. Create SEED Emulator infrastructure
# --------------------------------------------------

emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

base = emu.getLayer("Base")

# We use the same AS structure as the B06 example.

cardano_ases = [
    150,
    151,
    152,
    153,
]

print("SEED Emulator base network created.")


# --------------------------------------------------
# 5. Configure Cardano hosts
# --------------------------------------------------

for index, asn in enumerate(cardano_ases, start=1):

    # Get the host belonging to this autonomous system.

    host = base.getAutonomousSystem(asn).getHost(
        "host_0"
    )

    # Assign a descriptive name.

    host.setDisplayName(
        f"Cardano-Node-{index}"
    )

    # ----------------------------------------------
    # 5.1 Install networking utilities
    # ----------------------------------------------

    host.addSoftware("iputils-ping")
    host.addSoftware("netcat-openbsd")
    host.addSoftware("tcpdump")

    # ----------------------------------------------
    # 5.2 Import Cardano executables
    # ----------------------------------------------

    host.importFile(
        str(CARDANO_NODE),
        "/usr/local/bin/cardano-node"
    )

    host.importFile(
        str(CARDANO_CLI),
        "/usr/local/bin/cardano-cli"
    )

    # ----------------------------------------------
    # 5.3 Import private node configuration
    # ----------------------------------------------

    host.importFile(
        str(CONFIG_DIR / "config.json"),
        "/cardano/config.json"
    )

    # ----------------------------------------------
    # 5.4 Import private genesis files
    # ---------------------------------------------- 

    for filename in genesis_files:

        host.importFile(
            str(CONFIG_DIR / filename),
            f"/cardano/{filename}"
        )

    # ----------------------------------------------
    # 5.5 Import individual P2P topology
    # ----------------------------------------------

    topology_file = (
        CONFIG_DIR / f"topology-node{index}.json"
    )

    host.importFile(
        str(topology_file),
        "/cardano/topology.json"
    )
    
    # ----------------------------------------------
    # 5.6 Import block-producer credentials
    # ----------------------------------------------

    producer_options = ""

    if index in (1, 2, 3):

        pool_dir = (
            PROJECT_DIR
            / "config"
            / "generated"
            / "testnet-conway-v2"
            / "pools-keys"
            / f"pool{index}"
    )

        for filename in ("kes.skey", "vrf.skey", "opcert.cert"):

            credential_file = pool_dir / filename

            assert credential_file.is_file(), (
                f"Missing producer credential: {credential_file}"
            )

            host.importFile(
                str(credential_file),
                f"/cardano/producer/{filename}"
            )

        producer_options = (
            " --shelley-kes-key /cardano/producer/kes.skey"
            " --shelley-vrf-key /cardano/producer/vrf.skey"
            " --shelley-operational-certificate "
            "/cardano/producer/opcert.cert"
        )

    # ----------------------------------------------
    # 5.7 Persistent blockchain database
    # ----------------------------------------------

    # Each node receives a separate Docker volume.
    #
    # This prevents the loss of blockchain data
    # when containers are recreated.
   
    # Store blockchain databases in the current
    # user's home directory.

    DATABASE_DIR = (
        Path.home()
        / "field-project"
        / "cardano-data"
        / "testnet-conway-113-v2"
        / f"as{asn}"
    )

    # Create the directory if it does not exist.
    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Map host database storage into the container.
    host.addSharedFolder(
        "/cardano/db",
        str(DATABASE_DIR)
    )

    # ----------------------------------------------
    # 5.8 Ensure executables are executable
    # ----------------------------------------------

    # PRESERVED AS REQUESTED.
    #
    # This command runs during container startup.
    # It is retained even though we also configure
    # permissions during Docker image construction.

    host.insertStartCommand(
        0,
        "chmod +x /usr/local/bin/cardano-node "
        "/usr/local/bin/cardano-cli"
    )
    
    # Restrict producer credentials before starting Cardano.
    if index in (1, 2, 3):
        host.appendStartCommand(
            "chmod 700 /cardano/producer && "
            "chmod 600 /cardano/producer/kes.skey "
            "/cardano/producer/vrf.skey && "
            "chmod 644 /cardano/producer/opcert.cert"
    )

    # ----------------------------------------------
    # 5.9 Start Cardano after SEED configuration
    # ----------------------------------------------

    # isPostConfigCommand=True:
    #
    # Cardano starts after SEED performs its
    # basic network configuration.
    #
    # fork=True:
    #
    # Cardano runs in the background.

    # ----------------------------------------------
    # 5.9 Start Cardano with optional producer credentials
    # ----------------------------------------------

    host.appendStartCommand(
    	"mkdir -p /cardano/db && "
    	"cardano-node run "
    	"--config /cardano/config.json "
    	"--topology /cardano/topology.json "
    	"--database-path /cardano/db "
    	"--socket-path /cardano/node.socket "
    	"--host-addr 0.0.0.0 "
    	"--port 3001"
    	+ producer_options
    	+ " > /var/log/cardano-node.log 2>&1",
    	fork=True,
    )

    # ----------------------------------------------
    # 5.10 Display configuration summary
    # ----------------------------------------------

    print(
        f"Configured Cardano Node {index} "
        f"in AS{asn}"
    )


# --------------------------------------------------
# 6. Render SEED Emulator
# --------------------------------------------------

print("Rendering SEED Emulator network...")

emu.render()

print("SEED Emulator rendering completed.")


# --------------------------------------------------
# 7. Configure Docker compiler
# --------------------------------------------------

docker = Docker(
    etherViewEnabled=True,
    platform=platform_mapping[platform],
)


# --------------------------------------------------
# 8. Compile SEED network
# --------------------------------------------------

print("Compiling Docker infrastructure...")

emu.compile(
    docker,
    str(OUTPUT_DIR),
    override=True
)

print("Docker infrastructure generated.")

# --------------------------------------------------
# 9. Add shared capture directory to SEED nodes
# --------------------------------------------------

import re

CAPTURES_DIR = (
    Path.home()
    / "field-project"
    / "captures"
)

CAPTURES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

compose_file = OUTPUT_DIR / "docker-compose.yml"

capture_mount = (
    f"{CAPTURES_DIR}:/captures"
)

lines = compose_file.read_text().splitlines(
    keepends=True
)

target_re = re.compile(
    r"^    ((?:hnode_|rnode_|rs_)[^:]+):\s*$"
)

service_re = re.compile(
    r"^    [A-Za-z0-9_.-]+:\s*$"
)

targets = []

for i, line in enumerate(lines):

    if target_re.match(line):

        end = len(lines)

        for j in range(i + 1, len(lines)):

            if service_re.match(lines[j]):
                end = j
                break

        targets.append((i, end))


for start, end in reversed(targets):

    block = lines[start:end]

    # Avoid duplicate /captures mounts.
    if any(
        "/captures" in line
        for line in block
    ):
        continue

    volumes_index = None

    # Find an existing volumes: section.
    for offset, line in enumerate(block):

        if line.startswith("        volumes:"):
            volumes_index = start + offset
            break

    if volumes_index is not None:

        # Find the end of the complete volumes section.
        # This keeps long-form mounts such as:
        #
        # - type: bind
        #   source: ...
        #   target: ...
        #
        # together.

        insert_index = end

        for pos in range(
            volumes_index + 1,
            end
        ):

            current = lines[pos]

            # A new service-level key such as:
            # labels:
            # networks:
            # command:
            if (
                current.startswith("        ")
                and not current.startswith("            ")
                and current.strip()
            ):
                insert_index = pos
                break

        lines[
            insert_index:insert_index
        ] = [
            f"            - {capture_mount}\n"
        ]

    else:

        # No existing volumes section.
        # Create one before networks or labels.

        insert_index = end

        for pos in range(
            start + 1,
            end
        ):

            if (
                lines[pos].startswith("        networks:")
                or lines[pos].startswith("        labels:")
            ):
                insert_index = pos
                break

        lines[
            insert_index:insert_index
        ] = [
            "        volumes:\n",
            f"            - {capture_mount}\n",
        ]


compose_file.write_text(
    "".join(lines)
)

print(
    "Added /captures bind mount to "
    "SEED hosts, routers, and route servers."
)

    # --------------------------------------------------
    # 9. Add shared capture directory to SEED nodes
    # --------------------------------------------------

import re

CAPTURES_DIR = (
    Path.home()
    / "field-project"
    / "captures"
)

CAPTURES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

compose_file = OUTPUT_DIR / "docker-compose.yml"

capture_mount = (
    f"{CAPTURES_DIR}:/captures"
)

lines = compose_file.read_text().splitlines(
    keepends=True
)

target_re = re.compile(
    r"^    ((?:hnode_|rnode_|rs_)[^:]+):\s*$"
)

service_re = re.compile(
    r"^    [A-Za-z0-9_.-]+:\s*$"
)

targets = []

for i, line in enumerate(lines):

    if target_re.match(line):

        end = len(lines)

        for j in range(i + 1, len(lines)):

            if service_re.match(lines[j]):
                end = j
                break

        targets.append((i, end))


for start, end in reversed(targets):

    block = lines[start:end]

    # Avoid duplicate /captures mounts.
    if any(
        "/captures" in line
        for line in block
    ):
        continue

    volumes_index = None

    # Find an existing volumes: section.
    for offset, line in enumerate(block):

        if line.startswith("        volumes:"):
            volumes_index = start + offset
            break

    if volumes_index is not None:

        # Find the end of the complete volumes section.
        # This keeps long-form mounts such as:
        #
        # - type: bind
        #   source: ...
        #   target: ...
        #
        # together.

        insert_index = end

        for pos in range(
            volumes_index + 1,
            end
        ):

            current = lines[pos]

            # A new service-level key such as:
            # labels:
            # networks:
            # command:
            if (
                current.startswith("        ")
                and not current.startswith("            ")
                and current.strip()
            ):
                insert_index = pos
                break

        lines[
            insert_index:insert_index
        ] = [
            f"            - {capture_mount}\n"
        ]

    else:

        # No existing volumes section.
        # Create one before networks or labels.

        insert_index = end

        for pos in range(
            start + 1,
            end
        ):

            if (
                lines[pos].startswith("        networks:")
                or lines[pos].startswith("        labels:")
            ):
                insert_index = pos
                break

        lines[
            insert_index:insert_index
        ] = [
            "        volumes:\n",
            f"            - {capture_mount}\n",
        ]


compose_file.write_text(
    "".join(lines)
)

print(
    "Added /captures bind mount to "
    "SEED hosts, routers, and route servers."
)

# --------------------------------------------------
# 10. Ensure executable permissions in Dockerfiles
# --------------------------------------------------

# The SEED importFile() operation copies binaries
# into Docker images.
#
# Their executable permissions may not be retained.
#
# We therefore append a Docker RUN chmod command
# to each generated Cardano Dockerfile.
#
# This executes at image-build time, after COPY.

chmod_command = (
    "RUN chmod 755 "
    "/usr/local/bin/cardano-node "
    "/usr/local/bin/cardano-cli"
)

for asn in cardano_ases:

    dockerfile = (
        OUTPUT_DIR
        / f"hnode_{asn}_host_0"
        / "Dockerfile"
    )

    if not dockerfile.is_file():
        raise FileNotFoundError(
            f"Generated Dockerfile missing: {dockerfile}"
        )

    content = dockerfile.read_text()

    # Avoid adding duplicate instructions.

    if chmod_command not in content:

        content += (
            "\n"
            "# Ensure Cardano executables are runnable\n"
            + chmod_command
            + "\n"
        )

        dockerfile.write_text(content)

    print(
        f"Cardano executable permissions "
        f"configured for AS{asn}"
    )


# --------------------------------------------------
# 11. Completion summary
# --------------------------------------------------

print()
print("=" * 55)
print("B12 - CARDANO BLOCKCHAIN")
print("=" * 55)

print("SEED Emulator network compiled successfully.")
print()

print("Configured nodes:")

for index, asn in enumerate(cardano_ases, start=1):

    print(
        f"  Cardano Node {index} "
        f"-> AS{asn}"
    )

print()
print("Cardano version: 11.0.1")
print("Network magic: 4242")
print("Cardano P2P port: 3001")

print()
print("Configuration:")
print("  Private genesis files imported")
print("  Individual P2P topology files imported")
print("  Persistent host database bind mounts configured")
print("  Executable permissions configured")
print("  Cardano startup commands generated")

print()
print("Important:")
print("  Docker images have not yet been built.")
print("  Cardano nodes are not yet running.")
print("  Producer credentials configured for Nodes 1–3.")
print("  Node 4 is configured as a relay.")
print("  Block production must be verified after startup.")

print()
print("Next step:")
print("  Verify generated Dockerfiles and Compose volumes.")

print("=" * 55)
