# Internet Emulator

The goal of this project is to build a emulator of the Internet, containing necessary components that will enable us to build replicas of the real-world Internet infrastructure. 

We can already experiment with small-scale attacks like ARP poisoning, TCP hijacking, and DNS poisoning, but our goal is to provide a emulation where users are allowed to conduct attacks on a macroscopic level. The emulation will enable users to launch attacks against the entire Internet. The emulator for the Internet allows users to experiment with various Internet technologies that people usually would not have access to, like BGP. This emulator will enable users to perform a nation-level BGP hijack to bring down the Internet for an entire nation, perform MITM on a core ISP router, or launch DNS poisoning attacks on the TLD name servers.

Users can join the simulated Internet with VPN client software. This emulation is completely transparent to users joining it, allowing many different possibilities. This allows users to conduct and experience in real-time, as if it was happening in the real world. Simulation is popular in every field of engineering, especially for those activities that are expensive or dangerous to conduct. However, popular Internet emulators usually do not do well in a real-time application, as they are mainly designed to be used for research and runs slow. Also, lots of no-for-research-use emulators have very high system requirements, rendering them unfeasible for large-scale emulations.

## Table of Contents

   * [Internet Emulator](#internet-emulator)
      * [Table of Contents](#table-of-contents)
      * [Design](#design)
      * [Case study](#case-study)
         * [BGP peering](#bgp-peering)
         * [Transit provider](#transit-provider)
         * [MPLS transit provider](#mpls-transit-provider)
         * [Fun with DNS](#fun-with-dns)
            * [DNS infrastructure](#dns-infrastructure)
            * [Local DNS](#local-dns)
            * [DNSSEC](#dnssec)
            * [Reverse domain name and IP origin](#reverse-domain-name-and-ip-origin)
         * [A miniature internet](#a-miniature-internet)
         * [Botnet](#botnet)
         * [Bitcoin](#bitcoin)
      * [Advance topics](#advance-topics)
         * [Hook into the rendering](#hook-into-the-rendering)
         * [Buliding new compiler](#buliding-new-compiler)
         * [Buliding new service](#buliding-new-service)
         * [Buliding new layer](#buliding-new-layer)
         * [Creating new graphs](#creating-new-graphs)


## Design

See [design.md](design.md)

## Case study

### BGP peering

### Transit provider

### MPLS transit provider

### Fun with DNS

#### DNS infrastructure

#### Local DNS

#### DNSSEC

#### Reverse domain name and IP origin

### A miniature internet

### Botnet

[Botnet Document](botnet.md)

### Bitcoin

## Advance topics

### Hook into the rendering

### Buliding new compiler

### Buliding new service

### Buliding new layer

### Creating new graphs

