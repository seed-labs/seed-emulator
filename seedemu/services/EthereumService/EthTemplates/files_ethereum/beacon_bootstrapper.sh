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

        curl --http0.9 -s http://$node/testnet > /tmp/testnet.tar.gz
        mkdir /tmp/bn
        tar -xzvf /tmp/testnet.tar.gz -C /tmp/bn

        ($validator) && {{
            mkdir /tmp/vc
            tar -xzvf /tmp/testnet.tar.gz -C /tmp/vc
            eth2-val-tools keystores --source-mnemonic "giant issue aisle success illegal bike spike question tent bar rely arctic volcano long crawl hungry vocal artwork sniff fantasy very lucky have athlete" --source-max 4 --source-min 0 --out-loc "/tmp/vc/assigned_data" 

            mkdir /tmp/vc/local-testnet/testnet/validators
            cp -r /tmp/vc/assigned_data/keys/* /tmp/vc/local-testnet/testnet/validators/
            cp -r /tmp/vc/assigned_data/secrets /tmp/vc/local-testnet/testnet/
        }}

        
        
        echo "[beacon_client] starting lighthouse beacon client"
        {bc_start_command}
        {wallet_create_command}
        {validator_create_command}
        {validator_deposit_sh}

        # while loop till bc client is ready
        while ! curl --http0.9 -sHf http://{ip_address}:8000 > /dev/null; do
            echo "eth: local beacon node not ready, waiting..."
            sleep 3
        done

        ($validator) && {{
        echo "[validator client] starting lighthouse validator client"
        }}
        {vc_start_command}
    }}
}}; done < /tmp/beacon-setup-node


