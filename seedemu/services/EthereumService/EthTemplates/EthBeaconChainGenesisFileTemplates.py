

BEACON_GENESIS = '''\
# Mainnet config

# Extends the mainnet preset
PRESET_BASE: mainnet

# Free-form short name of the network that this configuration applies to - known
# canonical network names include:
# * 'mainnet' - there can be only one
# * 'sepolia' - testnet
# * 'holesky' - testnet
# * 'hoodi' - testnet
# Must match the regex: [a-z0-9\-]
CONFIG_NAME: testnet # needs to exist because of Prysm. Otherwise it conflicts with mainnet genesis

# Transition
# ---------------------------------------------------------------
# Estimated on Sept 15, 2022
TERMINAL_TOTAL_DIFFICULTY: 0
# By default, don't use these params
TERMINAL_BLOCK_HASH: 0x0000000000000000000000000000000000000000000000000000000000000000
TERMINAL_BLOCK_HASH_ACTIVATION_EPOCH: 18446744073709551615



# Genesis
# ---------------------------------------------------------------
# `2**14` (= 16,384)
MIN_GENESIS_ACTIVE_VALIDATOR_COUNT: 4
# 2025-Jun-11 05:51:16 AM UTC
# MIN_GENESIS_TIME: 1749621076
# Mainnet initial fork version, recommend altering for testnets
GENESIS_FORK_VERSION: 0x10000038
# Some seconds
GENESIS_DELAY: 0


# Forking
# ---------------------------------------------------------------
# Some forks are disabled for now:
#  - These may be re-assigned to another fork-version later
#  - Temporarily set to max uint64 value: 2**64 - 1

# Altair
ALTAIR_FORK_VERSION: 0x20000038
ALTAIR_FORK_EPOCH: 0
# Merge
BELLATRIX_FORK_VERSION: 0x30000038
BELLATRIX_FORK_EPOCH: 0
# Capella
CAPELLA_FORK_VERSION: 0x40000038
CAPELLA_FORK_EPOCH: 0
# Deneb
DENEB_FORK_VERSION: 0x50000038
DENEB_FORK_EPOCH: 0
# Electra
ELECTRA_FORK_VERSION: 0x60000038
ELECTRA_FORK_EPOCH: 0
# Fulu
FULU_FORK_VERSION: 0x70000038
FULU_FORK_EPOCH: 18446744073709551615
# EIP7441
EIP7441_FORK_VERSION: 0xa0000000
EIP7441_FORK_EPOCH: 18446744073709551615
# EIP7732
EIP7732_FORK_VERSION: 0x80000038
EIP7732_FORK_EPOCH: 18446744073709551615
# EIP7805
EIP7805_FORK_VERSION: 0x90000038
EIP7805_FORK_EPOCH: 18446744073709551615

# Time parameters
# ---------------------------------------------------------------
# 12 seconds
SECONDS_PER_SLOT: 12
# 14 (estimate from Eth1 mainnet)
SECONDS_PER_ETH1_BLOCK: 14
# 2**8 (= 256) epochs ~27 hours
MIN_VALIDATOR_WITHDRAWABILITY_DELAY: 256
# 2**8 (= 256) epochs ~27 hours
SHARD_COMMITTEE_PERIOD: 256
# 2**11 (= 2,048) Eth1 blocks ~8 hours
ETH1_FOLLOW_DISTANCE: 2048

# Validator cycle
# ---------------------------------------------------------------
# 2**2 (= 4)
INACTIVITY_SCORE_BIAS: 4
# 2**4 (= 16)
INACTIVITY_SCORE_RECOVERY_RATE: 16
# 2**4 * 10**9 (= 16,000,000,000) Gwei
EJECTION_BALANCE: 16000000000
# 2**2 (= 4)
MIN_PER_EPOCH_CHURN_LIMIT: 4
# 2**16 (= 65,536)
CHURN_LIMIT_QUOTIENT: 65536
# [New in Deneb:EIP7514] 2**3 (= 8)
MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT: 8

# Fork choice
# ---------------------------------------------------------------
# 40%
PROPOSER_SCORE_BOOST: 40
# 20%
REORG_HEAD_WEIGHT_THRESHOLD: 20
# 160%
REORG_PARENT_WEIGHT_THRESHOLD: 160
# `2` epochs
REORG_MAX_EPOCHS_SINCE_FINALIZATION: 2


# Deposit contract
# ---------------------------------------------------------------
DEPOSIT_CHAIN_ID: "{chain_id}"
DEPOSIT_NETWORK_ID: "{chain_id}"
NETWORK_ID: "{chain_id}"
DEPOSIT_CONTRACT_ADDRESS: 0x00000000219ab540356cBB839Cbe05303d7705Fa

# Networking
# ---------------------------------------------------------------
# `10 * 2**20` (= 10485760, 10 MiB)
MAX_PAYLOAD_SIZE: 10485760
# `2**10` (= 1024)
MAX_REQUEST_BLOCKS: 1024
# `2**8` (= 256)
EPOCHS_PER_SUBNET_SUBSCRIPTION: 256
# `MIN_VALIDATOR_WITHDRAWABILITY_DELAY + CHURN_LIMIT_QUOTIENT // 2` (= 33024, ~5 months)
MIN_EPOCHS_FOR_BLOCK_REQUESTS: 33024
# 5s
TTFB_TIMEOUT: 5
# 10s
RESP_TIMEOUT: 10
ATTESTATION_PROPAGATION_SLOT_RANGE: 32
# 500ms
MAXIMUM_GOSSIP_CLOCK_DISPARITY: 500
MESSAGE_DOMAIN_INVALID_SNAPPY: 0x00000000
MESSAGE_DOMAIN_VALID_SNAPPY: 0x01000000
# 2 subnets per node
SUBNETS_PER_NODE: 2
# 2**8 (= 64)
ATTESTATION_SUBNET_COUNT: 64
ATTESTATION_SUBNET_EXTRA_BITS: 0
# ceillog2(ATTESTATION_SUBNET_COUNT) + ATTESTATION_SUBNET_EXTRA_BITS
ATTESTATION_SUBNET_PREFIX_BITS: 6

# Deneb
# `2**7` (=128)
MAX_REQUEST_BLOCKS_DENEB: 128
# `2**12` (= 4096 epochs, ~18 days)
MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS: 4096
# `6`
BLOB_SIDECAR_SUBNET_COUNT: 6
## `uint64(6)`
MAX_BLOBS_PER_BLOCK: 6
# MAX_REQUEST_BLOCKS_DENEB * MAX_BLOBS_PER_BLOCK
MAX_REQUEST_BLOB_SIDECARS: 768

# Electra
# 2**7 * 10**9 (= 128,000,000,000)
MIN_PER_EPOCH_CHURN_LIMIT_ELECTRA: 128000000000
# 2**8 * 10**9 (= 256,000,000,000)
MAX_PER_EPOCH_ACTIVATION_EXIT_CHURN_LIMIT: 256000000000
# `9`
BLOB_SIDECAR_SUBNET_COUNT_ELECTRA: 9
# `uint64(9)`
MAX_BLOBS_PER_BLOCK_ELECTRA: 9
# MAX_REQUEST_BLOCKS_DENEB * MAX_BLOBS_PER_BLOCK_ELECTRA
MAX_REQUEST_BLOB_SIDECARS_ELECTRA: 1152

# Fulu
NUMBER_OF_COLUMNS: 128
NUMBER_OF_CUSTODY_GROUPS: 128
DATA_COLUMN_SIDECAR_SUBNET_COUNT: 128
MAX_REQUEST_DATA_COLUMN_SIDECARS: 16384
SAMPLES_PER_SLOT: 8
CUSTODY_REQUIREMENT: 4
VALIDATOR_CUSTODY_REQUIREMENT: 8
BALANCE_PER_ADDITIONAL_CUSTODY_GROUP: 32000000000
MIN_EPOCHS_FOR_DATA_COLUMN_SIDECARS_REQUESTS: 4096

# EIP7441
EPOCHS_PER_SHUFFLING_PHASE: 256
PROPOSER_SELECTION_GAP: 2

# EIP7732
MAX_REQUEST_PAYLOADS: 128
PROPOSER_SCORE_BOOST_EIP7732: 20

# EIP7805
ATTESTATION_DEADLINE: 4
PROPOSER_INCLUSION_LIST_CUT_OFF: 11
VIEW_FREEZE_DEADLINE: 9
# 2**4 (= 16)
MAX_REQUEST_INCLUSION_LIST: 16
# 2**13 (= 8192)
MAX_BYTES_PER_INCLUSION_LIST: 8192
TARGET_COMMITTEE_SIZE: "{target_committee_size}"
TARGET_AGGREGATORS_PER_COMMITTEE: "{target_aggregator_per_committee}"
'''

BEACON_BOOTNODE_HTTP_SERVER = '''\
from http.server import HTTPServer, BaseHTTPRequestHandler

eth_id = 0

class SeedHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = open("/local-testnet/{{}}.tar.gz".format(self.path), "rb")
        self.wfile.write(response.read())
        response.close()

httpd = HTTPServer(('0.0.0.0', {beacon_bootnode_http_port}), SeedHTTPRequestHandler)
httpd.serve_forever()
'''

BEACON_MNEMONIC_YAML = '''\
- mnemonic: "{validator_mnemonic}"  # a 24 word BIP 39 mnemonic
  count: {validator_count} # amount of validators
'''

PREPARE_RESOURCE_TO_SEND = '''\
#!/bin/bash
tar -czvf /local-testnet/testnet.tar.gz /local-testnet/testnet
'''
