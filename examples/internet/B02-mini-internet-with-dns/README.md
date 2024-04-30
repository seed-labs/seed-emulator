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

## Loading the DNS Infrastructure and Base Network

```
emuA.load('../B00-mini-internet/base-component.bin')
emuB.load('../B01-dns-component/dns-component.bin')
emu = emuA.merge(emuB, DEFAULT_MERGERS)
```


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
can be done after the container starts. We have created the following 
APIs to allow users to set the local DNS server at the emulator, AS,
and node levels. 

```
# At the AS level
base.getAutonomousSystem(160).setNameServers(['10.152.0.53'])
base.getAutonomousSystem(170).setNameServers(['10.152.0.53'])

# At the emulator level
base.setNameServers(['10.153.0.53'])

# At the node level (not included in the example)
node.setNameServers(['10.152.0.53'])
```


## Customization

After we bind the DNS virtual nodes to physical nodes, we may want to 
customize the physical nodes based on their new roles, such as 
changing their display name to something relevant to their roles. 
However, this needs to be done after the rendering,
because virtual nodes are only bound to physical nodes when the emulator is 
rendered, since the physical node may not even exist when one creates a binding. 
Even if a physical node matching the condition does exists at that time, 
there is no guarantee that the same physical node will be picked (consider 
a binding w/ empty filter: any physical node can be picked). 

After the rendering, we can get an instance of the physical node
and then do the customization. See the following examples: 

```
emu.render()
emu.getBindingFor('a-root-server').setDisplayName('A-Root')
emu.getBindingFor('global-dns').setDisplayName('Global DNS')
```

**Note:** While we can still use the method above to customize the 
physical nodes, in our new design, we allow the customization to be
done on virtual nodes. When they are bound to physical nodes, the 
customization will be carried to the physical nodes. This way,
the customization can be done when a virtual node is created, instead
of waiting for it to be bound to a physical node.
Our DNS component is already modified to use the new design. 
