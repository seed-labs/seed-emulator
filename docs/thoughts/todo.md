# TODO List

This document lists some of the features that we should consider
in our future release


## Core 

- Service: add `getVNodes` API, so we can get a list of all the 
  vnodes (names) added to a service. 


## Service



## Blockchain

- Every time I run the D00 example, the program will generate the accounts,
  which takes a long time. Is it possible to provide an option to save the 
  accounts in a local folder (cache), and allow the programs to directly
  load them from the cache, instead of regenerating them.

- In blockchain, we often need to create a special node to do the following
  things. We may think about adding this to the blockchain. 

  - Deploy smart contract (the contract is provided during the build time). 
  - Provide runtime information to others (via a http server). For the contract
    deployed by this special node or by other nodes, the address needs to
    be provided to others. This special server can be a place to store
    the information, as well as providing the query service.

- The Ethereum software has been evolving. Our pre-built container image is 
  still based on the old version. We need to think about how to support the 
  newer versions of Ethereum, how to support such an upgrading effort, 
  and how frequently we should do the upgrading, etc. This is a long-term 
  effort. 
