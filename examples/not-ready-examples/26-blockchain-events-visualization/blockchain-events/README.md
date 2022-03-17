# Status
- Not ready to be merged to master.
- Still in development.
- For Haotong Wang  to use as a base for the visualization.

# Notes for Haotong Wang
- This code was never merged because it was still in development.
- This code is the base for the blockchain visualization. We successfully capture events from our blockchain network.
- The main file is the `index.js`.
- It first creates a map between container ids and ethereum accounts.
- When all accounts are mapped, we set listeners inside the emulator blockchain network using web3.
- The first few lines connect to our ethereum nodes using web3.
- Make sure to check which ports are open for connection inside `component-blockchain.py` or the code will break.

# Todos, tasks, and ideas
- Since this code was still experimental and in development, it can be cleaned up. Remove the unused functions and dependencies.
- Go to `https://web3js.readthedocs.io/en/v1.2.11/web3-eth-subscribe.html` and select the necessary information we can extract from the events we currently listen to: `pendingTransactions` and `newBlockHeaders`.
- Visualize the event data using the map (e.g. if account 1 in container 1 is sending data to account 2 in container 2, maybe we can blink the whole path from container 1 to container 2)
- web3 also supports an API called `clearSubscriptions` where you can stop all your listeners (in our case both events i mentioned above). Maybe you can trigger it through the UI too to avoid wasting resources when we don't want to visualize the blockchain anymore.
- On the map we want to be able to differentiate miners/sealers from other nodes
- On the map we want to be able to identify bootnodes from other nodes
- There are 2 types of transactions in ethereum, sending ether and deploying/interacting with a smart contract. Maybe we can differentiate between them too.
- enjoy :))
