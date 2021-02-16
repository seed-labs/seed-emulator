Layers
---

The different functionality of the simulator is separated into different layers. `Base` layer, for example, describes the base of the simulation: what autonomous systems (AS) and internet exchanges (IX) are in the simulator, what nodes and networks are in each of the AS, and how nodes are connected with networks. `Bgp` layer, on the other hands, describes how ASes and where are peered with each other, and what's the relation between the peers.

### Render

Layers will have no knowledge of what or how other layers are configured prior to the render stage. Layers must keep track of the changes they try to make internally within the class. The process of actually makeing changes, like adding nodes, networks, peering configurations, or other fancy stuff like DNS, web server, etc., into the simulation is called rendering.

During the render stage, the `render` method of each layer will be called in order of their dependencies, and a `Simulator` object will be passed in. The `Simulator` object allows the different layers to collaboratively build a single simulation. `Base` layer, for example, creates routers, hosts and exchanges, and networks in the `Registry` (obtained by calling `simulator.getRegistry()`). `Bgp` layer can then access those exchanges and routers configured by the `Base` layer and setup BGP peering to them.

In the old design, layers are allowed to change the simulator outside the render stage, which makes layers deeply coupled with a particular simulator scenario code.

One example of this is the DNS layer. We build a DNS infrastructure with the DNS layer. The old DNS layer uses the host node object to keep track of what nodes are hosting what zone (root zone, com TLD, net TLD, etc.). The `Base` layer creates the node objects, which means now the DNS layer is coupled with this particular `Base` layer. To use this DNS infrastructure in another simulation, we have to copy the `Base` layer along with it, which is not ideal as the base layer contains other ASes and IXes, which might cause conflicts in the other simulation where we try to port to.

Therefore, we make the design decision to have layers keep track of the changes they try to make internally and only make changes during the render stage, so that the individual layers can be easily taken out and moved to other simulations. In the new design, all services layers (DNS is one of the service layers) keep track of nodes they try to install on with IP address or node name, and they find the node to install the server during render, therefore removes the dependencies on the node objects and `Base` layer.


### Configure

Configure is an optional class method of the `Layer` class, which the layer developer can choose to override if they want. By default, layers do nothing in the configure stage.

In the configure stage, layers will be provided with access to the simulator object. The configure stage allows the layer developer to have more control over the simulation.

In the configure stage, layers should register the data that other layers might need. For example, in the `Base` layer, we register the nodes, networks, etc., and resolv all pending networks joins. Layers, however, should not make irreversible changes, as there are chances that other layers will add new data to the simulator.

The configure stage is especially useful if a layer wants to make changes to another layer but still requires the other layer to have configured the simulator first. Currently, this is used in the `ReverseDomainName` and `CymruIpOrigin` service, both of which create a new zone in the `DomainName` service, and they do so in the configure stage, as `DomainName` compies the `Zone` data structure to zone files in the render stage, and additional zone added after the render that won't be included in the final output. 