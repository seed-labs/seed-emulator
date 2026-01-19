# EtherView 2.0


## Overview 

EtherView is a collection of tools that can be used to 
interact with the Ethereum emulator. It has the following
features:

- Viewing the balances for the built-in accounts
- Viewing blocks and transactions (like EtherScan)
- Visualizing) interesting blockchain properties, such as
  - base fee
  - transaction pools on each node 
- Future work: Displaying POS related information
- Future work: Displaying the network topology (peers)
- Future work: Sample dApps. We should host some open-source dApps. Each dApp
  is built into a container. They can be included when the emulator
  is built. When EtherView detects it, the corresponding menu
  will appear, leading us to the dApp. More thinking is needed
  for this feature. 

## Building Image

We use the following command to build and push the image to Docker Hub

```
docker buildx build --push -t handsonsecurity/seedemu-multiarch-etherview:2.0 .
```
 

