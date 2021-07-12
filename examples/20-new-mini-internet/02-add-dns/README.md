# Deploying DNS Infrastructure in Emulator

This example demonstrates how we can build a DNS infrastructure as a 
component, and then deploy this infrastructure onto a pre-built
emulator. It consists of three steps:

- **Load the DNS component and the base emulator**.

- **Install the DNS infrastructure to physical nodes**: nodes in the DNS infrastructure
  are all virtual nodes; they are not bound to any physical nodes.
  They represent a service. When we deploy the DNS infrastructure
  to an emulator, we just need to bind each virtual node to a physical node
  inside the emulator, i.e., we will install the service to physical nodes. 

- **Bridging the emulator and the DNS infrastructure**: local DNS server (also
  called DNS cache server) is the bridge between the nodes in the emulator and 
  the DNS infrastructure. We need to create one or multiple local DNS
  servers.

  - When a node needs to find a DNS mapping, it will contact its local DNS server.
  - To use the DNS infrastructure to find the answer, the local DNS server 
    starts from the root servers. 
  - The following diagram depicts their relationships: 
    ```
    Physical nodes ---> Local DNS server 
                           |
                           v
         Root servers (entry point of the DNS infrastructure)
    ```

## Creating a DNS Infrastructure

We use a separate program (`dns-component.py`) to generate the DNS infrastructure
and then save it into a file as a DNS component. How to create the
DNS infrastructure will be given in a separate manual. In this example,
we created the following nameservers:

- a-com-server
- b-com-server
- a-net-server
- a-edu-server
- a-cn-server
- b-cn-server
- ns-twitter-com
- ns-google-com
- ns-example-net
- ns-syr-edu
- ns-weibo-cn

The DNS layer in the emulator will manage their relationships. For example,
the nameserver of the `com.` zone will be automatically registered to the 
nameserver of the root zone.  


## Installing DNS Services on Physical Nodes

The nodes in the DNS infrastructures are virtual nodes, representing services.
We will install them to physical nodes by binding the virtual nodes
to physical nodes. We have crated a variety of binding mechanism. In 
this example, we only show a simple binding, which
use `Action.FIRST` to bind a virtual node to the first 
acceptable node (service conflicts can make some nodes unacceptable)
that satisfies the filter rule. The following example
binds the virtual node `a-root-server` in the DNS infrastructure 
to the first acceptable node in autonomous system `171`. 

```
emu.addBinding(Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST))
```

All the virtual nodes need to be bound to physical nodes; otherwise 
rendering will report errors. 


## Creating Local DNS Server

Creating a local DNS server is similar to creating 
other types of services. In the following example,
we create a virtual node called `global-dns`. We plan
to use this cached DNS server as the local DNS 
server of the entire emulator.  

```
ldns = DomainNameCachingService()
ldns.install('global-dns')
```

We need to host this cache DNS server on a physical node.
In this example, we create a new host in `AS-153`, and
use it to host the local DNS server. We will fix the IP
address for this node, because this IP address is the 
bridge that connects the emulator and the DNS 
infrastructure. 

```
base: Base = emu.getLayer('Base')
as153 = base.getAutonomousSystem(153)
as153.createHost('local-dns').joinNetwork('net0', address = '10.153.0.53')
emu.addBinding(Binding('global-dns', filter = Filter(asn=153, nodeName="local-dns")))
```

We need to add 10.153.0.53 as the local DNS server for all the nodes in the emulation.
This is done by adding the following record  record in `/etc/resolve.conf`:
```
nameserver 10.153.0.53
```

However, the `/etc/resolve.conf` is dynamically updated after the container
has started, so we cannot add this record when we build the container. 
Our solution is to create a hook, which adds a command to the 
container startup script, so adding the local DNS server record
can be done after the container starts. 

```
emu.addHook(ResolvConfHook(['10.153.0.53']))
```


## Suggestions

- (Priority: High): Several DNS-related APIs should return `self` to allow API chaining.
  For example, `addZone()`, `setMaster()`, `addRecord()`, etc. Typically, these set-APIs
  do not return anything. If we let them return `self`, we can do the following:
  ```
  xyz.addRecord().addRecord().addRecord()
  abc.addZone().setMaster()
  ```

- (Priority: Low): During the binding, use `Action.NEW` to bind a virtual node to a new 
  physical node, i.e., the node needs to be created.

- (Priority: Low): The way to set the local DNS server is not clear. 
  I hope to be able to do the 
  following: the `localDNS` argument could be an IP address (physical node) 
  or a virtual node name, the `overwrite` option indicates whether to overwrite 
  the existing setting if a node already has set the local DNS:
  - `emu.setLocalDNS(localDNS, overwrite=true/false)`: 
     set the local DNS for the entire emulation. This will be a wrapper of 
     the `addHook` API (we will keep `addHook` public because it could be 
     quite useful for other scenarios).

  - `as.setLocalDNS()`: for the entire autonomous system
  - `network.setLocalDNS()`: for the entire network
  - `node.setLocalDNS()`: for a node

