# Building the Chainlink Service

This README provides a step-by-step guide to build the Chainlink service on the SEED emulator.

## Table of Contents
- [Building the Chainlink Service](#building-the-chainlink-service)
  - [Table of Contents](#table-of-contents)
  - [Building the Emulation](#building-the-emulation)
  - [Interacting with the Chainlink Initializer Server](#interacting-with-the-chainlink-initializer-server)
    - [How to know if the Chainlink Initializer Server is running?](#how-to-know-if-the-chainlink-initializer-server-is-running)
  - [Interacting with the Chainlink Normal Server](#interacting-with-the-chainlink-normal-server)
    - [How to know if the Chainlink Normal Server is running?](#how-to-know-if-the-chainlink-normal-server-is-running)


## Building the Emulation
1. Load the instance of the blockchain layer with the hybrid internet layer:
    ```python
    emuA = Emulator()
    local_dump_path = './blockchain-poa.bin'
    # Run and load the pre-built ethereum poa component
    ethereum_poa.run(dumpfile=local_dump_path, hosts_per_as=4)
    emuA.load(local_dump_path)
    ```
2. Get the information about faucet and eth nodes from the above loaded component:
    ```python
    eth:EthereumService = emuA.getLayer('EthereumService')
    blockchain: Blockchain =  eth.getBlockchainByName(eth.getBlockchainNames()[0])
    faucet_dict = blockchain.getFaucetServerInfo()
    eth_nodes = blockchain.getEthServerNames()
    ```
3. Initialize the Chainlink Service with faucet server info:
    ```python
    emuB = Emulator()
    chainlink = ChainlinkService()
    # Set the faucet server in the service class
    chainlink.setFaucetServerInfo(faucet_dict[0]['name'], faucet_dict[0]['port'])
    ```
    - `setFaucetServerInfo(vnode = 'faucet', port = 80)`: This function sets up the faucet server information for the Chainlink initializer server. The faucet server is used to fund the Chainlink server with ETH tokens. The function requires the virtual node name of the faucet server and the port number.

4. Initialize the Chainlink Initializer Server:
    ```python
    # Create Chainlink init server
    cnode = 'chainlink_init_server'
    chainlink.installInitializer(cnode) \
            .setLinkedEthNode(name=random.choice(eth_nodes)) \
            .setDisplayName('Chainlink-Init')
    ```    
    The following essential functions are used to set up the Chainlink initializer server:
    - `setLinkedEthNode('eth2')`: This function configures the Ethereum RPC address for the Chainlink initializer server. The function requires the node name of the Ethereum node to which the Chainlink initializer server  will use to interact with the blockchain.
    
    Additionaly, these are the API functions that are avilable for configuration:
    - `setDisplayName('Chainlink-Init')`: This function sets the display name for the Chainlink initializer server. The display name is used to identify the Chainlink initializer server in the emulator.

5. Initialize the Chainlink Server:
   ```python
    # Create Chainlink normal servers
    for i in range(total_chainlink_nodes):
        cnode = 'chainlink_server_{}'.format(i)
        chainlink.install(cnode) \
                .setLinkedEthNode(name=random.choice(eth_nodes)) \
                .setDisplayName('Chainlink-{}'.format(i))
    ```
    In the above code, we are creating multiple chainlink server nodes each associated with different autonoumous system (ASNs). For each server we are assigning the server instance chainlink.install(cnode) to c_normal, specifying the virtual node cnode named 'chainlink_server_{}'.format(i). 
    
    The following essential functions are used to set up the Chainlink server:
    - `setLinkedEthNode('eth{}'.format(i))`: This function configures the Ethereum RPC address for the Chainlink server. The function requires the node name of the Ethereum node to which the Chainlink server will be listening through the websocket and interacting with the blockchain.
    - `setDisplayName('Chainlink-{}'.format(i))`: This function sets the display name for the Chainlink Normal server. The display name is used to identify the Chainlink normal server in the emulator.

    Additionaly, these are the API functions that are avilable for configuration:
    - `setUsernameAndPassword(username = '<username>', password = '<password>')`: This function sets the username and password for the Chainlink server. The default username is 'seed@seed.com' and the default password is 'Seed@emulator123'. The username must be a valid email address and password must be between 16 to 50 characters.
    - 
6. Once you have completed the installation and configuration the Chainlink initializer and Chainlink node, you can add the Chainlink Service layer to the emulation.
    ```python
    emuB.addLayer(chainlink)
    ```

7. Merge the two emulator components:
   ```python
    # Merge the two components
    emu = emuA.merge(emuB, DEFAULT_MERGERS)
    ```

8. Get the information about the chainlink initialized virtual nodes and bind them to physical nodes on the emulator
   ```python
    init_node    = chainlink.getChainlinkInitServerName()
    server_nodes = chainlink.getChainlinkServerNames()
    # Bind each v-node to a randomly selected physical nodes (no filters)
    emu.addBinding(Binding(init_node))
    for cnode in server_nodes:
        emu.addBinding(Binding(cnode))
    ```

9.  Now, we can render and compile the emulation:
    ```python
    # Render and compile
    emu.render()
    if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
        current_platform = Platform.ARM64
    else:
        current_platform = Platform.AMD64

    docker = Docker(etherViewEnabled=True, platform=current_platform)
    emu.compile(docker, './output', override = True)
    ```
10. Finally, run the emulation script using the following command:
    ```python
    python3 blochain-poa-chainlink.py
    ```

## Running the Emulation
Within the output directory, a docker-compose.yml file is generated. Run the following command to start the emulation:
```bash
./output$ docker-compose build
./output$ docker-compose up
```

## Interacting with the Chainlink Initializer Server
The Chainlink Initializer server is used to deploy the LINK token contract and display the deployed oracle contract address. You can access the Chainlink Initializer server by navigating to `http://<host_ip>:80` in your web browser. The Chainlink Initializer server displays the deployed oracle contract address and the LINK token contract address. This information is useful for building and deploying solidity contracts and deploying jobs.

### How to know if the Chainlink Initializer Server is running?
You can check if the Chainlink Initializer server is running by navigating to `http://<host_ip>:80` in your web browser. If the Chainlink Initializer server is running, you will see the deployed oracle contract address and the LINK token contract address. Additionaly, you can check logs of the Chainlink Initializer server by running the following command:
```bash
docker ps | grep Chainlink-Init
docker logs <CONTAINER ID>
```
The web server will display the deployed oracle contract address as it is deployed on the Ethereum blockchain by the chainlink normal node.

Here is the sample output of the Chainlink Initializer server:
![Chainlink Initializer Server](./images/chainlink-init.png)

## Interacting with the Chainlink Normal Server
There are two ways to interact with the Chainlink service:
1. Chainlink UI: You can access the Chainlink UI by navigating to `http://<host_ip>:6688` in your web browser. The Chainlink UI allows you to create and manage Chainlink jobs. It is also useful to check the status of connection with the Ethereum node.
2. Chainlink CLI: You can interact with the Chainlink service using the Chainlink CLI. The Chainlink CLI is a command-line tool that allows you to interact with the Chainlink node. You can use the CLI to create and manage Chainlink jobs, check the status of the Chainlink node, and more. The Chainlink CLI can be accessed by running the following command:
    ```bash
    docker exec -it <CONTAINER ID> /bin/bash
    chainlink admin login
    ```

### How to know if the Chainlink Normal Server is running?
You can check if the Chainlink Normal server is running by navigating to `http://<host_ip>:6688` in your web browser. If the Chainlink Normal server is running, you will see the Chainlink UI. Additionaly, you can check logs of the Chainlink Normal server by running the following command:
```bash
docker ps | grep Chainlink
docker logs <CONTAINER ID>
```
Here is the screenshots of the Chainlink UI and how to interact with the Chainlink UI:
1. Chainlink UI Login Page:
![Chainlink UI Login Page](./images/chainlink-login.png)
This is the login page of the Chainlink UI. You can login using the username and password you have set during the configuration of the Chainlink server.
2. Chainlink UI Dashboard:
![Chainlink UI Dashboard](./images/chainlink-dashboard.png)
This is the dashboard of the Chainlink UI. You can create and manage Chainlink jobs, check the status of the Chainlink node, and more. It will show the ETH address of the account created during chainlink start command which should be funded with 5 ETH tokens.
3. Chainlink UI Nodes:
![Chainlink UI Nodes](./images/chainlink-nodes.png)
This is the nodes page of the Chainlink UI. You can check the status of the Chainlink node, add new nodes, and more.
4. Chainlink UI Jobs:
![Chainlink UI Jobs](./images/chainlink-jobs.png)
- This is the jobs page of the Chainlink UI. You can create and manage Chainlink jobs. The Chainlink jobs are used to fetch data from external APIs and send it to the Ethereum blockchain.
![Chainlink UI Job 1](./images/chainlink-job-example.png)
- Click on one of the jobs and then go to definition of that job. Here you will see the contract address of the oracle contract deployed on the Ethereum blockchain. This can be used by the user to create new jobs. Another way is to use the Chainlink Init Node webserver to get the contract address and then call the getAuthorizedSenders function to get the chainlink node address which can be used to create new jobs on that oracle contract as chainlink node and oracle contract have 1-1 relationship. 

