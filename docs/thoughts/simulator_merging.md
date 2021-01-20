# Merging simulators

Idea: perform merging top-down, e.g.:

```
simulatorA.merge(simulatorB)
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
- Overlapping internal networks (try merge network).
- For overlapping network:
- Node IP conflict (try merge node?)
- Router IP conflict (try merge node?)
- RS IP conflict (just pick one, RS are the same)

For merging nodes:
- Conflicting router configurations,
- Conflicting hosts node services.

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

Problem: Do we really want to merge two networks? Consider some of the following problems:

- What to do if two nodes have the same IP address?
    - Option A: merge two nodes; see the node merging section below.
    - Option B: assign new IP addresses to conflicting nodes.

For option A, check the node merging section below for a detailed discussion.

For option B, what if the user hard-coded IP address in the simulation? For example, what if the user already added DNS records to point to one of the nodes?

Special case: Internet exchange network. If there are duplicate IP addresses, the merge will just fail, as IP addresses are assigned to exchange networks according to their ASN. However:

- What if two simulator used different `AddressAssignmentConstraint` and for the same AS, their address is different according to the `AddressAssignmentConstraint`? 

### Merging Node

Merge criteria: see Merging Network section above.

What needs to be merged: 

- Name string
- interface list
- file list
- software list
- build commands
- start commands
- ports
- privileged flag

Special cases:

- RS node: just pick one and keep it. RS nodes are always the same currently.

Problems: 

- Currently, for services (e.g., DNS layer, web service layer) installed on the nodes, only the layer themselves keep track of what nodes to install the services on. What to do when we merged the nodes?