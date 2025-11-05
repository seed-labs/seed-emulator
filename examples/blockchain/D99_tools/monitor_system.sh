#!/bin/bash

# Select a docker node (must be an Ethereum node)
eth_node="as163h-Ethereum-POS-87-10.163.0.77"

# Generate the name of the log file 
file_prefix="system_info"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
filename="$file_prefix-$TIMESTAMP.log"
echo "block_number, mem_usage" >> $filename

while true;
do 
   # Get the block number
   block=$(docker exec $eth_node geth attach --exec 'eth.blockNumber')

   # Get the memory usage
   mem_usage0=$(free -h |grep Mem: | awk '{print $3}')
   mem_usage=${mem_usage0/Gi}

   line="$block, $mem_usage"
   echo "Block number: $block -- Mem usage: $mem_usage"
   echo $line >> $filename

   sleep 30
done
