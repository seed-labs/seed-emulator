# Tools for Interacting with Blockchain

This folder contains programs that can be used to interact with the blockchain.
They use the libraries that we developed. 


## Setup 

Most of these tools import the variables defined in `emulator_setup.py`, 
which provide the essential emulator parameters, such as
sender's address and key, address of contract, and the URLs of the Faucet server, 
Utility server, and `geth` server. Users need to manually set the
content of this file based on the emulator setup. 


## Tools

These are basic tools that can be used to interact with the blockchain emulator.

- `create_account <total>`: create `<total>` number of accounts from a pre-defined 
  mnemonic phrase.  

- `print_balance.py <account>`: print out the balance of the specified account

- `get_fund.py <account>`: use the Faucet server to fund the specified account

- `send_fund.py <account>`: transfer fund from the sender to
  an account. The sender's account and private key information is imported
  from `emulator_setup.py`. 

- `deploy_contract.py args ...`: deploy a contract.  The sender's information
  is imported from `emlator_setup.py`. The contract name and location are also
  in `emulator_setup.py`. The arguments are for the constructor. 
  After the contract is deployed, the contract name is 

- `invoke_contract.py <function_name> args ...`: invoke the function of a deployed 
  contract. The length of the `args` list must match with the number of 
  parameters of the function.  The sender address/key
  are imported from `emulator_setup.py`. The contract address is obtained from
  the Utility server. 

  
