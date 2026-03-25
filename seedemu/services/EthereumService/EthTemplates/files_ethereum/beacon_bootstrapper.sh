#!/bin/bash
while read -r node; do {{
    let count=0
    ok=true
    validator=false
    until curl --http0.9 -sHf http://$node/testnet > /dev/null; do {{
        echo "eth: beacon-setup node $node not ready, waiting..."
        sleep 10
        let count++
        [ $count -gt 60 ] && {{
            echo "eth: connection to beacon-setup node $node failed too many times, skipping."
            ok=false
            break
        }}
    }}; done
   
        curl --http0.9 -s http://$node/testnet > /tmp/testnet.tar.gz
        mkdir /tmp/bn
        tar -xzvf /tmp/testnet.tar.gz -C /tmp/bn

        echo "[beacon_client] starting lighthouse beacon client"
        {bc_start_command}

      
}}; done < /tmp/beacon-setup-node


