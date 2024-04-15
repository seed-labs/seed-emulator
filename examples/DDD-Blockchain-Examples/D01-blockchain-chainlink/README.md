# Chainlink Example
This example demonstrates how to use Chainlink with a blockchain. The developer manual can be found [here](../../../docs/developer_manual/06-chainlink-service.md)

## Table of Contents
- [Chainlink Example](#chainlink-example)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Building the Emulation](#building-the-emulation)
  - [Interacting with the Chainlink Normal Server](#interacting-with-the-chainlink-normal-server)
  - [Interacting with the Chainlink Initializer Server](#interacting-with-the-chainlink-initializer-server)
  - [Chainlink User Service](#chainlink-user-service)
    - [Flow of the Chainlink User Service](#flow-of-the-chainlink-user-service)
    - [Interating with the User contract deployed by the Chainlink User Service](#interating-with-the-user-contract-deployed-by-the-chainlink-user-service)
  - [To Do](#to-do)

## Requirements
1. Base Layer: [hybrid-internet](./hybrid-internet.py)
2. Blockchain: [blockchain-poa](../D00-blockchain-poa/blockchain-poa.py)
3. Faucet: [faucet](../../B12-ethereum-faucet/blockchain.py)

## Building the Emulation
1. Create an instance of the emulator:
    ```python
    emu = Emulator()
    ```
2. Load the base layer:
We are using a slighly modified version of the hybrid-internet. So to generate the hybrid-internet.bin file, run the following command:
    ```python
    python3 hybrid-internet.py
    ```
Then load the base layer:
    ```python
    emu.load('./hybrid-internet.bin')
    ```
3. Initialize the blockchain:
Use the template from the blockchain-poa example and make sure to enable the websocket on the ethereum nodes:
    ```python
    e.enableGethWs()    # Enable WS on all nodes for chainlink service to listen
    ```
4. Initialize the faucet:
Use the template from the ethereum-faucet example:

5. Initialize the Chainlink Service:
    ```python
    chainlink = ChainlinkService()
    ```
6. Initialize the Chainlink Initializer Server:
    ```python
      cnode = 'chainlink_init_server'
      c_init = chainlink.installInitializer(cnode)
      c_init.setFaucetServerInfo(vnode = 'faucet', port = 80)
      c_init.setRPCbyEthNodeName('eth2')
      service_name = 'Chainlink-Init'
      emu.getVirtualNode(cnode).setDisplayName(service_name)
      emu.addBinding(Binding(cnode, filter = Filter(asn=164, nodeName='host_2')))
    ```
    In the above code, we are assigning the server instance chainlink.installInitializer(cnode) to c_init, specifying the virtual node cnode named 'chainlink_init_server'. The script then sets up the faucet server information for the Chainlink initializer by assigning the virtual node 'faucet' and the port '80' through c_init.setFaucetServerInfo(). It configures the Ethereum RPC address using the node name 'eth2' with c_init.setRPCbyEthNodeName(). Additionally, the display name of the virtual node is set to 'Chainlink-Init', which helps in identifying the node within the emulated network. Finally, the script establishes a network binding for this initializer server to a host node identified by ASN 164 and the node name 'host_2', ensuring that the Chainlink server is correctly linked within the specified autonomous system.

7. Initialize the Chainlink Node:
   ```python
    i = 0
    c_asns  = [150, 151]
    # Create Chainlink normal servers
    for asn in c_asns:
        cnode = 'chainlink_server_{}'.format(i)
        c_normal = chainlink.install(cnode)
        c_normal.setRPCbyEthNodeName('eth{}'.format(i))
        c_normal.setInitNodeIP("chainlink_init_server")
        c_normal.setFaucetServerInfo(vnode = 'faucet', port = 80)
        service_name = 'Chainlink-{}'.format(i)
        emu.getVirtualNode(cnode).setDisplayName(service_name)
        emu.addBinding(Binding(cnode, filter = Filter(asn=asn, nodeName='host_2')))
        i = i + 1
    ```
    In the above code, it creates multiple chainlink server nodes each associated with different autonomous system numbers (ASNs). For each server, we set up the Ethereum RPC connection using `setRPCbyEthNodeName('eth{i}')`, which links each Chainlink server to a specific Ethereum node. We have to make sure the websocket for that Ethereum node is enabled. `setInitNodeIP()` is used to set the IP address of the Chainlink initializer server. This is necessary for the Chainlink server to get the LINK token address and send the deployed oracle contract address to be displayed on the Chainlink Init server. `setFaucetServerInfo()` is used to set the faucet server information for the Chainlink server. `setUsernameAndPassword()` is used to set the username and password for the Chainlink server default is `seed@seed.com` and `Seed@emulator123`. The display name of the virtual node is set to 'Chainlink-{i}' to help identify the node within the emulated network. Finally, a network binding is established for each Chainlink server to a host node identified by ASN and node name 'host_2'.

8. Once you have completed the installation and configuration the Chainlink initializer and Chainlink node, you can add the Chainlink Service layer to the emulation. Additionaly we have to add the blockchain and faucet layers to the emulation.:
    ```python
    emu.addLayer(eth)
    emu.addLayer(faucet)
    emu.addLayer(chainlink)
    ```
9. Now, we can render and compile the emulation:
    ```python
    OUTPUTDIR = './emulator_20'
    emu.render()
    docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=Platform.AMD64)
    emu.compile(docker, OUTPUTDIR, override = True)
    ```
    Here we have enabled the etherView, this displays the Ethereum transactions on the emulator. The internetMap is enabled to view the network topology of the emulated network. The platform is set to AMD64. The compiled emulation is stored in the directory 'emulator_20'. If you want to use a ARM platform, you can set the platform to `Platform.ARM64`.
10. Finally, run the emulation script using the following command:
    ```python
    python3 blochain-poa-chainlink.py
    ```

## Running the Emulation
Within the output directory, a docker-compose.yml file is generated. Run the following command to start the emulation:
```bash
./emulator_20$ docker-compose build
./emulator_20$ docker-compose up
```

## Interacting with the Chainlink Normal Server
There are two ways to interact with the Chainlink service:
1. Chainlink UI: You can access the Chainlink UI by navigating to `http://<host_ip>:6688` in your web browser. The Chainlink UI allows you to create and manage Chainlink jobs. It is also useful to check the status of connection with the Ethereum node.
2. Chainlink CLI: You can interact with the Chainlink service using the Chainlink CLI. The Chainlink CLI is a command-line tool that allows you to interact with the Chainlink node. You can use the CLI to create and manage Chainlink jobs, check the status of the Chainlink node, and more. The Chainlink CLI can be accessed by running the following command:
    ```bash
    docker exec -it <CONTAINER ID> /bin/bash
    chainlink admin login
    ```

## Interacting with the Chainlink Initializer Server
The Chainlink Initializer server is used to deploy the LINK token contract and display the deployed oracle contract address. You can access the Chainlink Initializer server by navigating to `http://<host_ip>:80` in your web browser. The Chainlink Initializer server displays the deployed oracle contract address and the LINK token contract address. This information is useful for building and deploying solidity contracts and deploying jobs.

## Chainlink User Service
The Chainlink User Service is an automated example that demonstrates how to interact with the Chainlink service. First let's take a look how to build the emulation for the Chainlink User Service:
1. Create an instance of the Chainlink User Service:
    ```python
    chainlink_user = ChainlinkUserService()
    ```
2. Setup the User Service
   ```python
    cnode = 'chainlink_user'
    c_user = chainlink_user.install(cnode)
    c_user.setRPCbyEthNodeName('eth2')
    c_user.setFaucetServerInfo(vnode = 'faucet', port = 80)
    c_user.setChainlinkServiceInfo(init_node_name='chainlink_init_server', number_of_normal_servers=2)
    emu.getVirtualNode(cnode).setDisplayName('Chainlink-User')
    emu.addBinding(Binding(cnode, filter = Filter(asn=153, nodeName='host_2')))
    ```
    In the above code, we are assigning the server instance chainlink_user.install(cnode) to c_user, specifying the virtual node cnode named 'chainlink_user'. The script then sets up the faucet server information for the Chainlink user by assigning the virtual node 'faucet' and the port '80' through c_user.setFaucetServerInfo(). It configures the Ethereum RPC address using the node name 'eth2' with c_user.setRPCbyEthNodeName(). Additionally, the script establishes the Chainlink service information using c_user.setChainlinkServiceInfo(). This function requires the Chainlink initializer node name and the number of normal servers. The display name of the virtual node is set to 'Chainlink-User', which helps in identifying the node within the emulated network. Finally, the script establishes a network binding for this user server to a host node identified by ASN 153 and the node name 'host_2', ensuring that the Chainlink server is correctly linked within the specified autonomous system.
3. Add the Chainlink User Service layer to the emulation:
    ```python
    emu.addLayer(chainlink_user)
    ```

### Flow of the Chainlink User Service
This example demonstrates how to interact with the Chainlink service using a [user contract](./contracts/user_contract.sol). The user contract is deployed on the Chainlink user server. The user contract interacts with the Chainlink service to get the latest price of an asset. The user contract uses the LINK token contract address and the oracle contract addresses to interact with the Chainlink service. The user contract is funded with LINK tokens using the faucet server. The user contract sends a request to the Chainlink service to get the latest price of an asset. The Chainlink service sends the response to the user contract. The user contract then processes the response and displays the latest price of the asset.

1. Wait for the chainlink init server to be up. Get LINK token contract address and oracle contract addresses from the Chainlink init server
2. Create a web3 account and deploy the user contract
3. Fund the user account using the faucet server
4. Deploy the user contract
5. Set the LINK token contract address and oracle contract addresses in the user contract
6. Send 1ETH to the LINK token contract to fund the user account with LINK tokens
7. Transfer LINK token to the user contract
8. Call the main function in the user contract

### Interating with the User contract deployed by the Chainlink User Service
After the Chainlink User Service is done running, you can interact with the user contract deployed by the Chainlink User Service. To get the User contract address, you can check the logs of the Chainlink User Service. And another way is to do the following steps:
1. Execute the following command to get the container ID of the Chainlink User Service:
    ```bash
    docker ps | grep Chainlink-User
    ```
2. Execute the following command to get the bash shell of the Chainlink User Service:
    ```bash
    docker exec -it <CONTAINER ID> /bin/bash
    ```
3. After the Chainlink User Service deployes the user contract, you can find the contract address inside the container. You can use the following command to get the contract address:
    ```bash
    cat ./info/user_contract.json
    ```
4. Now you can interact with the user contract using Remix or any other Ethereum development tool.
   - Compile the user contract
   - Go to the Deploy and Run Transactions tab
   - In the Environment dropdown, select MetaMask
   - Select the user contract in the contract dropdown
   - In the At Address field, enter the contract address
   - Click the At Address button
   - You can now interact with the user contract

## To Do
- [ ] Make a video tutorial for the Chainlink example and how to interact with the Chainlink service