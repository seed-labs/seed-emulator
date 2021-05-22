# Design

   * [Design](#design)
      * [Overview](#overview)
      * [Layers](#layers)
         * [Services](#services)
         * [Included layers](#included-layers)
            * [The Base layer](#the-base-layer)
            * [Routing layers](#routing-layers)
            * [Infrastructure layers](#infrastructure-layers)
            * [Service and application layers](#service-and-application-layers)
            * [Other layers](#other-layers)
         * [Implementation](#implementation)
            * [Rendering layers](#rendering-layers)
            * [Configuring layers](#configuring-layers)
      * [Graphing](#graphing)
      * [Compilers](#compilers)
         * [Included compilers](#included-compilers)
            * [Docker](#docker)
            * [Docker (Distributed)](#docker-distributed)
            * [Docker (Distributed) (GCP)](#docker-distributed-gcp)
            * [Graphviz](#graphviz)
         * [Implementation](#implementation-1)
      * [Merging Emulators](#merging-emulators)
         * [Exporting emulation](#exporting-emulation)
         * [Importing emulation](#importing-emulation)
         * [Merging emulation](#merging-emulation)
            * [Conflict resolution](#conflict-resolution)
            * [Custom merge actions](#custom-merge-actions)

## Overview

Unlike traditional emulators, this emulator is based on the idea of layers. Each layer holds part of the information required for building a emulation scenario. Layers are independent of each other, meaning users can take a layer from one emulation scenario and put it into another.

## Layers

Every component is a layer. The base of the emulation is the `Base` layer, and the other layers, like `Routing`, `Bgp`, `Ospf`, `Mpls` and `DomainNameService` add different components to the emulation.  `Base` layer, for example, describes the base of the emulation: what autonomous systems (AS) and internet exchanges (IX) are in the emulator, what nodes and networks are in each of the AS, and how nodes are connected with networks. `Bgp` layer, on the other hand, describes how ASes and where are peered with each other, and what's the relationship between the peers.

Each layer only takes care of its' own matter. BGP layer only saves what autonomous systems are peered with what autonomous system, and what internet exchange. It doesn't care how or where the router node actually is; as long as the information matched (correct IX, correct peer ASN), it will configure the peering between them. DNS layer only saves what zones are hosted on which node with their IP address or name, meaning one can build a DNS infrastructure with DNS layer in one emulation and easily export it and re-use the same infrastructure in a emulation with entirely different BGP peerings and layer two topologies, given that they re-create nodes with the same name in the other emulation. In other words, layers will have no knowledge of what or how other layers are configured prior to the render stage. Layers must keep track of the changes they try to make internally within the class.

### Services

Services are special kinds of layers. One way to differentiate the regular layers and services layer is their scope. A regular Layer makes changes to the entire emulation (like BGP, which configure peeing across multiple different autonomous systems, exchanges, and routers). In contrast, a service only makes changes to individual nodes (like `Web`, which install `nginx` on the given node). 

In the old design, services are installed by providing the node object to the services. In the new design, we decided not to use any node object to identify which node to install the services on, as that creates dependencies to the base layer, as mentioned in the previous section. In the new design, we use the node's name and IP address to identify nodes to install service on. And in fact, the `Service` class itself is derived from the `Layer` class and it just adds a few helper functions to make developing new services easier:

- `Service::installByName(asn: int, nodename: str)`: install service on the node with `nodename` in AS `asn`.
- `Service::installByIp(address: str, asn: int = None)`: install service on the node with IP address `address`, optionally limit the ASN to `asn`.
- `Service::installIf(cond: Callable[[Node], bool])`: install the service on a node if the function or lambda returns true for the node object passed in. Examples:
   - `service.installIf(lambda node: node.getAsn() == 150)`: install on first node in AS150.
   - `service.installIf(lambda node: not node.getAttribute('services').keys.has('DomainNameService')`: install on first node in any AS, that does not have `DomainNameService` installed on them.

The `Service` layer will keep track of what nodes are pending service configuration / installation and will do the proper configuration / installation during the configure and render stage. 

To create a new `service`, only the `_createServer` method needs to be implemented by the derived class. The `_createServer` takes no parameters and should return a class object derived from the `Server` class. Only one method needs to be implemented for the `Server` class, `install`, which takes only one parameter, the node object to install the server on. Developers can implement additional methods on the derived `Server` for configuring the server-specific settings; for example, there's a `setPort` method in the `WebServer` class, which allows users to change the listen port of the webserver.

Derived `Service` layer can alternatively implement the following methods to change how servers are installed and configured:

- `_doInstall(server: Server, node: Node)`: change how servers are installed. By default, this calls `server.install(node)`. Servers are installed during the render stage. 
- `_doConfigure(server: Server, node: Node)`: change how servers are configured. This is called during the configure stage, and by default, this does nothing.

As a single server object is typically installed only on one node, the `_doInstall` and `_doConfigure` method only passes in the `Node` object. However, sometimes the service layer may need to gather information from the entire emulation, instead of from just the node it tries to install the services on. An example of this includes the `ReverseDomain` service, which needs to collect IP addresses of all nodes in the entire emulation and create PTR records for them in the `in-addr.arpa.` zone. In such an occurrence, the `configure` and `render` method inherited from the `Service` layer may be overridden tool. Just remember to call the `configure` and `render` in the parent class (i.e., `Service` class), as those are responsible for invoking the `_doInstall` and `_doConfigure` methods.

### Included layers

The emulator includes the different layers to enable users to built and tune the emulator. 

#### The `Base` layer

The `Base` layer is the base of the emulation; consider it as the OSI layer 1. Users define Autonomous Systems, Internet Exchanges, routers, hosts, networks, and how they are connected in the `Base` layer.

#### Routing layers

Routing layers are the layers that will be handling routing protocols, like BGP, OSPF, and LDP.

- `Routing`: The routing layer provides the basic routing functionality to the emulator. It does three things: (1) install BIRD on router nodes and allow dynamic routing protocol layers to work, (2) setup kernel and device and (3) setup defult routes for host nodes. When this layer is rendered, two new methods will be added to the router node and can be used by other layers: (1) `addProtocol`: add new protocol block to BIRD, and (2) `addTable`: add new routing table to BIRD. This layer also assign loopback address for iBGP/LDP, etc., for other protocols to use later and as router id. The `Routing` layer itself also offers an `addDirect` method to mark a network as direct, to load the network into the routing information base. 
- `Ebgp`: The EBGP layer offers a convenient way to set up BGP peering between different autonomous systems. Users only need to provide the Internet exchange ID and peer ASNs, and the BGP layer will find the correct routers and setup BGP peering between them.
- `Ospf`: This layer enable OSPF on all router nodes. By default, this will make all internal network interfaces (interfaces that are connected to a network created by the AS). OSPF interface. Other interfaces, like internet exchange interfaces, will also be added as stub (passive) interface. Users can choose to override the automatic behavior by manually marking networks as stub or remove the network from OSPF entirely. Users can also choose to mask an entire autonomous system if they don't want OSPF in a particular autonomous system.
- `Ibgp`: This layer automatically setup IBGP full mesh peering between routers within AS using the loopback address configured by the routing layer. This will allow routers from within the AS to exchange routes received from other BGP peers (customers, upstreams, IX peering, etc.) between each other, building a transit network. OSPF will have to be enabled for `Ibgp` to work.
- `Mpls`: This layer is a replacement for the IBGP full mesh + OSPF setup for the transit provider's internal network. Instead of the traditional IP network, which requires every hop to have a copy of the full table, MPLS allows non-edge hops to hold only the MPLS forwarding table, which negated the need for the full table. MPLS uses LDP (Label Distribution Protocol) to create LSP (Label-switched path) for each unique path between the edge routers from within an autonomous system. The number of paths in an AS between edges is far less than the number of routes in the DFZ (Default Free Zone), saving resources on the non-edge routers. 

#### Infrastructure layers

Infrastructure layers are a special set of service layers, which instead of hosting on a single node, need to be hosted on multiple nodes, and the nodes work collaboratively to provide one type of service.

- `DomainNameService`: The DNS service allows hosting one or more zones on host nodes. It provides a internal zone tracking mechanism to help setting up complex zone structures or even running the entire DNS chain from the root. It can be configured to handle adding NS records, PTR records, and glue of NS records automatically, so users can focus on adding the records they want, and it will just work.
- `Dnssec`: The `Dnssec` class is not really a service but actually a layer. It works finding the given zones and set up a script on the server hosting the zone to sign the zone on-the-fly and send the DS record to the parent zone server with `nsupdate`.
- `BotnetService`:

#### Service and application layers

Service and application layers are services that can be hosted on a single node to provide some services.

- `WebService`: A simple nginx-based web service.
- `DomainNameCachingService`: The `DomainNameCachingService` service allows hosting local DNS (Caching DNS server) on the host node. This service provides the option to change `resolv.conf` on all nodes within the AS (`setResolvconf`), and the option to automatically update the local root hint file according to the root zone in the `DomainNameService` layer (`autoRoot`).
- `ReverseDomainNameService`: Reverse DNS. This service hosts the `in-addr.arpa.` zone, collect IP address of all nodes in the simlation, and resolves IP addresses to `nodename-netname.nodetype.asn.net.`.
- `CymruIpOrigin`: Cymru's IP info service is used by various traceroute utilities to map IP address to ASN (using DNS). This service loads the prefix list within the emulation and creates ASN mappings for them, so with proper local DNS configuration, nodes can see the ASN when doing traceroute. The layer will host domain `cymru.com`.
- `DomainRegistrarService`:

#### Other layers

Layers in this category do not fit well in any of the above categories or intervene with the emulation in a "meta" way.

- `Reality`: Reality Layer offers optons to connect the emulator from and to the real world. It allows exposing a simulated network with a VPN to the real-world, and enables adding real-world AS to emulation with ease. The layer allows users to set a list of prefixes to announce with BGP to the simulated Internet, and route it to the real-world. It can also fetch the prefix list of real-world AS and add them automatically.

### Implementation

#### Rendering layers

The process of actually makeing changes, like adding nodes, networks, peering configurations, or other fancy stuff like DNS, web server, etc., into the emulation is called rendering.

During the render stage, the `render` method of each layer will be called in order of their dependencies, and a `Emulator` object will be passed in. The `Emulator` object allows the different layers to collaboratively build a single emulation. `Base` layer, for example, creates routers, hosts and exchanges, and networks in the `Registry` (obtained by calling `emulator.getRegistry()`). `Bgp` layer can then access those exchanges and routers in the `Registry` configured by the `Base` layer and setup BGP peering on them.

In the old design, layers are allowed to access the emulator object and registry outside the render stage, which makes layers deeply coupled with a particular emulator scenario code.

One example of this is the DNS layer. We once bulit a DNS infrastructure with the DNS layer. The old DNS layer uses the host node object to keep track of what nodes are hosting what zone (root zone, com TLD, net TLD, etc.). The `Base` layer creates the node objects, which means now the DNS layer is coupled with this particular `Base` layer. To use this DNS infrastructure in another emulation, we have to copy the `Base` layer along with it, which is not ideal as the base layer contains other ASes and IXes, which might cause conflicts in the other emulation where we try to port to.

Therefore, we make the design decision to have layers keep track of the changes they try to make internally and only make changes during the render stage, so that the individual layers can be easily taken out and moved to other emulations. In the new design, all services layers (DNS is one of the service layers) keep track of nodes they try to install on with IP address or node name, and they find the node to install the server during render, therefore removes the dependencies on the node objects and `Base` layer.

#### Configuring layers

Configure is an optional class method of the `Layer` class, which the layer developer can choose to override if they want. By default, layers do nothing in the configure stage.

In the configure stage, layers will be provided with access to the emulator object. The configure stage allows the layer developer to have more control over the emulation.

In the configure stage, layers should register the data that other layers might need. For example, in the `Base` layer, we register the nodes, networks, etc., and resolv all pending networks joins. Layers, however, should not make irreversible changes, as there are chances that other layers will add new data to the emulator.

The configure stage is especially useful if a layer wants to make changes to another layer but still requires the other layer to have configured the emulator first. Currently, this is used in the `ReverseDomainName` and `CymruIpOrigin` service, both of which create a new zone in the `DomainName` service. They do so in the configure stage, as `DomainName` compiles the `Zone` data structure to zone files in the render stage, and additional zone added after the render stage won't be included in the final output. 

## Graphing

Serval classes of the emulator offer graphing options to convert the topologies to graphs. These classes are:

- `AutonomousSystem` offers the following graphs:
    - Layer 2 connections of the current AS.
- `Base` offers the following graphs:
    - Layer 2 connections of all AS, on one graph.
- `Ebgp` offers the following graphs:
    - eBGP peering (One each AS).
    - eBGP peering (All AS on one graph)
- `Ibgp` offers the following graphs:
    - iBGP peering (One each AS).
- `Mpls` offers the following graphs:
    - MPLS topology (One each AS).

## Compilers

Compile are the step that turns the rendered node and network objects into something that can be run by the user. The node objects basically keep track of what software to install on them, what networks they are connected to, what files are installed to what location, and what commands to run to start the node. Networks are just objects with properties storing the network name, prefix, link properties (speed limit, MTU, latency to add, etc.). These objects themself won't run, so we need to "compile" these objects. 

### Included compilers

The emulator includes serval different compilers to fit different use cases.

#### Docker

The docker compiler compiles the emulation to multiple docker containers. Networks in the emulation will be converted to docker networks, and nodes in the emulation are converted to docker services. It also generates a docker-compose file for spawning the containers.

#### Docker (Distributed)

The `DistributedDocker` compiler compiles the emulation to multiple docker containers. Networks in the emulation will be converted to docker networks, and nodes in the emulation are converted to docker services. It also generates a docker-compose file for spawning the containers.

Instead of putting all containers on one docker host, the `DistributedDocker` compiler generates one group of containers and docker-compose configuration for each AS, so the containers can be distributed across multiple Docker hosts.

The "distributed emulations" works by making all IX networks overlay networks. For this to work, all participating docker hosts must join the same swarm, and IX network and container must be started on the master Docker host before other ASes' containers.

#### Docker (Distributed) (GCP)

This compiler has the same behavior as the `DistributedDocker` compiler, but in addition to generating container configurations, it also generates a Terraform configuration to allow users to deploy to emulation to Google Cloud Platform directly.

#### Graphviz

This is not a real compiler. Instead of building the emulation, the Graphviz compiler collects all graphs from different layers and save them to the output directory.

### Implementation

Compilers, while actually doing all the heavy-lifting jobs, and actually trivial to implement. The only method needed to be implemented is `_doCompile`, which will pass in a `Emulator` object as the parameter. Compilers then iterate through all node objects and network objects in the emulation and "compiles" them to `Dockerfile` and `docker-compose.yml`.

While all the included compilers compile to Docker in some ways, there are no limits as to what backend the compilers can compiler to, given one implement them; compilers provided a clean way to abstract the idea of emulation. When users build an emulation, they do not need to worry about how or where the emulation will be running on eventually; it can be running on a single Docker host, or it can be running distributed across multiple Docker hosts. It may not even be running on Docker platforms. One can easily build a compiler of Vagrant and have the emulation run on virtual machines instead of containers.

## Merging Emulators

Thanks to the layered design, we can merge different emulations into one. This allows users to re-use part of existing emulations to build new emulations. For example, one can take the DNS layer out from an emulation with a complete DNS infrastructure and use it in another emulation. As the DNS layer only keep track of the name of nodes to target the service installation, as long as the user re-creates nodes with the same name in the new emulation, the DNS layer will "just works," even if the new emulator has a completely different topology in the Base layer.

The reusability aspect of the layer opens up an entirely new area of possibilities: sharing emulations. This section will go over the design of the merging mechanism.

### Exporting emulation

### Importing emulation

### Merging emulation

#### Conflict resolution

#### Custom merge actions