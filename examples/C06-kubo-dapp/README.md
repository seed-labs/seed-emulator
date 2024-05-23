# Kubo dApp Example
This is an example that illustrates one use case for IPFS: its intergation with Ethereum smart
contracts to create distributed applications, or dApps.

This dApp is a simple image board web application. Users are differentiated by their Ethereum
accounts, and each use may upload images to their own image boards. Upon loading the application,
the user is greeted by all previously uploaded images (if applicable).

This simple demonstration is a preview of the functionality that IPFS can add to decentralized
applications built on the Ethereum blockchain. Future applications could create more complex smart
contracts to provide more backend functionality to the dApp, and take advantage of advanced IPFS
technologies like the [InterPlanetary Name System (IPNS)](https://docs.ipfs.tech/concepts/ipns/) to serve content stored in IPFS dynamically
and to provide the illusion of mutability.

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
   2. Follow the setup wizard that you are presented with.
   3. Upload images to the image board. MetaMask will pop up and ask you to confirm a smart contract interaction each time you upload something. Your images are bound to your account. You can test this by changing the active account in MetaMask.

## Using the SEED Image Board (dApp)

The SEED Image Board presents users with their own personal collection of user-uploaded images. The
images shown are unique to each user. The files themselves are stored in the InterPlanetary File
System, and an Ethereum smart contract maintains the relationship between a user and their images
while also storing extremely limited metadata about those images. Despite all of this, using the
SEED Image Board is simple!

### Interacting with the dApp

1. Visit the web application hosted at http://localhost:3000/.
2. If this is your first time using the SEED Image Board, you will be met with a brief setup wizard
   which will inform you about the dApp and guide you through connecting your wallet (we recommend
   using MetaMask).
3. You can now upload your own image by clicking the "Upload" button and chosing a file.
4. Once you have chosen an image, add it to your image board by clicking the "Add to Board" button.
5. Upon adding a photo to your image board, your Ethereum wallet may request your authorization in
order to interact with the smart contract. Approve this interaction to save the uploaded image to
your board.
6. Next time you reload the SEED Image Board (while this same simulation is running), you will find
all of your previously-uploaded images on your personal board.

### Switching Users/Accounts

If you'd like to switch users, you must change your active Ethereum wallet account. You can do so
using the wallet connector account center displayed as a small icon in the bottom right-hand corner
of the web page. Some Ethereum wallets like MetaMask do not allow your account to be changed this
way, and so you may have to refer to the documentation for your wallet to switch active accounts.

For MetaMask, the process is simple:
1. Click on the MetaMask browser extension icon.
2. Click on the website connection icon. This is a circle with an icon representing the current
   website, and is located directly to the right of the account selector at the top center of the
   browser extension popup.
3. All available accounts are now displayed. To change accounts, click on the "Switch to this
   account" link under the desired account.
4. Upon refreshing the page, the new user's account will now be active and their images displayed
   (if any).

## Emulator Code

Below, you will find a walkthrough of the code used to build this emulation. This code is based on several pre-existing examples including [B00-mini-internet](/examples/B00-mini-internet/README.md) and [B06-blockchain](/examples/B06-blockchain/README.md).

### Ethereum

First, we import a pre-build base component including hosts and routing. This is based on [B00-mini-internet](/examples/B00-mini-internet/README.md) and is compiled by `base-component.py`.

We then create the Ethereum layer based on the [B06-blockchain](/examples/B06-blockchain/README.md) example. We also create a blockchain instance using the proof-of-authority consensus protocol.
```python
eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)
```

Now that we have created an instance of the Ethereum blockchain, we can add local accounts which
will may be used as users of the dApp. We also create an additional account which is used only to
deploy the smart contract used by the dApp automatically.
```python
# Generate three more accounts for users:
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=30)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9', 
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24', 
                           balance=10)

# The smart contract will be deployed from this account:
blockchain.addLocalAccount(address='0xad15bEbf1992212A57dC3513acc77796110E2bD4', 
                           balance=9999999)
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

The dApp is a web application created using `node.js`, React, and the Material UI framework. This means that we must install the appropriate software to host the dApp.
```python
# Add software to node:
webHost.addSoftware('curl')
webHost.addBuildCommand('curl -fsSL https://deb.nodesource.com/setup_21.x | bash - && apt update -y && apt install -y nodejs')
webHost.addBuildCommand('npm install -g serve')
webHost.addBuildCommand('pip install web3 py-solc-x')   # Used to deploy the smart contract
webHost.addBuildCommand("""python3 -c 'from solcx import install_solc;install_solc(version="0.8.15")'""")   # Install the solc compiler to compile the smart contract
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

Now, we render the emulation:
```python
# Render and compile 
emu.addLayer(ipfs)
emu.addLayer(eth)
emu.render()
```

After rendering, we have to add a few more start commands. We wait until after rendering to do so
because we need to determine the IPv4 address for a node which we cannot do until all virtual nodes
have been bound to a physical node and their interfaces created.

```python
# Deploy the smart contract:
webHost.appendStartCommand(f'python3 volumes/deployContract.py {getIP(emu.resolvVnode(ethVnode))}')

# Build and run the web app:
webHost.appendStartCommand('serve -sC /volumes/kubo-dapp/build', fork=True)
```

Following this, we simply compile as usual!

```python
docker = Docker(internetMapEnabled=True, etherViewEnabled=True)
emu.compile(docker, OUTPUTDIR, override = True)
```

## Deploying the Contract
As is mentioned in the outline of the [Emulator Code](#emulator-code), we automatically compile and
deploy the smart contract for this dApp when the emulation starts. We do so using a simple Python
script which compiles the smart contract written in Solidity using the `solcx` Python library, and
deploys the smart contract to the Ethereum blockchain using the `web3` Python library.

**This script takes a single command line argument:** the IPv4 address to use for the Geth RPC API. In this case, this is the IPv4 address of the node whose RPC API port we expose to the host (for consistencys's sake).

First, we do some basic setup. Most notably, we initialize a local variable containing the private
key of the Ethereum account that the smart contract will be deployed from. This is the account
created in the emulator code during the [Ethereum setup section](#ethereum).

```python
CONTRACT_DIR = '/volumes/contract/'
RPC_URL = f'http://{sys.argv[1]}:8545'
DEPLOYER_ACC_KEY = '0x213c14e0aefb8738cda0bdccb2aa42d63ca9acfe32d9e666666bb2bce88b468f'
```

### Compiling the Smart Contract

We compile the smart contract automatically using the Solidity compiler via the Python library
`solcx`. The original smart contract is stored within the code for this example. We specify the EVM
version to ensure that the contract may be successfully deployed to the simulated Ethereum
blockchain, which runs an older version of the EVM than new nodes. We then extract the compiled ABI
and bytecode ("bin") which are needed to access and deploy the smart contracted.

```python
# Compile the smart contract:
compiledContract = compile_files(
   [os.path.join(CONTRACT_DIR, 'IPFS_Storage.sol')],
   output_values=['abi', 'bin'],
   solc_version='0.8.15',
   evm_version='london',
   optimize=True,
   optimize_runs=200
)
_, contract_interface = compiledContract.popitem()
contract_abi = contract_interface['abi']
contract_bin = contract_interface['bin']
```

### Connecting to Ethereum

Now that we've compiled our smart contract, we need to connect to the local Ethereum blockchain via
the Geth RPC API. In addition, we need to inject some middleware into `web3` to allow the client to
correctly communicate with our simulated blockchain. This is because our simulated Ethereum
blockchain uses the proof-of-authority consensus protocol, whereas the Ethereum mainnet now uses
the proof-of-stake consensus protocol.

```python
# Connect to the Ethereum RPC API via Web3:
web3 = Web3(HTTPProvider(RPC_URL))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
retryInterval = 5
timeout = 60
while not web3.is_connected() and timeout > 0:
   logging.error("Failed to connect to Ethereum node. Retrying...")
   time.sleep(retryInterval)
   timeout -= retryInterval
logging.info("Successfully connected to the Ethereum node.")
```

### Connecting our Account

In order to deploy our smart contract, we must do so from a valid and well-funded Ethereum account.
We will use the account that we created in the emulator code during the [Ethereum setup section](#ethereum),
which we will recover using its private key. We also add some middleware here to handle signing of
transactions using this account as default.

```python
# We will deploy this using an account that was created when the emulation was generated.
# This account has a starting balance of 9999999 ETH.
deployerAccount: LocalAccount = Account.from_key(DEPLOYER_ACC_KEY)
web3.middleware_onion.add(construct_sign_and_send_raw_middleware(deployerAccount))
web3.eth.default_account = deployerAccount.address
```

### Deploying IPFS Storage

Now that we have completed all of the necessary preparation, it is time to deploy the smart
contract to the Ethereum blockchain. We do so by first creating the smart contract object using
`web3` and the ABI and bytecode that we generated earlier during the [compile phase](#compiling-the-smart-contract).
Next, we deploy the smart contract, executing its constructor and creating a public transaction.
We wait for this transaction to be confirmed, after which we receive a receipt containing the
address of the deployed smart contract. Finally, we write this address to a file to be used by our
dApp.

```python
# Construct the smart contract object:
ipfsStorage = web3.eth.contract(abi=contract_abi, bytecode=contract_bin)
logging.info('Successfully imported ABI and bytecode to create contract.')

# Deploy the smart contract:
nonce = web3.eth.get_transaction_count(deployerAccount.address)
logging.info('Deploying smart contract...')
tx_hash = ipfsStorage.constructor().transact()
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
logging.info(f'Deployed smart contract at {tx_receipt.contractAddress}')

# Save the address of the deployed contract for our dApp to use:
with open('volumes/kubo-dapp/public/contract_address.txt', 'w') as file:
   file.write(tx_receipt.contractAddress)
```