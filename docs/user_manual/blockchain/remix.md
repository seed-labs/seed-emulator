# Connect Remix to SEED Emulator

Remix IDE (Integrated Development Environment) can be
used to write, compile, and debug the Solidity code.
It supports testing, debugging and deploying smart contracts.
In this manual, we show how to connect it to the SEED emulator. 


## Step 1: Open Remix IDE

We use Remix online IDE, so we do not need to install anything.
Simply go to [https://remix.ethereum.org/](https://remix.ethereum.org/), 
and you will get the Remix IDE. Remix provides excellent instructions on
[how to use the IDE](https://remix-ide.readthedocs.io/).


## Step 2: Set Up MetaMask

Remix can connect to blockchains via several mechanisms,
such as Remix VM, injected provider (MetaMask), and external HTTP
providers. The Remix VM is sandbox blockchain in the browser;
it is a blockchain simulator, not a real blockchain.
We will connect Remix to our SEED blockchain emulator, which
is a real blockchain. This can be done using an injected
provider (such as MetaMask) or an external HTTP provider.
We will use the MetaMask approach because we would like
to use MetaMask to manage our accounts. 
Please follow this instruction to 
[set up MetaMask and connect it to the SEED emulator](./metamask.md). 


## Step 3: Choose EVM Version in Remix

Go to the Remix IDE, in the `"Solidity Compiler"` menu, click
the `"Advanced Configurations"` drop-down menu, set the following:
```
Language: Solidity
EVM Version: paris
```

A new OP code `PUSH0` was introduced in
[EIP-3855](https://eips.ethereum.org/EIPS/eip-3855), which
and was included in the Shanghai upgrade. Our Ethereum docker image was
built before the Shanghai upgrade, so it will not work with
the upgrade. Before we upgrading our image, we need to use 
an older EVM version, such as `paris`. 

To compile the smart contract using the command line tool,
such as `solc`, we also need to use the solidity compiler version 
`0.8.18` or lower, or the contract deployed to the emulator
will have problems.


## Step 4: Connect Remix to MetaMask

In the Remix IDE, go to the `"Deploy & Run Transactions"` menu,
set the `Environment` to `"Injected Provider - MetaMask"`.
If everything is set up correctly, in the `Account` drop-down menu,
you should be able to see the list of accounts from your 
MetaMask wallet. 

Whenever we need to send transactions to the SEED blockchain
from Remix, such as deploying a contract or invoking 
a contract function, Remix will communicate with 
MetaMask, which sends the transactions for us using 
the accounts (their private keys) in the wallet. 
When sending a transaction from Remix, MetaMask window will show 
up, asking for confirmation. 


## Potential Problems

- Some users found that when they deploy smart contract from Remix,
  it takes a long time for the MetaMask to come up. This is not a 
  problem of the emulator, because the problem is the same when they
  connect to a test net. After changing the VM's network setting 
  from NAT to the bridge mode, the problem is gone. Most users 
  do not have this issue using the NAT mode, so this might be isolated
  issue caused by the user's network environment. 


