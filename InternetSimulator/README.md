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

**`AddressAssignmentConstraint`**: The IP address assignment in a network is automated if one is not specified. This is to make building a scenario simpler. Users can derive from the `AddressAssignmentConstraint` class and change the assignment behavior.

**`AutonomousSystem`**: The `AutonomousSystem` class provides an easy-to-use wrapper for creating a new network and nodes in the simulation. The `AutonomousSystem` class itself is an abstract concept in the simulation. It is only there for ease of access and does not take part in the simulation generation. 

**`InternetExchange`**: The `InternetExchange` class provides an easy way to access the created node and network for an Internet Exchange. `InternetExchange` is only there for ease of access and does not take part in the simulation generation. 

**`Network`**: The `Network` class is an abstraction of network in the simulation. 

**`Node`**: The `Node` class is an abstraction of a node in the simulation. A node can be either a router or a server. The `Node` class provides various APIs for installing new software, adding new files, and joining networks. 

**`Printable`**: The `Printable` class is the base class of all classes that are "printable." It can be considered a special toString interface that allows specifying indentation. 

**`Registry`**: The `Registry` class is a singleton class for "registering" objects in the simulation. All classes can access the `Registry` to register new object or get registered objects. Objects in the `Registry` are all derived from the `Registerable` class. All `Registerable` class has three tags: scope, type, and name. For example, a router node name R1 in AS150 will be tagged with `('150', 'rnode', 'R1')`, and the `Routing` layer instance, if installed, will be tagged with `('seedsim', 'layer', 'Routing')`.

### Layers

#### Base

- Class Name: `Base`
- Depende: None
- Description: The base layer, as the name suggested, provides the base of simulation. This layer can only be used to create Autonomous Systems and Internet Exchanges. 

```python
base = Base()

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)

as150 = base.createAutonomousSystem(150)
as151 = base.createAutonomousSystem(151)

as150.createNetwork("net0")
as150.createNetwork("net_link")
as150.createNetwork("net1")

as150_r1 = as150.createRouter("r1")
as150_r1.joinNetworkByName("ix100")
as150_r1.joinNetworkByName("net0")
as150_r1.joinNetworkByName("net_link")

as150_h1 = as150.createHost("h1")
as150_h1.joinNetworkByName("net0")

as150_r2 = as150.createRouter("r2")
as150_r2.joinNetworkByName("ix101")
as150_r2.joinNetworkByName("net_link")
as150_r2.joinNetworkByName("net1")

as150_h2 = as150.createHost("h2")
as150_h2.joinNetworkByName("net1")

as151.createNetwork("net0") 

as151_r1 = as151.createRouter("r1")
as151_r1.joinNetworkByName("ix100")
as151_r1.joinNetworkByName("net0")

as151_h1 = as151.createHost("h1")
as151_h1.joinNetworkByName("net0")

as151_h2 = as151.createHost("h2")
as151_h2.joinNetworkByName("net0")
```

#### Routing

- Clas Name: `Routing`
- Dependencies: `Base`
- Description: The routing layer install the base for other routing protocols like BGP and OSPF. It installs the necessary software on the nodes with router nodes and does proper initial configurations. The routing layer also allows users to specify a list of directly connected interfaces to generate connected routes and install them to RIB (routing information base). 

```python
routing = Routing()
routing.addDirectByName(150, "net0")
routing.addDirectByName(150, "net1")
routing.addDirectByName(151, "net0")
```

#### eBGP

- Class Name: `Ebgp`
- Dependency: `Routing`
- Description: The external BGP (eBGP) layer. This layer allows users to set up BGP peering by specifying only the Internet Exchange ID and peer ASNs.

```python
ebgp = Ebgp()
ebgp.addPrivatePeering(100, 150, 151)
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
```

#### OSPF

- Class Name: `Ospf`
- Dependency: `Routing`
- Description: The OSPF layer. OSPF layer, if installed, will set up OSPF on all non-IX interfaces. IX interfaces will also be included in the OSPF as passive (stub) interfaces'. The auto stub-interface and auto OSPF behavior can be controlled by manually marking a network as a stub, or by removing the network from OSPF altogether.

```python
ospf = Ospf()
```

#### iBGP

- Class Name: `Ibgp`
- Dependency: `Ospf`
- Description: The internal BGP (iBGP) layer. This layer will setup full-mesh iBGP peering between all routers within an AS in all ASes. Masks can be applied on an AS to prevent the auto full-mesh. The full-mesh peering is done using the first non-IX interface address. Nexthop resolution will be made with the OSPF table, so OSPF should be installed for iBGP to work properly.

```python
ibgp = Ibgp()
```

#### Service

- Class Name: `Service`
- Dependency: `N/A`
- Description: The service layer is the base layer of other services. The service itself cannot be rendered and only services the goal of providing common utility methods for users and other service layers.

```python
s = SomeService()
s.installOnAll(150)
s.installOn(as150_h1)
```

#### Web Service

- Class Name: `WebService`
- Dependency: `Base`
- Description: The web service layer installs `nginx-light` on host nodes and hosts a simple webpage showing the current node name and ASN.

```python
ws = WebService()
ws.installOnAll(150)
ws.installOn(as151_h1)
```

### Domain Name Service

- Class Name: `DomainNameService`
- Dependency: `Base`
- Description: The DNS layer allows hosting one or more zones on host nodes. It provides a simple zone tracking mechanism to help setting up complex zone structures or even running the entire DNS chain from the root.

```python
dns = DomainNameService()
dns.getZone('example.com.').addRecord('@   A 127.0.0.1')
dns.getZone('example.com.').addRecord('www A 127.0.0.1')
dns.getZone('example2.com.').resolveTo('test', as151_h1)
dns.hostZoneOn('example.com.', as151_h1)
dns.hostZoneOn('example2.com.', as151_h1)
dns.hostZoneOn('com.', as150_h2)
dns.hostZoneOn('.', as150_h1)
dns.autoNameServer()
```

### Domain Name Caching Service

- Class Name: `DomainNameCachingService`
- Dependency: `Base` only if not using `autoRoot`, `Base` and `DomainNameService` otherwise.
- Description: The `DomainNameCachingService` layer allows hosting local DNS (Caching DNS server) on the host node. This layre provides the option to change `resolv.conf` on all nodes within the AS (`setResolvconf`), and the option to automatically update the local root hint file according to the root zone in the `DomainNameService` layer (`autoRoot`).

```python
ldns = DomainNameCachingService(autoRoot = True, setResolvconf = True)
ldns.installOn(as151_h2)
```

### Reality

- Class Name: `Reality`
- Dependency: `Ebgp`
- Description: The `Reality` layer allows easy interaction with hosts in the real-world. It allows exposing a simulated network with a VPN to the real-world (TODO), and enables adding real-world AS to simulation with ease. The layer allows users to set a list of prefixes to announce with BGP, to the simulated Internet, and route it via the default gateway (i.e., the reality.) It can also fetch the prefix list of real-world AS and add them automatically.

```python
real = Reality()
as11872 = base.createAutonomousSystem(11872)
as11872_rw = real.createRealWorldRouter(as11872)
as11872_rw.joinNetworkByName("ix100", "10.100.0.118")
ebgp.addRsPeer(100, 11872)
```

### Renderer

TODO

### Compiler

TODO