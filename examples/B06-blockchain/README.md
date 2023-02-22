## Table of Content

- [Build a Blockchain Component](#blockchain-component)
- [Build emulator with blockchain](#emulator)
- [Use blockchain](#use-blockchain)
- [Smart contract](#smart-contract)
- [Manually deploy a smart contract](#smart-contract-manual)

---

<a name="blockchain-component"></a>

# Build a Blockchain Component

## A.1 Creating Virtual Blockchain Node

We will create the Blockchain nodes at the Ethereum layer,
so each node created is a virtual node so that they can be deployed
in different emulators.

```python
# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`,
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = True, override=True)


# Create the 2 Blockchain layers, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.

# blockchain1 is a POW based blockchain
blockchain1 = eth.createBlockchain(chainName="POW", consensus=ConsensusMechanism.POW)

# blockchain2 is a POA based blockchain
blockchain2 = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain1 nodes (POW Etheruem) (nodes in this layer are virtual)
e1 = blockchain1.createNode("pow-eth1")
e2 = blockchain1.createNode("pow-eth2")
e3 = blockchain1.createNode("pow-eth3")
e4 = blockchain1.createNode("pow-eth4")

# Create blockchain2 nodes (POA Ethereum)
e5 = blockchain2.createNode("poa-eth5")
e6 = blockchain2.createNode("poa-eth6")
e7 = blockchain2.createNode("poa-eth7")
e8 = blockchain2.createNode("poa-eth8")
```

## A.2 Setting a Node as a Bootnode

We can set a node as a bootnode that bootstraps all blockchain nodes.
If a node is set as a bootnode, it will run a http server that sends
its blockchain node url so that the other nodes can connect to it.
The default port number of the http server is 8088 and it can be
customized. If bootnode does not set to any node, we should specify
peer nodes urls manually.

```python
# Set bootnode on e1. The other nodes can use these bootnodes to find peers.
e1.setBootNode(True).setBootNodeHttpPort(8090)
```

## A.3 Creating Accounts

By default, one account will be created per node. In POW Consensus,
the account will be created with no balance. In the case of POA Consensus,
the account will have 32\*pow(10,18) balance as the node will not get sealing
(mining) rewards in POA.
If you want to create additional accounts you can use `createAccount`
or `createAccounts` method. Using a `createAccount`, you can create
an individual account customizing balance and password. On the other
hand, using a `createAccounts` method, you create a bulk of accounts
that have same amount of balance and a same password.

```python
# Create more accounts with Balance on e3 and e7
# Create one account with createAccount() method
# Create multiple accounts with createAccounts() method
e3.createAccount(balance= 32 * pow(10,18), password="admin")
e7.createAccounts(3, balance = 32*pow(10,18), password="admin")
```

## A.4 Importing Accounts

When you want to reuse an existing account, you can use `importAccount` method.

```python
# Import account with balance 0 on e2
e2.importAccount(keyfilePath='./resources/keyfile_to_import', password="admin", balance=10)
```

## A.5 Setting Geth Command Options

We use `go-ethereum;geth` software to run blockchains on emulator.
When the containers are up, they will install `geth` and run it with the command
which is generated from EthereumService Class. We can customized the
`geth start command` with the following methods.
The `base start command` is `geth --datadir {datadir} --identity="NODE_{node_id}" --networkid=10 --syncmode {syncmode} --snapshot={snapshot} --verbosity=2 --allow-insecure-unlock --port 30303 `

- `setNoDiscover()` = --nodiscover
- `enableGethHttp()` = --http --http.addr 0.0.0.0 --http.port 8545 --http.corsdomain "\*" --http.api web3,eth,debug,personal,net,clique
- `enableGethWs()` = --ws --ws.addr 0.0.0.0 --ws.port 8546 --ws.origins "\*" --ws.api web3,eth,debug,personal,net,clique
- `unlockAccounts()` = --unlock "{accounts}" --password "{accounts_passwords}"
- `startMiner()` = --mine --miner.threads=1
- `setSyncmode()` = --syncmode (snap|full|light)
- `setSnapshot()` = --snapshot (true|false)

You can also set further options using `setCustomGethCommandOption()` method.
The options will append to the `base start command`.

```python
# Start mining on e1,e2 and e5,e6
# To start mine(seal) in POA consensus, the account should be unlocked first.
e1.setBootNode(True).setBootNodeHttpPort(8090).startMiner()
e2.startMiner()
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Enable http connection on e3
# Set geth http port to 8540 (Default : 8545)
e3.enableGethHttp().setGethHttpPort(8540)

# Set custom geth command option on e4
# Possible to enable geth http using setCustomGethCommandOption() method
# instead of using enableGethHttp() method
e4.setCustomGethCommandOption("--http --http.addr 0.0.0.0")

# Enable ws connection on e5 geth
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)

# Set nodiscover option on e8 geth
e8.setNoDiscover()
```

<!-- ## A.6 Setting Custom Geth Binary

Occationally, it is needed to set customed `geth` binary instead of the original one
to conduct experiment. In this case, you can use `setCustomGeth()` method.

```python
# Set custom geth binary file instead of installing an original file.
e3.setCustomGeth("./resources/custom_geth")
```

## A.7 Setting Custom Genesis

If you want to deploy your customed genesis file on a blockchain,
you can set the customed genesis using the `setGenesis()` method.

```python
# Set custom genesis on e4 geth
e4.setGenesis(CustomGenesisFileContent)
``` -->

<a name="emulator"></a>

# Build Emulator with Blockchain

## B.1 Create the Blockchain Component

We create the Blockchain in `component-blockchain.py`. This
program generates a Ethereum component, which can be deployed
to any emulator that satisfy the requirements.
All the nodes in this layer are virtual nodes, and they are not
bound to any physical node.
This component is saved in a file (`component-blockchain.bin`).
Please refer to the comments in the code to understand
how the layer is built.

## B.2 Deploying the Blockchain

We deploy the blockchain in `blockchain.py`. It first loads two pre-built
components, a base-layer component and a blockchain component. The
base-layer component is from our mini-Internet example. It then uses
binding to bind each virtual node in the blockchain component to
a physical node in the base layer. Here we show an example:
it binds the virtual node `eth1` to a host inside the autonomous
system `AS-151` (letting the emulator code to pick one).

```python
emuA = Emulator()
emuB = Emulator()

emuA.load('../B00-mini-internet/base-component.bin')
emuB.load('./component-blockchain.bin')
emu = emuA.merge(emuB, DEFAULT_MERGERS)

emu.addBinding(Binding('eth1', filter = Filter(asn = 151)))
...
```

## B.4 Generate the Emulation Files and Set Up the Data Folders

After running the two Python programs (make sure to also run the B00 example
to generate the base layer first), we will get the `output` folder, which
contains all the Docker files for the emulation.

If we set `saveState=True` when creating the `EthereumService` object,
`eth-states` folder will be created automatically and
used to hold the blockchain data on each ethereum node.

## B.5 Start the Emulator

Now we can run the docker-compose commands inside the `output` folder
to build the containers and then start them.

```
// Inside the output folder
$ docker-compose build
$ docker-compose up
```

We can use our map tool to visualize the network. However,
Firefox is going to consume quite a bit of resources (CPU and RAM). It is better
to leave them to the Ethereum, which needs a lot of resources. Therefore,
we will access the containers from the terminal, instead of from the map.

We have added `Ethereum` to the names of the containers used as Ethereum nodes.
This way, we can easily list them:

```
$ docker ps --format "{{.ID}}  {{.Names}}" | grep Ether
647d9acd6317  as164h-Ethereum-4-10.164.0.71
c851ad76e79b  as170h-Ethereum-6-10.170.0.72
a0f23d5f995c  as150h-Ethereum-5-10.150.0.72
f6fb88f9e09d  as152h-Ethereum-2-10.152.0.79
91803d7a27c2  as163h-Ethereum-3-10.163.0.72
58fc02906a06  as151h-Ethereum-1-10.151.0.72
```

Let's get on one of the containers (e.g., `Ethereum-2`)

```
$ docker exec -it f6f /bin/bash;
root@f6fb88f9e09d / #
```

---

<a name="use-blockchain"></a>

# Use Blockchain

## C.1 Access the Blockchain Network

Once we are inside an Ethereum container, we can use the `geth`
command to access the Blockchain.

```
root@f6fb88f9e09d / # geth attach
Welcome to the Geth JavaScript console!

instance: Geth/NODE_2/v1.10.6-stable-576681f2/linux-amd64/go1.16.4
coinbase: 0x3e64b5b296ccb365eab980b094a4af7b1009825e
at block: 1010 (Sat Aug 07 2021 14:50:41 GMT+0000 (UTC))
 datadir: /root/.ethereum
 modules: admin:1.0 debug:1.0 eth:1.0 ethash:1.0 miner:1.0 ...

To exit, press ctrl-d
>
```

After the emulator starts, we need to wait for a while, 10 to 15 minutes, because
Ethereum takes time to initialize. During this period, mining will not start, so
we will not earn any ether. If we check the balance on any miner node,
we will get zero initially. If we see a non-zero value, that means the mining
has already started, and the blockchain is fully functional. It should be
noted that two of the ethereum nodes in our construction
are not miners (`Ethereum-5` and `Ethereum-6`),
so if you check their balance,
theirs will still be zero.

```
> eth.getBalance(eth.accounts[0])
0

... After waiting for a while ...
> eth.getBalance(eth.accounts[0])
527937500000000000000
```

## C.2 Get Account Numbers

A typical transaction involves sending some ethers from our account
to another account. First, we need to get the account numbers. All the
accounts created on an ethereum node can be found from `eth.accounts`.
We created only one account for some of the nodes, so we can
get it using `eth.accounts[0]`.

To use any account created on the node, we need to unlock it, because
the account data (including a private key) are password protected.
The password `admin` is hardcoded in the emulator.

```
> eth.accounts
["0x3e64b5b296ccb365eab980b094a4af7b1009825e"]

> my_account = eth.accounts[0]
> personal.unlockAccount(my_account, "admin")
true
```

We also need to know the recipient's account address. This can
be obtained from its host nodes (using `eth.accounts`).
We can also go to the `output/eth-states/N/keystore/` folder (N
should be replaced by the node number), because all the
accounts created on node `N` are stored in this folder.
The suffix of the file name is the account number (in hex format).

```
$ sudo ls output/eth-states/6/keystore/
UTC--2021-08-07T13-51-52.142916284Z--326025535363043c0ab13404ebafacb8947e420b
UTC--2021-08-07T13-52-20.060346038Z--c20ab9a1ab88c9fae8305b302836ee7734c6afbe
```

We select one of the accounts. Let's pick a non-mining node (the 2nd one),
so its balance is zero. We will send some ethers to this account.

```
> target_account = "0xc20ab9a1ab88c9fae8305b302836ee7734c6afbe"
> eth.getBalance(target_account)
0
> eth.getBalance(my_account)
897750000000000000000
```

## C.3 Create Transactions

Now from the geth console, we can create a transaction to send ethers to the target account.
After waiting for a few seconds, we check the balance again. We will
see that the target account's balance become `99999`, while the sender's account's
balance gets deducted.

```
> eth.sendTransaction ({from: my_account, to: target_account, value: "99999"})
"0xeb4037357ac55361fcf8cc824017a8b288e2daafb9534e20ecc5b2dd843927a8"

... After waiting for a while ...
> eth.getBalance(target_account)
99999
> eth.getBalance(my_account)
907749999999999900001
```

If you see an authentication error, it means that you forgot to unlock your
account, or the unlocking period has already expired (you need to unlock
it again).

## C.4 Get Transaction Information

The transaction hash value will be printed out after we run `eth.sendTransaction()`.
We can use this hash to get the details about this transaction.
It shows which block this transaction is added to.

```
> eth.getTransaction("0xeb4037357ac55361fcf8cc824017a8b288e2daafb9534e20ecc5b2dd843927a8")
{
  blockHash: "0x97a6bf80f154841eed4ef2cf8d5331a1dbd8a9974244f9c8bafc6468c027e60e",
  blockNumber: 1623,
  from: "0x3e64b5b296ccb365eab980b094a4af7b1009825e",
  gas: 21000,
  gasPrice: 1000000000,
  hash: "0xeb4037357ac55361fcf8cc824017a8b288e2daafb9534e20ecc5b2dd843927a8",
  input: "0x",
  nonce: 0,
  r: "0x726a04773111db213215ee96664ebdab3e3f0f5cad52bc7138e33234e689311f",
  s: "0x5f2567b002f0241087720e27e88e3b090f81e0d5e2e5452de7579b94b08037b7",
  to: "0xc20ab9a1ab88c9fae8305b302836ee7734c6afbe",
  transactionIndex: 0,
  type: "0x0",
  v: "0x37",
  value: 99999
}
```

---

<a name="smart-contract"></a>

# Smart Contract

## D.1 Example

In this example, we have provided an smart contract program
inside the `Contract/` folder. You can also write one yourself.
If you want to do that, you need to install the Solidity program,
and use it to compile your own program to `abi` and `bin` files.
Please install Solidity with
a version above 0.8.0. Installation can be
found [here](https://docs.soliditylang.org/en/v0.8.0/installing-solidity.html#linux-packages).
We can generate the `abi` and `bin` files using the following command.

```
solc --abi <filename.sol> | awk '/JSON ABI/{x=1}x' | sed 1d > contract.abi
solc --bin <filename.sol> | awk '/Binary:/{x=1;next}x' | sed 1d > contract.abi
```

## D.2 Deploy Smart Contract

To deploy a smart contract in the Emulator, we first need to create a
`SmartContract` object using the generated `abi` and `bin` files, and
then invoke the `deploySmartContract()` API on the node that
we want to use to deploy the contract.

```python
smart_contract = SmartContract("./Contracts/contract.bin", "./Contracts/contract.abi")
e3.deploySmartContract(smart_contract)
```

**Note:** To deploy a smart contract from an account, the account needs to have
enough ethers. When we first start the emulator, no account has any
ether, so the contract will not be deployed, until the mining gets
started (so nodes can earn ethers). Our emulator automatically checks
the balance before deploying the contract.
By default, if we are using our custom API, the minimum ethers required
to deploy a smart contract is 1000000 (in wei).
Our further development will make this value configurable.

## D.3 Get the Smart Contract Address

Once the contract is deployed, we can perform certain tasks on it.
The supplied program `contract.sol` acts as a bank account. We can
send ethers to this smart contract, and transfer the ethers from the contract
to any specified account (anybody can do this, as no security protection is
implemented in the contract).

In order to send ethers from an account to the smart contract,
we first need to get the address of the contract. When
the contract gets deployed onto the network (via a transaction),
the hash of the transaction is printed out, and our emulator
will save the hash to `/transaction.txt`. We need to go to
the contract-deploying node to get the hash value.

```
# cat /transaction.txt
{
  abi: [{
      inputs: [{...}, {...}],
      name: "claimFunds",
      outputs: [],
      stateMutability: "payable",
      type: "function"
  }, {
      stateMutability: "payable",
      type: "receive"
  }],
  address: undefined,
  transactionHash: "0x9b9cba041dc534ad030dde361c434ae001b3578625f7696644808596841c676a"
}
```

Using this transaction hash, we can get the transaction receipt,
which contains the address of the smart contract. This operation can be
done on any node.

```
# geth attach
> eth.getTransactionReceipt("0x9b9cba041dc534ad030dde361c434ae001b3578625f7696644808596841c676a")
{
  blockHash: "0xc1ef36addf70370838e1fdf2e7c6ccad189fbefcb51b46d74635744e37db9c3f",
  blockNumber: 2934,
  contractAddress: "0xfde00f58fbdcfaedf6ca086120d2f53e646e6cce",
  cumulativeGasUsed: 177433,
  effectiveGasPrice: 1000000000,
  from: "0xfdeb37243f2cd3111935fc284d3a092ce2cd11ca",
  gasUsed: 177433,
  logs: [],
  logsBloom: "0x0000000 ...(omitted) ...",
  status: "0x1",
  to: null,
  transactionHash: "0x9b9cba041dc534ad030dde361c434ae001b3578625f7696644808596841c676a",
  transactionIndex: 0,
  type: "0x0"
}
```

## D.4 Send Ethers to Contract

We can treat the contract as a bank account, and can send ethers to this account.
This is similar to sending ethers to a normal account. All we need to do is to
create a transaction.

```
> contract = "0xfde00f58fbdcfaedf6ca086120d2f53e646e6cce"
> my_account = eth.accounts[0]
> personal.unlockAccount(my_account, "admin")
> eth.getBalance(contract)
0
> eth.sendTransaction ({from: my_account, to: contract, value: "555555"})
> eth.getBalance(contract)
555555
```

**Note:** It takes a little bit of time for the transaction to be added to the blockchain.

## D.5 Invoke Smart Contract APIs

To invoke the APIs in a smart contract is little bit more complicated. Let us look
at the source code of the smart contract example (in `Contracts/contract.sol`).

```solidity
contract Crowdfunding {
    uint256 amount;

    receive() external payable {
        amount += msg.value;
    }

    function claimFunds(address payable _to, uint _amount) public payable {
        _to.transfer(_amount);
    }
}
```

This program has a `claimFunds()` API, which sends ethers
from the contract's account to any specified target account. It can be invoked
by anybody. If we want to limit who can invoke the API, we can easily
add it to the program (not included in this example). We will show how
to invoke this API to claim funds.

- Step 1: First, we need to re-create the contract object, so that we can
  invoke its APIs. We will copy the content from the contract's `abi` file
  and assign it to a varaible (called `abi` in the example).
  Then, using the address of the contract, we can create the contract object.

  ```js
  abi = [
    {
      inputs: [
        { internalType: "address payable", name: "_to", type: "address" },
        { internalType: "uint256", name: "_amount", type: "uint256" },
      ],
      name: "claimFunds",
      outputs: [],
      stateMutability: "payable",
      type: "function",
    },
    { stateMutability: "payable", type: "receive" },
  ];

  addr_contract = "0xfde00f58fbdcfaedf6ca086120d2f53e646e6cce";
  contract = eth.contract(abi).at(addr_contract);
  ```

- Step 2: Invoking a smart contract API will generate a transaction
  using the account number contained in `eth.defaultAccount`. Therefore,
  we will assign our account number to this variable, unlock the
  acount, before invoking the API.

  ```js
  target_account = "0xc20ab9a1ab88c9fae8305b302836ee7734c6afbe";
  eth.defaultAccount = eth.accounts[0];
  personal.unlockAccount(eth.accounts[0], "admin");
  contract.claimFunds(target_account, 300000);
  ```

  **Note:** The account that is used to send this transaction needs to
  pay for the gas incured by the transaction. Therefore, the account
  should have enough ethers, otherwise the transaction will fail.

- Verification: Before and after invoking the API, we can check the balance
  of the smart contract address and the target account address. We will see
  their balances have changed.

  ```
  // Before invoking claimFunds()
  > eth.getBalance(target_account)
  99999
  > eth.getBalance(contract)
  555555

  // After invoking claimFunds()
  > eth.getBalance(target_account)
  399999
  > eth.getBalance(addr_contract)
  255555
  ```

---

<a name="smart-contract-manual"></a>

# Manually Deploy Smart Contract

If you want to manually deploy a smart contract, you just
need to get the `abi` and `bin` file from the smart contract.
The bytecode of the contract is in the `bin` file.

```js
abi = [
  {
    inputs: [
      { internalType: "address payable", name: "_to", type: "address" },
      { internalType: "uint256", name: "_amount", type: "uint256" },
    ],
    name: "claimFunds",
    outputs: [],
    stateMutability: "payable",
    type: "function",
  },
  { stateMutability: "payable", type: "receive" },
];

byteCode =
  "0x608060405234801561001057600080fd5b50610241806100206000396000f3fe6080604052600436106100225760003560e01c8063ed2b40ea1461004657610041565b3661004157346000808282546100389190610117565b92505081905550005b600080fd5b610060600480360381019061005b91906100d7565b610062565b005b8173ffffffffffffffffffffffffffffffffffffffff166108fc829081150290604051600060405180830381858888f193505050501580156100a8573d6000803e3d6000fd5b505050565b6000813590506100bc816101dd565b92915050565b6000813590506100d1816101f4565b92915050565b600080604083850312156100ee576100ed6101d8565b5b60006100fc858286016100ad565b925050602061010d858286016100c2565b9150509250929050565b60006101228261019f565b915061012d8361019f565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff03821115610162576101616101a9565b5b828201905092915050565b60006101788261017f565b9050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b6000819050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b600080fd5b6101e68161016d565b81146101f157600080fd5b50565b6101fd8161019f565b811461020857600080fd5b5056fea2646970667358221220fd0adefc15077d6244e347b29105d839828d14848f48b094229c6fa0c021715d64736f6c63430008060033";

personal.unlockAccount(eth.accounts[0], "admin");
eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000 });
```

The last statement above will generate a transaction, and miners will add
this smart contract to the blockchain. We can further get the address
of the smart contract using the transaction hash printed out
by the last statement:

```
{
  abi: [{
      inputs: [{...}, {...}],
      name: "claimFunds",
      outputs: [],
      stateMutability: "payable",
      type: "function"
  }, {
      stateMutability: "payable",
      type: "receive"
  }],
  address: undefined,
  transactionHash: "0x261c6079f1b18c16b4252f6e60d44c561303f5f686d24a2531588df992cc20eb"
}
```
