# Deploy contract

------------------------------------------------------
Note: We try to develop a way to deploy contract directly 
into the genesis block, because we can set the contract
address. Using this approach, the constructor will not be invoked,
so we need to explicitly initialize variables that are 
typically done inside the constructor. 
However, it seems that calculating where variables are 
stored is quite complicated, and may not worth the time 
to do this (we can deploy contracts using another method).
Therefore, this example is incomplete. 

------------------------------------------------------

Smart contract deployment has to be done at the run time, instead
of the build time. In this example, we show how to
set up the contract deployment at the build time, so when the emulator
starts, the contract can be automatically deployed.

## Using the genesis block
To deploy a contract at runtime, we need to include the contract's bytecode in the genesis block. Below is an example setup.

## Emulator Setup

### Compiling the contract
To deploy the smart contract using the genesis block, we need to compile the contract using the `solc` compiler. The smart contract should be compiled with the flag `--bin-runtime` to generate the runtime bytecode, which is necessary for deployment.

Run the following command in your terminal to compile the contract:

```bash
cd Contracts
solc --bin-runtime --abi --evm-version paris contract.sol -o .
```
- `solc`: The Solidity compiler.
- `--bin-runtime`: Generates the runtime bytecode for the contract.
- `--abi`: Generates the Application Binary Interface (ABI) for the contract.
- `contract.sol`: The Solidity source file to compile.
- `-o .`: Specifies the current directory as the output directory.

By using the runtime bytecode, we ensure that the contract's constructor and initialization data are not included in the deployment process, making it suitable for deployment in the genesis block.

### Building the Emulator
1. Get the blockchain component from the pre-defined ethereum_poa
    ```python
    # Get the blockchain information
    eth: EthereumService = emu.getLayer("EthereumService")
    blockchain: Blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
    ```
2. Load the runtime bytecode from the Contracts folder
    ```python
    with open("./Contracts/Contract.bin-runtime", "r") as f:
        runtime_bytecode = Web3.toHex(hexstr=f.read().strip())
    ```
3. Add a local account in the genesis with the runtime bytecode
    - Define a specific address to be used as the contract address. This address is derived from a predefined mnemonic phrase for consistency and reproducibility.
    ```python
    # This account has been generated from the mnemonic phrase: "gentle always fun glass foster produce north tail security list example gain"
    # We will use this as a contract address for the contract deployment using genesis block
    contract_address = "0xA08Ae0519125194cB516d72402a00A76d0126Af8"
    blockchain.addLocalAccount(contract_address, balance=0)

    # Add the runtime bytecode with the contract address in the genesis block
    blockchain.addCode(contract_address, runtime_bytecode)
    ```
4. Add storage for the contract
  - In Ethereum, contracts deployed directly into the genesis block don't execute constructors, hence initial states must be set manually. This involves specifying the contract's storage in the genesis block. For example, to allocate tokens to a contract owner in an ERC20 setup, the balance storage slot for the owner's address must be explicitly defined and set within the genesis configuration. This process ensures the contract is operational with predetermined states from the start.
  
  ```python
  # Set initial storage for the contract
  blockchain.addStorage(contract_address=contract_address, owner_address=contract_address, slot=0, value=1000000)
    
  custom_address = "0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9"
  blockchain.addStorage(contract_address=contract_address, owner_address=custom_address, slot=0, value=50000)
  ```

## Genesis Block Configuration
The `alloc` section in the genesis block configuration includes account addresses and their corresponding initial balances. To deploy a contract at runtime, we add an account with a zero balance and include the contract's runtime bytecode in the `code` field. The contract's storage is also defined in the `storage` section.

```json
"alloc": {
    "F5406927254d2dA7F7c28A61191e3Ff1f2400fe9": {
      "balance": "30000000000000000000"
    },
    "2e2e3a61daC1A2056d9304F79C168cD16aAa88e9": {
      "balance": "9999999000000000000000000"
    },
    "CBF1e330F0abD5c1ac979CF2B2B874cfD4902E24": {
      "balance": "10000000000000000000"
    },
    "A08Ae0519125194cB516d72402a00A76d0126Af8": {
      "balance": "0",
      "code": "0x608060405234801561000f575f80fd5b506004361061009c575f3560e01c8063313ce56711610064578063313...",
      "storage": {
        "0xa382bf1969e805728659671dc63868739e5720caddee9562fe4801ea1cdf9415": "00000000000000000000000000000000000000000000000000000000000f4240",
        "0x97e6456d61b2840173338dadfa57884bf553678864475c04ed778feb0f880faf": "000000000000000000000000000000000000000000000000000000000000c350"
      }
    }
}
```

## Test the contract deployment
To test if the contract has been deployed successfully use the script provided:

  ```bash
  python3 test_deployment.py
  ```

### Expected output:
  ```bash
  Connected to Ethereum node successfully
  Contract is deployed successfully
  Total supply: 200000000000000000000000
  Checking the initial balance of the accounts...
  Balance of account 0xA08Ae0519125194cB516d72402a00A76d0126Af8: 1000000
  Balance of account 0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9: 50000
  Transferring 100 tokens from account 2 to account 1...
  Balance after transaction:
  Balance of account 0xA08Ae0519125194cB516d72402a00A76d0126Af8: 1000100
  Balance of account 0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9: 49900
```
