# B11 - Cardano Blockchain in SEED Emulator

## 1. Project Overview

This project implements a private Cardano blockchain
network using SEED Emulator.

The implementation builds on the networking architecture
used in the B06-blockchain example.

The objective is to investigate Cardano networking,
consensus, block production, and synchronization
across different autonomous systems.

## 2. Environment

- Ubuntu Linux
- SEED Emulator
- Docker and Docker Compose
- Python 3.8
- Cardano Node 11.0.1
- Cardano CLI 11.0.0.0

The validated deployment uses AMD64 binaries.

## 3. Network Architecture

Four Cardano nodes are distributed across
four autonomous systems.

AS150 - Cardano Node 1 - Genesis Delegate 1
AS151 - Cardano Node 2 - Genesis Delegate 2
AS152 - Cardano Node 3 - Genesis Delegate 3
AS153 - Cardano Node 4 - Relay

Node IP addresses:

AS150: 10.150.0.71
AS151: 10.151.0.71
AS152: 10.152.0.71
AS153: 10.153.0.71

Cardano P2P port: 3001
Network magic: 4242

## 4. Consensus Configuration

The private blockchain currently operates
in the Alonzo era.

Genesis configuration:

- Decentralisation parameter: 1
- Active slots coefficient: 0.05
- Slot length: 1 second
- Epoch length: 432000 slots
- Genesis delegates: 3
- Initial stake pools: 1

The three genesis delegates participate in
the bootstrap block-production mechanism.

This configuration does not demonstrate
fully decentralized stake-pool production.

## 5. Experimental Results

The following results were verified:

1. Successful startup of four Cardano nodes.
2. P2P communication across autonomous systems.
3. Successful Cardano protocol handshakes.
4. TCP connectivity on port 3001.
5. Blockchain synchronization across all four nodes.
6. Successful block forging by three genesis delegates.
7. Matching blockchain block hashes on all four nodes.
8. Verification of distinct KES, VRF, and
   operational certificate files.

## 6. Project Files

blockchain.py
    Generates the SEED Emulator network
    and configures the Cardano nodes.

scripts/create_topologies.py
    Generates Cardano P2P topology files.

scripts/create_node_config.py
    Generates Cardano node configuration
    from genesis files.

config/private-testnet/
    Contains private-testnet configuration
    and genesis JSON files.

## 7. Dependencies

Cardano Node and Cardano CLI binaries
are expected at:

resources/cardano-static/bin/cardano-node
resources/cardano-static/bin/cardano-cli

The binaries are not included in the
source-code archive.

The original experiment uses private
genesis-delegate credentials.

These credentials are also excluded
from the shared source archive.

## 8. Reproducibility

This package is intended for source-code
review and examination of the implementation.

It is not yet a fully self-contained
deployment package.

Reproducing block production requires
generating and configuring valid genesis
credentials and operational certificates.

The supplied genesis configuration belongs
to the original experimental network.

A fresh deployment should create an
appropriate new genesis configuration.

## 9. Future Experiments

Planned experiments include:

- Cardano transaction submission
- Block propagation measurements
- Network partition experiments
- Consensus behavior under network delays
- Stake-pool-based block production
- Conway-era experiments
