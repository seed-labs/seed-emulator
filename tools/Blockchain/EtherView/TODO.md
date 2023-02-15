# Todo List

## Should do it soon 

- We need another view to display all the transactions inside 
  a block (not finished yet).

- Several items in the `config.py` needs to be set
  automatically from the emulator, including
  `CONSENSUS` and `DEFAULT_URL`.

- Right now, we are using the `ETH_NODE_NAME_PATTERN`  
  to identify which container is an Ethereum node. 
  We should use the container meta data to replace this.

- Use the time stamp from the 1st block to decide whether 
  we should recreate the json files in the `emulator_data` 
  folder. 


## Will take a while 

- The style used in the program does not looks good.
  We need to fine tune it or find a better one. 


- Transaction view: use tabs for choosing transaction content and 
  transaction receipts. 

- On each view, we should display the following information:
  - chain id selection, provider selection
  - consensus, number of nodes 
  - When clicking on the number of nodes, we should switch to the InternetMap
    app (should we call it InternetView? to be consistent with EtherView).


- POA and POS related features. Whether to display these menus depend
  on the context: they should not appear when the blockchain is not
  their type. 





