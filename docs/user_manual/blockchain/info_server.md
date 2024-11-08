# Use A Server to Share Information

When a contract is deployed, its address needs to be known to those
who want to invoke the contract. In our emulator, this needs to be
automated. This was the main reason why we added an information
server to the blockchain. It is called `EthInitAndInfo` server,
which serves two purposes: for initialization (such as deploying
contract) and for information sharing.

Right now, the information server is mainly used for publishing
contract address. In the future, we will add more APIs to share 
other type of information.

To learn how to use this information server, please 
see [this example](../../../examples/blockchain/D21_deploy_contracts)



