#!/bin/bash

eth_container=as150h-Ethereum-POS-2-10.150.0.72
block=$(docker exec  $eth_container geth attach --exec 'eth.blockNumber')

echo "Block number: $block"
