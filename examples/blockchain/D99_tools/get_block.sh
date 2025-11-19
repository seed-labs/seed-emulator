#!/bin/bash

eth_container=as151h-Ethereum-POS-2-10.151.0.71
block=$(docker exec  $eth_container geth attach --exec 'eth.blockNumber')

echo "Block number: $block"
