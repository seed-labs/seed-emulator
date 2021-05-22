# Merging emulators

Idea: perform merging top-down, e.g.:

```
emulatorA.merge(emulatorB)
|- baselayerA.merge(baselayerB)
|  |- internetExchangeA.merge(internetExchangeB)
|  |   `- internetExchangeANetwork.merge(internetExchangeBNetwork)
|  `- autonomousSystemA.merge(autonomousSystemB)
|     |- internalNetworkA.merge(internalNetworkB)
|     `- nodeA.merge(nodeB)
|- routingLayerA.merge(routingLayerB)
`- ...
```

Cases:
- (00): No overlapping IX or AS,
- (10): Overlapping IX, no overlapping AS,
- (01): No overlapping AS, but overlapping AS,
- (11): Overlapping IX and AS.

For overlapping AS:
- Overlapping internal networks (don't try to merge them, treat them as different networks).
- Overlapping internet exchange (error out)

For overlapping IX:
- Keep only one of the RS; RSes are the same, so it does not matter which to keep.

## Layers

Merge criteria: invoke `merge` if two layers have the same type. (possible in all four cases)

### Merging `BaseLayer`

Merge criteria: see below.

#### Components: Internet Exchange

Merge criteria: invoke `merge` if the exchanges has the same ID. (only possible in case 10, 11)

Currently, internet exchanges are just networks. Refer to network merging in the "Core Components" section for details.

#### Components: Autonomous System

Merge criteria: invoke `merge` if the AS has the same ASN. (only possible in case 01, 11)

What needs to be merged:

1. Subnet Generator (case 01, 11)
2. Networks (case 01, 11)
3. Hosts (case 01, 11)
4. Routers (case 01, 11)

How to merge (both cases 01, 11):

1. Rewrite to use list to keep track of assigned subnets, then merge lists.
2. Merge if subnet are the same, see network merging in the "Core Components" section for details.
3. Do nothing; if they need to be merged, they will be handled during network merge.
4. Do nothing; if they need to be merged, they will be handled during network merge.

### Merging `RoutingLayer`

What needs to be merged (all four cases): 

1. List of networks marked as 'direct'

How to merge (all four cases):

1. It is just a set of networks; simply join the sets.

### Merging `EbgpLayer`

What needs to be merged (all four cases): 

1. RS peering list
2. Private peering list

How to merge (all four cases):

1. It's a list; just join them and remove duplicates.
2. It's a dictionary. Join them, and check for duplicates.

### Merging `IbgpLayer`

What needs to be merged (all four cases): 

1. Masked ASN list

How to merge (all four cases):

1. It's a list; just join them and remove duplicates.

### Merging `OspfLayer`

What needs to be merged (all four cases): 

1. List of marked stub networks
2. List of masked networks
3. List of masked ASNs

How to merge (all four cases):

1. Just join the lists.
2. Just join the lists.
3. Join the lists, and remove duplicates.

### Merging `MplsLayer`

What needs to be merged (all four cases): 

1. List of ASNs with MPLS enabled
2. List of manually marked edge routers

How to merge (all four cases):

1. Just join the lists.
1. Just join the lists.

### Merging `RealityLayer`

What needs to be merged (all four cases): 

1. List of realworld-access enabled networks.
2. List of realworld routers.

How to merge (all four cases):

1. Just join the lists.
2. Just join the lists. 

### Merging `DomainNameServiceLayer`

What needs to be merged (all four cases):

- Zones
- List of servers, and what zone they are hosting.

#### Merging zones (all four cases)

If two zones has the same name, merge them. Problems:

1. What if they have different SOA record?
2. What if They have different NS record(s)?
3. What if there are other conflicting records?
4. What to submit to the parent zone as gule records?

### Merging `DomainNameCachingServiceLayer`

What needs to be merged (all four cases):

1. List of nodes to install the service on.

How to merge (all four cases):

1. Just join the lists.

### Merging `ReverseDomainNameServiceLayer`

What needs to be merged (all four cases):

1. List of zone names with DNSSEC enabled.

How to merge (all four cases):

1. Just join the lists.

### Merging `DnssecLayer`

What needs to be merged (all four cases):

1. List of zone names with DNSSEC enabled.

How to merge (all four cases):

1. Just join the lists.

### Merging `CymruIpOriginLayer`

What needs to be merged (all four cases):

1. List of nodes to install the service on.

How to merge (all four cases):

1. Just join the lists.

### Merging `WebServiceLayer`

What needs to be merged (all four cases):

1. List of nodes to install the service on.

How to merge (all four cases):

1. Just join the lists.

## Core Components

### Merging Network

Merge criteria: invoke `merge` if the network has the same type, prefix, and belong to the same ASN.  (all four cases)

- If network merge was invoked with a network of different type (IX/internal), prefix, or ASN, error out.
- If network type is not IX, error out. For local networks, even if they have the same prefix, we cannot reliably merge them, as we might see host/router IP conflicts, and those host/router can be doing anything, so we can't merge them.

What needs to be merged: 

1. Name string
2. `AddressAssignmentConstraint` object
3. IP address assigners
    - Router address generator
    - Host address generator
4. List of connected nodes
5. Link configurations:
    - default latency
    - default bandwidth
    - default packet drop
    - mtu

How to merge:

Let's assume the merge call was `netA.merge(netB)`.

1. Use `netA.getName()`?
2. Use A's `AddressAssignmentConstraint`
3. This is rater non-trivial, as the generator is provided by `AddressAssignmentConstraint`, and may be implemented by the user. The best idea here will be to re-write `AddressAssignmentConstraint` and move the address assignment logic inside too. This way, we can implement something like `AddressAssignmentConstraint::merge` instead. For the default implementation, we can create a list to track used IP address and merge the lists.
4. See merging connected hosts section below.
5. Use A's configurations? 

#### Merging connected hosts

- If we found IP conflict and the node type is not RS, error out.
- If we found IP conflict and the node is RS, drop one of the RS.