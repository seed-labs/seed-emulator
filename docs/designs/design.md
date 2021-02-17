# Design

   * [Design](#design)
      * [Overview](#overview)
      * [Layers](#layers)
         * [Services](#services)
         * [Rendering layers](#rendering-layers)
         * [Configuring layers](#configuring-layers)
         * [Graphing](#graphing)
         * [Compiling](#compiling)
            * [Docker](#docker)
            * [Docker (Distributed)](#docker-distributed)
            * [Docker (Distributed) (GCP)](#docker-distributed-gcp)
            * [Graphviz](#graphviz)
      * [Merging Simulators](#merging-simulators)
         * [Exporting simulation](#exporting-simulation)
         * [Importing simulation](#importing-simulation)
         * [Merging simulation](#merging-simulation)
            * [Conflict resolution](#conflict-resolution)
            * [Custom merge actions](#custom-merge-actions)

## Overview

Unlike traditional simulators, this simulator is based on the idea of layers. Each layer holds part of the information required for building a simulation scenario. Layers are independent of each other, meaning users can take a layer from one simulation scenario and put it into another.

## Layers

Every component is a layer. The base of the simulation is the `Base` layer, and the other layers, like `Routing`, `Bgp`, `Ospf`, `Mpls` and `DomainNameService` add different components to the simulation.  `Base` layer, for example, describes the base of the simulation: what autonomous systems (AS) and internet exchanges (IX) are in the simulator, what nodes and networks are in each of the AS, and how nodes are connected with networks. `Bgp` layer, on the other hand, describes how ASes and where are peered with each other, and what's the relationship between the peers.

Each layer only takes care of its' own matter. BGP layer only saves what autonomous systems are peered with what autonomous system, and what internet exchange. It doesn't care how or where the router node actually is; as long as the information matched (correct IX, correct peer ASN), it will configure the peering between them. DNS layer only saves what zones are hosted on which node with their IP address or name, meaning one can build a DNS infrastructure with DNS layer in one simulation and easily export it and re-use the same infrastructure in a simulation with entirely different BGP peerings and layer two topologies, given that they re-create nodes with the same name in the other simulation. In other words, layers will have no knowledge of what or how other layers are configured prior to the render stage. Layers must keep track of the changes they try to make internally within the class.

Here's a list of included layers:

- `Base`: The base layer is the base of the simulation; consider it as the OSI layer 1. Users define Autonomous Systems, Internet Exchanges, routers, hosts, networks, and how they are connected in the `Base` layer.
- `Routing`: The routing layer provides the basic routing functionality to the simulator. 
- `Bgp`: ...

### Services

Services are special kinds of layers. One way to differentiate the regular layers and services layer is their scope. A regular Layer makes changes to the entire simulation (like BGP, which configure peeing across multiple different autonomous systems, exchanges, and routers). In contrast, a service only makes changes to individual nodes (like `Web`, which install `nginx` on the given node). 

In the old design, services are installed by providing the node object to the services. In the new design, we decided not to use any node object to identify which node to install the services on, as that creates dependencies to the base layer, as mentioned in the previous section. In the new design, we use the node's name and IP address to identify nodes to install service on. And in fact, the `Service` class itself is derived from the `Layer` class and it just adds a few helper functions to make developing new services easier:

- `Service::installByName(asn: int, nodename: str)`: install service on the node with `nodename` in AS `asn`.
- `Service::installByIp(address: str, asn: int = None)`: install service on the node with IP address `address`, optionally limit the ASN to `asn`.

The `Service` layer will keep track of what nodes are pending service configuration / installation and will do the proper configuration / installation during the configure and render stage. 

To create a new `service`, only the `_createServer` method needs to be implemented by the derived class. The `_createServer` takes no parameters and should return a class object derived from the `Server` class. Only one method needs to be implemented for the `Server` class, `install`, which takes only one parameter, the node object to install the server on. Developers can implement additional methods on the derived `Server` for configuring the server-specific settings; for example, there's a `setPort` method in the `WebServer` class, which allows users to change the listen port of the webserver.

Derived `Service` layer can alternatively implement the following methods to change how servers are installed and configured:

- `_doInstall(server: Server, node: Node)`: change how servers are installed. By default, this calls `server.install(node)`. Servers are installed during the render stage. 
- `_doConfigure(server: Server, node: Node)`: change how servers are configured. This is called during the configure stage, and by default, this does nothing.

As a single server object is typically installed only on one node, the `_doInstall` and `_doConfigure` method only passes in the `Node` object. However, sometimes the service layer may need to gather information from the entire simulation, instead of from just the node it tries to install the services on. An example of this includes the `ReverseDomain` service, which needs to collect IP addresses of all nodes in the entire simulation and create PTR records for them in the `in-addr.arpa.` zone. In such an occurrence, the `configure` and `render` method inherited from the `Service` layer may be overridden tool. Just remember to call the `configure` and `render` in the parent class (i.e., `Service` class), as those are responsible for invoking the `_doInstall` and `_doConfigure` methods.

### Rendering layers

The process of actually makeing changes, like adding nodes, networks, peering configurations, or other fancy stuff like DNS, web server, etc., into the simulation is called rendering.

During the render stage, the `render` method of each layer will be called in order of their dependencies, and a `Simulator` object will be passed in. The `Simulator` object allows the different layers to collaboratively build a single simulation. `Base` layer, for example, creates routers, hosts and exchanges, and networks in the `Registry` (obtained by calling `simulator.getRegistry()`). `Bgp` layer can then access those exchanges and routers in the `Registry` configured by the `Base` layer and setup BGP peering on them.

In the old design, layers are allowed to access the simulator object and registry outside the render stage, which makes layers deeply coupled with a particular simulator scenario code.

One example of this is the DNS layer. We once bulit a DNS infrastructure with the DNS layer. The old DNS layer uses the host node object to keep track of what nodes are hosting what zone (root zone, com TLD, net TLD, etc.). The `Base` layer creates the node objects, which means now the DNS layer is coupled with this particular `Base` layer. To use this DNS infrastructure in another simulation, we have to copy the `Base` layer along with it, which is not ideal as the base layer contains other ASes and IXes, which might cause conflicts in the other simulation where we try to port to.

Therefore, we make the design decision to have layers keep track of the changes they try to make internally and only make changes during the render stage, so that the individual layers can be easily taken out and moved to other simulations. In the new design, all services layers (DNS is one of the service layers) keep track of nodes they try to install on with IP address or node name, and they find the node to install the server during render, therefore removes the dependencies on the node objects and `Base` layer.

### Configuring layers

Configure is an optional class method of the `Layer` class, which the layer developer can choose to override if they want. By default, layers do nothing in the configure stage.

In the configure stage, layers will be provided with access to the simulator object. The configure stage allows the layer developer to have more control over the simulation.

In the configure stage, layers should register the data that other layers might need. For example, in the `Base` layer, we register the nodes, networks, etc., and resolv all pending networks joins. Layers, however, should not make irreversible changes, as there are chances that other layers will add new data to the simulator.

The configure stage is especially useful if a layer wants to make changes to another layer but still requires the other layer to have configured the simulator first. Currently, this is used in the `ReverseDomainName` and `CymruIpOrigin` service, both of which create a new zone in the `DomainName` service. They do so in the configure stage, as `DomainName` compiles the `Zone` data structure to zone files in the render stage, and additional zone added after the render stage won't be included in the final output. 

### Graphing

Serval classes of the simulator offer graphing options to convert the topologies to graphs. These classes are:

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

### Compiling

Compile are the step that turns the rendered node and network objects into something that can be run by the user. The node objects basically keep track of what software to install on them, what networks they are connected to, what files are installed to what location, and what commands to run to start the node. Networks are just objects with properties storing the network name, prefix, link properties (speed limit, MTU, latency to add, etc.). These objects themself won't run, so we need to "compile" these objects. 

The simulator includes serval different compilers to fit different use cases.

#### Docker

The docker compiler compiles the simulation to multiple docker containers. Networks in the simulation will be converted to docker networks, and nodes in the simulation are converted to docker services. It also generates a docker-compose file for spawning the containers.

#### Docker (Distributed)

The DistributedDocker compiler compiles the simulation to multiple docker containers. Networks in the simulation will be converted to docker networks, and nodes in the simulation are converted to docker services. It also generates a docker-compose file for spawning the containers.

Instead of putting all containers on one docker host, the DistributedDocker compiler generates one group of containers and docker-compose configuration for each AS, so the containers can be distributed across multiple Docker hosts.

The "distributed simulations" works by making all IX networks overlay networks. For this to work, all participating docker hosts must join the same swarm, and IX network and container must be started on the master Docker host before other ASes' containers.

#### Docker (Distributed) (GCP)


#### Graphviz

This is not a real compiler. Instead of building the simulation, the Graphviz compiler collects all graphs from different layers and save them to the output directory.

```python
gcompiler = Graphviz()
gcompiler.compile('./test-graphs') # output dir
```

## Merging Simulators

### Exporting simulation

### Importing simulation

### Merging simulation

#### Conflict resolution

#### Custom merge actions