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
    ($ok) && {{
        validator={is_validator}
        bootnode={is_bootnode}
        ($validator) && {{
            curl --http0.9 -s http://$node/eth-{eth_id} > /tmp/eth.tar.gz
            tar -xzvf /tmp/eth.tar.gz -C /tmp
        }}
        ($bootnode) && {{
            curl --http0.9 -s http://$node/bootnode > /tmp/bootnode.tar.gz
            tar -xzvf /tmp/bootnode.tar.gz -C /tmp
        }}
        curl --http0.9 -s http://$node/testnet > /tmp/testnet.tar.gz
        tar -xzvf /tmp/testnet.tar.gz -C /tmp
        {bootnode_start_command}
        {bc_start_command}
        {wallet_create_command}
        {validator_create_command}
        {validator_deposit_sh}
        {vc_start_command}
    }}
}}; done < /tmp/beacon-setup-node


