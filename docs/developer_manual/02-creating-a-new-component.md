# Creating a new component

A component is a collection of nodes, layers, and services. It does not necessarily have all of them. Consider it as a partially-built emulator template. An example of this is the BGP attacker component. The BGP attacker component allows users to create a new emulator with a BGP attack inside. The emulator contains a base layer for the attacker's autonomous system, a router in the autonomous system, and static route entries to route the prefix specified by the user to the black hole.

With the BGP attacker component, to create a hijacker, all the user needs to do is to set an ASN, set a list of prefixes, set the exchange to join, and merge the output of the component to the user's emulator. 

To create a new customizable component, one will need to implement the `Component` interface. However, if a component does not take any input (no customizable options), it is recommended to simply dump the emulation with the `Emulator::dump` API and share it that way instead.

The `Component` interface has only two methods:

## `Component::get`

The `get` call takes no input and should return an `Emulator` instance. 

## `Component::getVirtualNodes`

The `getVirtualNodes` takes no input and should return a list name of unbound virtual nodes in the emulator. Users may use this list to bind the virtual nodes to physical nodes. The default implementation returns an empty list on invoked.