#!/bin/bash
while read -r node; do {
    let count=0
    ok=true
    until curl -sHf http://$node:8545/eth-enode-url > /dev/null; do {
        echo "eth: node $node not ready, waiting..."
        sleep 3
        let count++
        [ $count -gt 60 ] && {
            echo "eth: node $node failed too many times, skipping."
            ok=false
            break
        }
    }; done
    ($ok) && while true; do {
        echo "`curl -s http://$node:8088/eth-enode-url`," >> /tmp/eth-node-urls
        ENODE_URL=`cat /tmp/eth-node-urls | cut -d ',' -f 1`
        if [[ $ENODE_URL = enode* ]]; then
            break
        fi
    }; done
}; done < /tmp/eth-nodes
