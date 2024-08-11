# Common Problems 


## Smart Contract 

- Solidity compiler version: On Remix, once we select the `paris`
  EVM version, the solidity compiler version will be set accordingly (to
  `0.8.18`). However, if we compile a contract directly from
  the command line using `solc`, the solidity compiler version installed
  in the system may be higher than `0.8.18`. 
  Deploying a contract compiled using a version more recent than
  `0.8.18` to the emulator will cause problems.
  Before we upgrade the version of Ethereum in the emulator,
  we need to use an older version of the solidity compiler ( 
  (Version `0.8.18` can be downloaded 
   [here](https://github.com/ethereum/solidity/releases/tag/v0.8.18)).
  Moreover, we need to set the `pragma` of the contract program to the following:
  ```
  pragma solidity <0.8.19;
  ```

