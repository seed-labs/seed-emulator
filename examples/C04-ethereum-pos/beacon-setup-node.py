#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os
import sys

# Change LCLI_BIN_PATH 
LCLI_BIN_PATH = "/home/won/.cargo/bin/lcli"

# Initialize the emulator and layers
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
web     = WebService()

###############################################################################
# Create and set up AS-150

# Create an autonomous system 
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0')

# Create a host called beacon-setup-node and connect it to a network
beacon_setup_node = as150.createHost('beacon-setup-node').joinNetwork('net0', address = '10.150.0.99')

n = len(sys.argv)
if n < 4:
   print("Please provide 1) terminal_total_difficulty 2) validator_ids 3) bootnode_ip")
   print("ex) ./beacon-setup-node.py 50 '2,4,5,6' '10.150.0.71' ")
   exit(0)
hosts_total = int(sys.argv[1])

TERMINAL_TOTAL_DIFFICULTY = int(sys.argv[1])
VALIDATOR_IDS = list(map(str,sys.argv[2].split(",")))

VALIDATOR_COUNT = len(VALIDATOR_IDS)
BOOTNODE_IP = sys.argv[3]
GETHNODE_IP = BOOTNODE_IP
BEACON_BOOTNODE_HTTP_PORT = 8090

# Setup Beacon 
BEACON_GENESIS = '''\
CONFIG_NAME: mainnet
PRESET_BASE: mainnet
TERMINAL_TOTAL_DIFFICULTY: "{terminal_total_difficulty}"
TERMINAL_BLOCK_HASH: "0x0000000000000000000000000000000000000000000000000000000000000000"
TERMINAL_BLOCK_HASH_ACTIVATION_EPOCH: "18446744073709551615"
SAFE_SLOTS_TO_IMPORT_OPTIMISTICALLY: "128"
MIN_GENESIS_ACTIVE_VALIDATOR_COUNT: "1"
GENESIS_FORK_VERSION: "0x42424242"
GENESIS_DELAY: "0"
ALTAIR_FORK_VERSION: "0x01000000"
ALTAIR_FORK_EPOCH: "0"
BELLATRIX_FORK_VERSION: "0x02000000"
BELLATRIX_FORK_EPOCH: "1"
EPOCHS_PER_ETH1_VOTING_PERIOD: "1"
SECONDS_PER_SLOT: "3"
SECONDS_PER_ETH1_BLOCK: "15"
MIN_VALIDATOR_WITHDRAWABILITY_DELAY: "256"
SHARD_COMMITTEE_PERIOD: "256"
ETH1_FOLLOW_DISTANCE: "1"
INACTIVITY_SCORE_BIAS: "4"
INACTIVITY_SCORE_RECOVERY_RATE: "16"
EJECTION_BALANCE: "16000000000"
MIN_PER_EPOCH_CHURN_LIMIT: "4"
CHURN_LIMIT_QUOTIENT: "65536"
PROPOSER_SCORE_BOOST: "40"
DEPOSIT_CHAIN_ID: "10"
DEPOSIT_NETWORK_ID: "10"
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

PREPARE_RESOURCE_TO_SEND = '''\
#!/bin/bash
let i=0
while read -r ethId; do {
    let i++
    mv /local-testnet/node_$i /local-testnet/eth-$ethId
    tar -czvf /local-testnet/eth-$ethId.tar.gz /local-testnet/eth-$ethId
}; done < /tmp/validator-ids
tar -czvf /local-testnet/testnet.tar.gz /local-testnet/testnet
tar -czvf /local-testnet/bootnode.tar.gz /local-testnet/bootnode
'''

DEPLOY_CONTRACT = '''\
let count=0
ok=true
until curl -sHf http://{geth_node_ip}:8545 > /dev/null; do {{
echo "eth: geth not ready, waiting..."
sleep 3
let count++
[ $count -gt 60 ] && {{
    echo "eth: geth connection failed too many times, skipping."
    ok=false
    break
}}
}}; done
($ok) && {{
lcli deploy-deposit-contract --eth1-http http://{geth_node_ip}:8545 --confirmations 1 --validator-count {validator_count} > contract_address.txt
}}
'''

beacon_setup_node.addBuildCommand('apt-get update && apt-get install -y --no-install-recommends software-properties-common')
beacon_setup_node.importFile(LCLI_BIN_PATH, "/usr/bin/lcli")
beacon_setup_node.appendStartCommand("chmod +x /usr/bin/lcli")
beacon_setup_node.appendStartCommand('lcli generate-bootnode-enr --ip {} --udp-port 30305 --tcp-port 30305 --genesis-fork-version 0x42424242 --output-dir /local-testnet/bootnode'.format(BOOTNODE_IP))
beacon_setup_node.setFile("/tmp/config.yaml", BEACON_GENESIS.format(terminal_total_difficulty=TERMINAL_TOTAL_DIFFICULTY))
beacon_setup_node.setFile("/tmp/validator-ids", "\n".join(VALIDATOR_IDS))
beacon_setup_node.appendStartCommand('mkdir /local-testnet/testnet')
beacon_setup_node.appendStartCommand('bootnode_enr=`cat /local-testnet/bootnode/enr.dat`')
beacon_setup_node.appendStartCommand('echo "- $bootnode_enr" > /local-testnet/testnet/boot_enr.yaml')
beacon_setup_node.appendStartCommand('cp /tmp/config.yaml /local-testnet/testnet/config.yaml')
beacon_setup_node.appendStartCommand(DEPLOY_CONTRACT.format(geth_node_ip=GETHNODE_IP, validator_count = VALIDATOR_COUNT))
beacon_setup_node.appendStartCommand('lcli insecure-validators --count {validator_count} --base-dir /local-testnet/ --node-count {validator_count}'.format(validator_count = VALIDATOR_COUNT))
beacon_setup_node.appendStartCommand('GENESIS_TIME=`date +%s`')
beacon_setup_node.appendStartCommand('''CONTRACT_ADDRESS=`head -1 contract_address.txt | cut -d '"' -f 2`''')
beacon_setup_node.appendStartCommand('''echo 'DEPOSIT_CONTRACT_ADDRESS: "'$CONTRACT_ADDRESS'"' >> /local-testnet/testnet/config.yaml''')
beacon_setup_node.appendStartCommand('''echo 'MIN_GENESIS_TIME: "'$GENESIS_TIME'"' >> /local-testnet/testnet/config.yaml''')
beacon_setup_node.appendStartCommand('''echo '3' > /local-testnet/testnet/deploy_block.txt''')
beacon_setup_node.appendStartCommand('''lcli interop-genesis --spec mainnet --genesis-time $GENESIS_TIME --testnet-dir /local-testnet/testnet {validator_count}'''.format(validator_count = VALIDATOR_COUNT))
beacon_setup_node.setFile("/tmp/prepare_resource.sh", PREPARE_RESOURCE_TO_SEND)
beacon_setup_node.appendStartCommand("chmod +x /tmp/prepare_resource.sh")
beacon_setup_node.appendStartCommand("/tmp/prepare_resource.sh")
beacon_setup_node.setFile('/local-testnet/beacon_bootnode_http_server.py', BEACON_BOOTNODE_HTTP_SERVER.format(beacon_bootnode_http_port=BEACON_BOOTNODE_HTTP_PORT))
beacon_setup_node.appendStartCommand('python3 /local-testnet/beacon_bootnode_http_server.py', True)


###############################################################################
# Rendering 

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()

###############################################################################
# Compilation
docker = Docker()

DOCKER_COMPOSE = '''\
version: "3.4"
services:
{}
networks:
    net_150_net0:
        name: output_net_150_net0
        external: true
'''
os.system('mkdir beacon-node')
f = open("./beacon-node/docker-compose.yml", 'w')
f.write(DOCKER_COMPOSE.format(docker._compileNode(beacon_setup_node)))
f.close()
os.system('mv hnode_150_beacon-setup-node beacon-node')


