#/bin/bash
set -eu

echo "Test account L1 balance:"
cast balance --rpc-url $L1_RPC_URL $GS_TEST_ADDRESS
echo "Test account L2 balance:"
cast balance --rpc-url $L2_RPC_URL $GS_TEST_ADDRESS

L1_BRIDGE_ADDRESS=$(cat l2/deployments/getting-started/L1StandardBridgeProxy.json | jq -r .address)
cast send --rpc-url $L1_RPC_URL --private-key $GS_TEST_PRIVATE_KEY --value 10ether $L1_BRIDGE_ADDRESS

