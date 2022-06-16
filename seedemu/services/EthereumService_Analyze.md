EthereumService Analyze

* Bootnode
    - By default, all of each node is a bootnode
    - When creating a node, the node need to know enode urls of bootnodes.

        ```python
        if allBootnode or self.__is_bootnode:
            # generate enode url. other nodes will access this to bootstrap the network.
            # Default port is 30301, you can change the custom port with the next command
            node.appendStartCommand('echo "enode://$(bootnode -nodekey /root/.ethereum/geth/nodekey -writeaddress)@{}:30301" > /tmp/eth-enode-url'.format(addr))
            # Default port is 30301, use -addr :<port> to specify a custom port
            node.appendStartCommand('bootnode -nodekey /root/.ethereum/geth/nodekey -verbosity 9 -addr {}:30301 > /tmp/bootnode-logs &'.format(addr))          
            # host the eth-enode-url for other nodes.
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self.__bootnode_http_port), True)

        ```
    - The way to let other nodes to know the enode url of bootnodes: use `bootstrapper` script. 
        ```python
        # bootstraper: get enode urls from other eth nodes.
        ETHServerFileTemplates['bootstrapper'] = '''\
        #!/bin/bash

        while read -r node; do {
            let count=0
            ok=true
            until curl -sHf http://$node/eth-enode-url > /dev/null; do {
                echo "eth: node $node not ready, waiting..."
                sleep 3
                let count++
                [ $count -gt 60 ] && {
                    echo "eth: node $node failed too many times, skipping."
                    ok=false
                    break
                }
            }; done

            ($ok) && {
                echo "`curl -s http://$node/eth-enode-url`," >> /tmp/eth-node-urls
            }
        }; done < /tmp/eth-nodes
        '''
        ```
    - Detailed description
        1. bootnode : Save a enode url to /tmp/eth-enode-url
        2. bootnode : Run bootnode 
        3. bootnode : Host http server
        4. node : Access to bootnode http server and get eth-enode-url file from the bootnode.
        5. node : Run node with bootnodes' urls collected from the previous step.

    /tmp/keystore : prefunded account's keystore


    suggestion:
    1)  Manage a genesis file inside Ethereum`Service` class not `Server` class.
    2) Is it necessary to support deploying multiple mechanisms ethereum at one emulator?
    3) 

    Build Step : seedemu
        - Install essential softwares on nodes. 
        - Create a genesis file 
            : prefund accounts
        - Run bootnodes.
    Dynamic Control Step : seedemu-controller(client)
        - Run Nodes
        - Deploy Contract

        

    
    
