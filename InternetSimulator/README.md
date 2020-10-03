Internet Simulator
---

The goal of this project is to build a simulator of the Internet, containing necessary components that will enable us to build replicas of the real-world Internet infrastructure. 

We can already experiment with small-scale attacks like ARP poisoning, TCP hijacking, and DNS poisoning, but our goal is to provide a simulation where users are allowed to conduct attacks on a macroscopic level. The simulation will enable users to launch attacks against the entire Internet. The simulator for the Internet allows users to experiment with various Internet technologies that people usually would not have access to, like BGP. This simulator will enable users to perform a nation-level BGP hijack to bring down the Internet for an entire nation, perform MITM on a core ISP router, or launch DNS poisoning attacks on the TLD name servers.

Users can join the simulated Internet with VPN client software. This simulation is completely transparent to users joining it, allowing many different possibilities. This allows users to conduct and experience in real-time, as if it was happening in the real world. Simulation is popular in every field of engineering, especially for those activities that are expensive or dangerous to conduct. However, popular Internet simulators usually do not do well in a real-time application, as they are mainly designed to be used for research and runs slow. Also, lots of no-for-research-use simulators have very high system requirements, rendering them unfeasible for large-scale simulations.

### Design

The simulator is built from four components: 

- Core classes, which provide the essential abstraction of the key simulator components like Network, Network Interface Card, Node (Router and Server),
- Layers, which provide a high-level API for building the simulation on different levels,
- Renderer, which "renders" the different layer and build a complete simulation, and
- Compiler, which "compiles" the product from renderer to actual simulation.

#### Core classes

TODO

#### Layers

**Base Layer**. We do need to have a base layer. This layer is the barebone setup. Considering this layer as the hardware layer. We use cable, switches, and routers to create and connect networks. However, nothing is set up on the routers yet. Setting up the routers is done through a routing protocol layer. Routers inside an IXP are automatically considered as BGP routers.

**BGP Layer** If we want to add BGP to the network, we create a BGP layer. In this layer, we configure all the BGP routers specified in this layer (or all the BGP routers in the base layer). The base layer has APIs for enumerating all the BGP routers and other components, such as ASes, networks, internal routers for an AS, etc. What this layer does is to specify the peering relationship, add BGP services and the corresponding configuration (based on peerings) to each BGP routers. This layer is for EBGP only.

**IBGP Layer**. If we want to run an IBGP inside an AS, we can create an IBGP layer for an AS, and then configure all the involved BGP routers. 

**OSPF Layer**. If we want to add OSPF to the internal routers of an AS, we can create an OSPF layer for that AS. In this layer, we configure the routers for each of the machines on this layer. 

#### Renderer

TODO

#### Compiler

TODO

### Layers

#### Base

TODO

#### Routing

TODO

#### Ebgp

TODO

#### Ibgp

TODO

#### WebService

TODO
