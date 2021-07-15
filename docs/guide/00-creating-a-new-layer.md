# Creating a new layer

The different functionality of the emulator is separated into different layers. `Base` layer, for example, describes the base of the emulation: what autonomous systems (AS) and internet exchanges (IX) are in the emulator, what nodes and networks are in each of the AS, and how nodes are connected with networks. `Bgp` layer, on the other hands, describes how ASes and where are peered with each other, and what's the relation between the peers.

To add new functionality into the emulator that works with the entire emulation as a whole, you can create a new layer. Note that if you are creating something that only works with a single node, like a service (like a webapp), you should create a service instead.

This guide is going to cover the following topics:

- Render and configuration.
- Why layers.
- Implementing and working with the `Layer` interface.
    - Implementing the `Configurable` interface.
    - Implementing the `Printable` interface.
    - Working with layer dependencies.
- Working with the `Registry`.
- Working with other layers.
- Working with merging.

## Render and configuration

Render and configuration are two separate steps in the emulator.

Layers will have no knowledge of what or how other layers are configured prior to the render stage. Layers must keep track of the changes they try to make internally within the class. The process of actually makeing changes, like adding nodes, networks, peering configurations, or other fancy stuff like DNS, web server, etc., into the emulation is called rendering.

During the render stage, the `render` method of each layer will be called in order of their dependencies, and a `Emulator` object will be passed in. The `Emulator` object allows the different layers to collaboratively build a single emulation. 

Configuration is an optional step. In the configure stage, layers will be provided with access to the emulator object. The configure stage allows the layer developer to have more control over the emulation construction.

In the configure stage, layers should register the data that other layers might need. For example, in the `Base` layer, we register the nodes, networks, etc., and resolv all pending networks joins. Layers, however, should not make irreversible changes, as there are chances that other layers will add new data to the emulator.

The configure stage is especially useful if a layer wants to make changes to another layer but still requires the other layer to have configured the emulator first. Currently, this is used in the `ReverseDomainName` and `CymruIpOrigin` service, both of which create a new zone in the `DomainName` service. They do so in the configure stage, as `DomainName` compiles the `Zone` data structure to zone files in the render stage, and additional zone added after the render stage won't be included in the final output. 

## Why layers?

In the old design, layers are allowed to access the emulator object and registry outside the render stage, which makes layers deeply coupled with a particular emulator scenario code.

One example of this is the DNS layer. We once bulit a DNS infrastructure with the DNS layer. The old DNS layer uses the host node object to keep track of what nodes are hosting what zone (root zone, com TLD, net TLD, etc.). The `Base` layer creates the node objects, which means now the DNS layer is coupled with this particular `Base` layer. To use this DNS infrastructure in another emulation, we have to copy the `Base` layer along with it, which is not ideal as the base layer contains other ASes and IXes, which might cause conflicts in the other emulation where we try to port to.

Therefore, we make the design decision to have layers keep track of the changes they try to make internally and only make changes during the render stage, so that the individual layers can be easily taken out and moved to other emulations. In the new design, all services layers (DNS is one of the service layers) keep track of nodes they try to install on with IP address or node name, and they find the node to install the server during render, therefore removes the dependencies on the node objects and `Base` layer.

Just note that the configuration stage is completely optional. If you don't feel like you need it, there is no need to have it.

## Implementing the `Layer` interface

To create a new layer, one will need to implement the `Layer` interface. The `Layer` interface is actually fairly simple. It only has two methods:

### `Layer::getName`

All layers must implement the `Layer::getName` method. This method takes no input and returns a string indicating the name of this layer. The name of the layer must be unique. The name of the layer will be used as the identifier for the layer object in the emulator.

### `Layer::render`

All layers must implement the `Layer::Render` method. This method takes one parameter, the reference to the `Emulator` class instance, as input. It does not need to return anything. Layers should make changes to the objects in the emulation here.

In the render stage, layers can safely assume that no further API calls will be made on the `Layer` class itself. An example of this is the DNS service layer. The DNS layer will start collecting nameservers for zones, finalize glue records, convert the internal tree structure to zone files, etc. No more changes can be made to the layer - meaning no new domains can be added, no more name servers can be added. 

## Implementing the `Configurable` interface

The `Layer` interface is derived from the `Configurable` interface. The `Configurable` class has only one method:

### `Configurable::configure`

Layers may optionally implement the `Configurable::configure` method. This method takes one parameter, the reference to the `Emulator` class instance, as input. It does not need to return anything. A default implementation of `Configurable::configure` is included in the `Configurable` class - it just returns when called. Layers can make changes to the objects, or even another layer, in the emulation here.

