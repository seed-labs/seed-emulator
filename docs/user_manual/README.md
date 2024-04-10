# User Manual for the SEED Emulator

We have plenty of examples to demonstrate the usages of the SEED emulator.
This document provides a portal to those examples.


## Internet Emulator: Manuals for Each Element

  - [Create an emulator: the overall flow](./overall_flow.md)
  - [Autonomous system](./as.md)
  - [Internet exchange](./internet_exchange.md)
  - [BGP routers and Peering](./bgp.md) 
  - [Routing](./routing.md) 
  - [Node and its customization](./node.md)
  - [Component and Binding](./component.md) 
  - [Compilation](./compiler.md) 
  - [Visualization](./visualization.md)
  - [Docker image](./docker.md)


## Internet Emulator: Manuals for Specific Features

  - [Build DNS Infrastructure](../../examples/B01-dns-component/) and
    [Add DNS to Emulator](../../examples/B02-mini-internet-with-dns)  
  - [Connect to the real world](./bgp.md#connect-to-realworld): set up the BGP routing
    so the nodes inside the emulator can communicate with the real Internet. 
  - [IP anycast](../../examples/B03-ip-anycast/)
  - [Add DHCP server](../../examples/B10-dhcp/)
  - [Support Apple Silicon machines (arm64)](./docker.md#platform): generate emulator
    files for Apple Silicon machines. 
  - [Hybrid Emulation: integrating physical devices in emulation](../../examples/C03-bring-your-own-internet/)
  - [The Hosts file (add IP-hostname mappings)](../../examples/B11-etc-hosts/): inside the
    emulator, we add ip-hostname mappings to the `/etc/hosts` file. 
  - [Add Public Key Infrastructure (PKI)](../../examples/)
  - [IPFS (InterPlanetary File System)](../../examples/)


## Internet Emulator: Additional Services
  - [IPFS Kubo](./kubo.md)


## Blockchain Emulator
  
  - [Build a Blockchain Emulator](../../examples/B06-blockchain/)
  - [Connect MetaMask to SEED Emulator](https://github.com/seed-labs/seed-labs/blob/master/manuals/emulator/metamask.md)
  - [Connect Remix to SEED Emulator](https://github.com/seed-labs/seed-labs/blob/master/manuals/emulator/remix.md)
  - [Use Faucet to Fund Accounts](../../examples/)
  - [Use Chainlink to Get Information From Outside](../../examples/)


## Frequently Asked Questions (FAQ)

  - Install python package
  - AMD issue
  - How to use custom docker image
