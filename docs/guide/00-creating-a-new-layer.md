# Creating new layer

The different functionality of the emulator is separated into different layers. `Base` layer, for example, describes the base of the emulation: what autonomous systems (AS) and internet exchanges (IX) are in the emulator, what nodes and networks are in each of the AS, and how nodes are connected with networks. `Bgp` layer, on the other hands, describes how ASes and where are peered with each other, and what's the relation between the peers.

To add new functionality into the emulator that works with the entire emulation as a whole, you can create a new layer. Note that if you are creating something that only works with a single node, like a service (like a webapp), you should create a service instead.

Creating a new layer in the emulator generally consists of the following steps:

- Implement the Layer interface.
- Implement the Configurable interface.
- Implement the Mergeable interface.
- Implement the Printable interface.

In this guide, we will also be covering the following topics:

- Accessing objects in the emulator.
- Working with layer dependencies.
- Render vs configuration.

## Render vs configuration

Render and configuration are two separate steps in the emulator.

Layers will have no knowledge of what or how other layers are configured prior to the render stage. Layers must keep track of the changes they try to make internally within the class. The process of actually makeing changes, like adding nodes, networks, peering configurations, or other fancy stuff like DNS, web server, etc., into the emulation is called rendering.

Configuration is an optional step. In the configure stage, layers will be provided with access to the emulator object. The configure stage allows the layer developer to have more control over the emulation.

In the configure stage, layers should register the data that other layers might need. For example, in the `Base` layer, we register the nodes, networks, etc., and resolv all pending networks joins. Layers, however, should not make irreversible changes, as there are chances that other layers will add new data to the emulator.

The configure stage is especially useful if a layer wants to make changes to another layer but still requires the other layer to have configured the emulator first. Currently, this is used in the `ReverseDomainName` and `CymruIpOrigin` service, both of which create a new zone in the `DomainName` service. They do so in the configure stage, as `DomainName` compiles the `Zone` data structure to zone files in the render stage, and additional zone added after the render stage won't be included in the final output. 

And during the render stage, the `render` method of each layer will be called in order of their dependencies, and a `Emulator` object will be passed in. The `Emulator` object allows the different layers to collaboratively build a single emulation. `Base` layer, for example, creates routers, hosts and exchanges, and networks in the `Registry` (obtained by calling `emulator.getRegistry()`). `Bgp` layer can then access those exchanges and routers in the `Registry` configured by the `Base` layer and setup BGP peering on them.

### Why two stages?

In the old design, layers are allowed to access the emulator object and registry outside the render stage, which makes layers deeply coupled with a particular emulator scenario code.

One example of this is the DNS layer. We once bulit a DNS infrastructure with the DNS layer. The old DNS layer uses the host node object to keep track of what nodes are hosting what zone (root zone, com TLD, net TLD, etc.). The `Base` layer creates the node objects, which means now the DNS layer is coupled with this particular `Base` layer. To use this DNS infrastructure in another emulation, we have to copy the `Base` layer along with it, which is not ideal as the base layer contains other ASes and IXes, which might cause conflicts in the other emulation where we try to port to.

Therefore, we make the design decision to have layers keep track of the changes they try to make internally and only make changes during the render stage, so that the individual layers can be easily taken out and moved to other emulations. In the new design, all services layers (DNS is one of the service layers) keep track of nodes they try to install on with IP address or node name, and they find the node to install the server during render, therefore removes the dependencies on the node objects and `Base` layer.

Just note that the configuration stage is completely optional. If you don't feel like you need it, there is no need to have it.

## Working with layer dependencies