Unlike the render stage, the layer should allow future changes to the layer, as other layers may make changes during their configuration stage. An example of this is, again, the DNS service layer. Layers like `ReverseDomainNameService` collect IP addresses in the emulator and assign reverse hostnames to them by creating a new `in-addr.arpa` zone in the DNS layer. 

In the configuration stage, a layer should register objects that may be useful to other layers in the emulator. An example of this is the `Base` layers. `Node` and `Network` objects are, in fact, registered in the emulator in the configuration stage by the `Base` layer. 

A `Node` object represents a network device in the emulator. It can be a server, a router, a user machine, or just any other device connected to the network. A `Network` object represents a network in the emulator. It can be a private local network within an AS, or a public global network like an internet exchange. For details on how to work with them, please consult the API documentation.

## Working with the `Registry`

To access another object in the emulator, one will use the `Registry`. Consider `Registry` as a database of objects in the emulator. Nodes, networks, and even other layers are registered in the `Registry`. To retrieve the `Registry`, use `Emulator::getRegistry`. The `Emulator` object is passed to layers in both render and configuration stages. 

To retrieve an object from the `Registry`, one will need to know the scope, type, and name of the object. Scope is usually the name of the owner of the object. For private `Node` and `Network`, it's usually their ASN. Type, as the name suggested, specifies the type of the object. Examples are `network` for `Network`, `hnode` for `Node` with host role, and `rnode` for `Node` with router role. And name defines the name of the object.

For example, to get a router node with name `router0` from `AS150`, one can do:

```python
r0_150: Router = emulator.getRegistry().get('150', 'rnode', 'router0')
```

Example of locations of some other objects in the emulator (in the format of `scope/type/name`):

- AS150's host node with name `web_server`: `150/hnode/web_server`.
- IX100's peering LAN: `ix/net/ix100`.
- IX100's router server node: `ix/rs/ix100`.
- The `Base` layer: `seedemu/layer/Base`.

To test if an object exist, use `has`:

```python
if registry.has('150', 'rnode', 'router0'):
    # do something...
```

To iterate over all objects, use `getAll`:

```python
for ((scope, type, name), obj) in registry.getAll().items():
    # do something...
```

To iterate over all objects of a type in a scope, use `getByType`:

```python
for router in registry.getByType('150', 'rnode'):
    # do something...
```

To register an object, use `register`:

```python
registry.register('some_scope', 'some_type', 'some_name', some_object)
```

For an object to be registrable, it must implement the `Registrable` interface. Refer to the API documentation for details.

## Working with other layers

As mentioned earlier, layers may access each other and make changes to each other. While having the two-stage process helps with making changes in order, sometimes it may be necessary to have some layers to be configured before or after another layer. The most obvious example of this is the `Base` layer. The `Base` layer must be configured before all other layers. Otherwise, they will not be able to retrieve the `Node` and `Network` objects from the `Registry`.

A layer can require itself to be rendered before or after another layer or ask the emulator to error out when another layer does not exist. This mechanism is called layer dependency. To add a dependency, layer can call `Layer::addDependency`.

`addDependency` takes three parametners:

- `layerName`: string, name of the layer to target.
- `reverse`: bool, when `True`, this `addDependency` creates a reverse dependency. Regular dependency requires the target layer to be rendered/configured before the current layer, while a reverse dependency requires the current layer to be rendered/configured before the target layer.
- `optional`: bool, when `True`, the emulator will contine render even if the target layer does not exist in the emulation.

## Working with merging

Merging is an important feature of the emulator. It enables the re-use of existing layers in another emulation. One can build and public a full DNS infrastructure without the base layer. Other users can then merge the DNS infrastructure with their own emulation that has the base layer without having to re-build the DNS infrastructure themself.

During merging, the same layer may exist in both emulators. A `Merger` needs to be implemented to handle the merging. The `Merger` interface are as follow:

### `Merger::getName`

The `getName` call takes no parameter and should return the name of the merger. This should be a unique identifier of the merger. 

### `Merger::getTargetType`

The `getTargetType` call takes no parameter and should return the name of type that this merger targers. For example, a merger that targets the `Base` layer should return `BaseLayer` here.

### `Merger::doMerge`

The `doMerge` call takes two parameters. Call them `objectA` and `objectB`. When user performs a merge by calling `newEmulator = emulatorA.merge(emulatorB)`, `objectA` will be the object from `emulatorA`, and `objectB` will be the object from `emulatorB`. 

The call should return a new, merged object of the same type with the `objectA` and `objectB`. 