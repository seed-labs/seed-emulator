# Kubo dApp Example
This is an example that illustrates one use case for IPFS: its intergation with Ethereum
smart contracts to create distributed applications, or dApps.

## Instructions

1. Run the emulation
2. Set up MetaMask:
   1. Download MetaMask [here](https://metamask.io/download/).
   2. Recover wallet using the recovery phrase "great amazing fun seed lab protect network system security prevent attack future".
   3. Add the local emulated network:
      - Go to Settings>Networks>Add Network>Add a Network Manually
      - RPC URL should be "http://localhost:8545".
      - Chain ID should be "1337".
      - Currency symbol should be "ETH".
3. Set up the Ethereum smart contract:
   1. Go to the [Remix IDE](https://remix.ethereum.org/#lang=en&optimize=true&runs=200&evmVersion=paris&version=soljson-v0.8.25).
   2. In the file explorer pane on the left side of the page, click on the "Upload files" icon and upload the smart contract located at [contract/IPFS_Storage.sol](contract/IPFS_Storage.sol).
   3. Using the navigation bar on the left side, go to the "Solidity compiler". If you clicked the link above to access Remix, you immediately click "Compile IPFS_Storage.sol". Otherwise, click on "Advanced Configurations" and change the EVM version to "paris" and enable optimization. Then click "Compile IPFS_Storage.sol".
   4. Using the navigation bar on the left side, go to the "Deploy & run transactions" tab. Click on the "Environment" dropdown and select "Injected Provider - Metamask". Finally, click the "Deploy" button.
   5. In the "Deployed Contracts" section below, you can find the contract address. Copy this address to be used later.
3. Open the dApp
   1. Go to the dApp hosted at http://localhost:3000/
   2. Follow the setup wizard that you are presented with. You will be required to paste in the contract address that you copied in the previous step.
   3. Upload images to the image board. MetaMask will pop up and ask you to confirm a smart contract interaction each time you upload something. Your images are bound to your account. You can test this by changing the active account in MetaMask.

## Emulator Code

Below, you will find a walkthrough of the code used to build this emulation. This code is based on several pre-existing examples including [B00-mini-internet](/examples/B00-mini-internet/README.md) and [B06-blockchain](/examples/B06-blockchain/README.md).

### Ethereum

First, we import a pre-build base component including hosts and routing. This is based on [B00-mini-internet](/examples/B00-mini-internet/README.md) and is compiled by `base-component.py`.

We then create the Ethereum layer based on the [B06-blockchain](/examples/B06-blockchain/README.md) example. We also create a blockchain instance using the proof-of-authority consensus protocol.
```python
eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)
```

Now that we have created an instance of the Ethereum blockchain, we can add local accounts:
```python
# Generate 5 accounts, each with 100 Ethers:
words = "great amazing fun seed lab protect network system security prevent attack future"
blockchain.setLocalAccountParameters(mnemonic=words, total=5, balance=999999999) 

# Generate three more accounts for users:
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=30)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9', 
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24', 
                           balance=10)
```

We then iterate through the ASNs and hosts to install the Ethereum service on all nodes:
```python
# Create the Ethereum servers. 
asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
hosts_total = 1    # The number of servers per AS
signers  = []
i = 0
for asn in asns:
    for id in range(hosts_total):
        vnode = 'eth{}'.format(i)
        e = blockchain.createNode(vnode)

        displayName = 'Ethereum-POA-%.2d'
        e.enableGethHttp()  # Enable HTTP on all nodes
        e.unlockAccounts()
        if i%2  == 0:
            e.startMiner()
            signers.append(vnode)
            displayName = displayName + '-Signer'
            emu.getVirtualNode(vnode).appendClassName("Signer")
        if i%3 == 0:
            e.setBootNode(True)
            displayName = displayName + '-BootNode'
            emu.getVirtualNode(vnode).appendClassName("BootNode")

        emu.getVirtualNode(vnode).setDisplayName(displayName%(i))
        emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        i = i+1
```

### InterPlanetary File System

First, we create the Kubo service and change the HTTP gateway port to 8081, instead of the default port 8080 because this conflicts with the Internet Map.
```python
# Initialize the Kubo service:
ipfs = KuboService(gatewayPort=8081)
```

We follow a similar pattern to installing the Ethereum service on the nodes, while installing the Kubo service.
```python
# Iterate through hosts from base component and install Kubo on them:
asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
numHosts = 1   # Number of hosts in the stub AS to install Kubo on
i = 0
webAppCandidates = []
for asNum in asns:
    curAS = emu.getLayer('Base').getAutonomousSystem(asNum)
    # This AS exists, so install Kubo on each host:
    for h in range(numHosts):
        vnode = f'kubo{i}'
        cur = ipfs.install(vnode)
        if i % 5 == 0:
            cur.setBootNode()
            webAppCandidates.append((asNum, f'host_{h}'))
        
        # Modify display name and bind virtual node to a physical node in the Emulator:
        print(f'Bound {vnode} to hnode_{asNum}_host_{h}')
        emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName='host_{}'.format(h), allowBound=True)))
        i += 1
```

### Setting up the dApp

There are a few additional steps that we must take in order to deploy and configure the dApp within the emulation.

We need to expose the `geth` RPC API for the dApp to access the Ethereum blockchain, so we select a random Ethereum node and forward port `8545`:
```python
# Expose Ethereum on a node:
ethVnode = random.choice(signers)
ethNode = emu.getVirtualNode(ethVnode)
ethNode.addPortForwarding(8545, 8545)
```

We then create an additional node on which we install the Kubo service:
```python
webKubo = ipfs.install('extraKubo')
asn, node = random.choice(webAppCandidates)
webASN = emu.getLayer('Base').getAutonomousSystem(asn)
webHost = webASN.createHost('webhost').joinNetwork('net0')
```

In order to allow our dApp to interact with Kubo, we must configure CORS in Kubo:
```python
# Make changes to active Kubo configuration:
webKubo.setConfig('API.HTTPHeaders.Access-Control-Allow-Origin', ["*"])
```

The dApp is a web application created using `node.js`, React, and the Material UI framework. This means that we must install the appropriate software to host the dApp. We then start the server.
```python
# Add software to node:
webHost.addSoftware('curl')
webHost.addBuildCommand('curl -fsSL https://deb.nodesource.com/setup_21.x | bash - && apt update -y && apt install -y nodejs')
webHost.addBuildCommand('npm install -g serve')

# Build and run the web app:
webHost.appendStartCommand('serve -sC /volumes/kubo-dapp/build', fork=True)
```

We must then allocate additional resources to the web host node which serves the dApp. This includes forwarding the necessary ports for dApp access, as well as access to IPFS which is handled by the frontend application. We also bind this virtual node to a physical node to apply these changes to the emulation.
```python
# Allocate node resources:
webHost.addSharedFolder('/volumes', '../volumes')
webHost.addPortForwarding(3000, 3000)
webHost.addPortForwarding(5001, 5001)
webHost.addPortForwarding(8081, 8081)
webHost.setDisplayName('WebHost')
emu.addBinding(Binding('extraKubo', filter = Filter(asn=asn, nodeName='webhost')))
```

Now we just render and compile as usual:
```python
# Render and compile 
emu.addLayer(ipfs)
emu.addLayer(eth)
emu.render()

docker = Docker(internetMapEnabled=True, etherViewEnabled=True)
emu.compile(docker, OUTPUTDIR, override = True)
```