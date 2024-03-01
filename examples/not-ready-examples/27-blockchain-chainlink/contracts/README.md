## Contracts
This directory contains the Chainlink contracts. The contracts are written in Solidity. The contracts are divided into the following categories:
1. Link Token:
    - The Link Token contract is an ERC677 token that is used to pay for services on the Chainlink network. The contract can be found on github [LinkToken.sol](https://github.com/smartcontractkit/LinkToken/blob/master/contracts/v0.4/LinkToken.sol)
    - The contract can be deployed using this [file](./deploy_linktoken_contract.py) it requires link_token.abi and link_token.bin files which is compiled from the LinkToken.sol file
    - Change RPC url and private key as per the requirement
    - The contract will be deployed and the address will be printed on the console
    - Open metamask and add the contract address in import token
2. Operator Contract:
    - The Operator contract is used to manage the Chainlink network. The contract can be found on github [here](https://github.com/smartcontractkit/chainlink/blob/develop/contracts/src/v0.7/Operator.sol)
3. Aggregator Chainlink Contract:
    - The Aggregator contract is used to aggregate data from multiple chainlink nodes. [This](./AggregateChainlinkData.sol) file contains the contract for the Aggregator