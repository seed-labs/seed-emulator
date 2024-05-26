# Internet Emulator: Components and Advanced Features


## Advanced Features 

  - [Connect to the real world](../bgp.md#connect-to-realworld): Set up the BGP routing
    so the nodes inside the emulator can communicate with the real Internet. 
  - [Allow outside machines to join the emulation](../../../examples/basic/A03_real_world/):
    This example shows how the outside machines (physical or virtual) can 
    join the emulation via a layer-2 VPN.
  - [Support Apple Silicon machines (arm64)](../docker.md#platform): Generate emulator
    files for Apple Silicon machines. 
  - [Hybrid Emulation 1: including physical devices](../../../examples/internet/B50_bring_your_own_internet/)
  - Hybrid Emulation 2: including virtual devices running on QEMU: work in progress


## Components

  - [Build DNS Infrastructure](../../../examples/internet/B01_dns_component/) and
    [Add DNS to Emulator](../../../examples/internet/B02_mini_internet_with_dns)  
  - [IP anycast](../../../examples/internet/B24_ip_anycast/)
  - [DHCP server](../../../examples/internet/B20_dhcp/)
  - [Botnet](../../../examples/internet/B22_botnet/)
  - [Darknet (Tor)](../../../examples/internet/B23_darknet_tor/)
  - [The Hosts file (add IP-hostname mappings)](../../../examples/internet/B21_etc_hosts/): 
    This example shows how to add ip-hostname mappings to the `/etc/hosts` file. With this,
    we can use hostnames instead of IP addresses. 
  - [Public Key Infrastructure (PKI)](./ca.md): Set up a PKI inside the emulator.  
  - [IPFS (InterPlanetary File System)](../../../examples/internet/B26_ipfs_kubo):
    This example shows how to set up an IPFS file system in the emulator. 
  - [IPFS Kubo](./kubo.md)

