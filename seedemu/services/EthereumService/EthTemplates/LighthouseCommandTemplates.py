

LIGHTHOUSE_BN_CMD = """lighthouse --debug-level info bn --datadir /tmp/local-testnet/eth-{eth_id} --testnet-dir /tmp/local-testnet/testnet --enable-private-discovery --staking --enr-address {ip_address}  --enr-udp-port 9000 --enr-tcp-port 9000 --port 9000 --http-address {ip_address} --http-port 8000 --http-allow-origin "*" --disable-packet-filter --target-peers {target_peers} --execution-endpoint http://localhost:8551 --execution-jwt /tmp/jwt.hex &"""

LIGHTHOUSE_VC_CMD = """lighthouse --debug-level info vc --datadir /tmp/local-testnet/eth-{eth_id} --testnet-dir /tmp/local-testnet/testnet --init-slashing-protection --beacon-nodes http://{ip_address}:8000 --suggested-fee-recipient {acct_address} --http --http-address 0.0.0.0 --http-allow-origin "*" --unencrypted-http-transport &"""

LIGHTHOUSE_WALLET_CREATE_CMD = """lighthouse account_manager wallet create --testnet-dir /tmp/local-testnet/testnet --datadir /tmp/local-testnet/eth-{eth_id} --name "seed" --password-file /tmp/seed.pass"""

LIGHTHOUSE_VALIDATOR_CREATE_CMD = """lighthouse --testnet-dir /tmp/local-testnet/testnet --datadir /tmp/local-testnet/eth-{eth_id} account validator create --wallet-name seed --wallet-password /tmp/seed.pass --count 1"""

VALIDATOR_DEPOSIT_SH = """\
#!/bin/bash

contract_address=`cat /tmp/local-testnet/testnet/config.yaml| grep -i address | cut -d '"' -f 2`
data=`cat /tmp/local-testnet/eth-{eth_id}/validators/0x*/eth1-deposit-data.rlp | cut -d '#' -f 1`
geth --exec "eth.sendTransaction({{from: eth.coinbase, to: '$contract_address', value: '32000000000000000000', data: '$data'}})" attach
"""

LIGHTHOUSE_BOOTNODE_CMD = """lighthouse boot_node --testnet-dir /tmp/local-testnet/testnet --port 30305 --listen-address {ip_address} --disable-packet-filter --network-dir /tmp/local-testnet/bootnode &"""
