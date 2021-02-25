# Binding configuration

This document specifies the schema of the component binding configuration file.

## Objects

### Top-level object: `Configuration`

This is the top-level object in the configuration.

|field|type|optional?|default|description|
|--|--|--|--|--|
|`bindings`|dictionary of `Binding` objects, where the key is `string`|yes|`{}`|binding list. `key` of the item indicates the name of pre-bulit nodes in the component. the `key` can be regex.|
|`options`|free-form object|yes|`{}`|options for the component; this will be converted to a python dictionary object and passed to the component.|

### Object: `Binding`

This object specifies the binding of a single server in the component.

|field|type|optional?|default|description|
|--|--|--|--|--|
|`filter`|`Filter` object|yes|`{}`|rules to filter out candidate nodes.|
|`action`|`Action` enum|yes|`RANDOM`|action to take on the candidate nodes.|

### Object: `Filter`

This object narrows down nodes for the binder to select from by giving a set of filter rules. Multiple rules can be given at the same time.

|field|type|optional?|default|description|
|--|--|--|--|--|
|`asn`|`int`|yes|`undefined`|select nodes in AS `asn` only.|
|`node_name`|`str`|yes|`undefined`|select node with name `node_name` only. can be regex.|
|`ip`|`str`|yes|`undefined`|select node with IP `ip` only.|
|`prefix`|`str`|yes|`undefined`|select node with IP within `prefix` only.|
|`any_services`|array of `str`|yes|`[]`|select node with any of the services specified in `any_services` installed only.|
|`all_services`|array of `str`|yes|`[]`|select node with all of the services specified in `all_services` installed only.|
|`not_services`|array of `str`|yes|`[]`|select node without any of the services specified in `not_services` installed only.|
|`lambda`|`str`|yes|`undefined`|advance usage; select node with lambda function provided.|

### Enum: `Action`

This enum sets the action to take on nodes that passwd the filters.

- `RANDOM`: pick one of the nodes randomly.
- `FIRST`: pick the first node.
- `LAST`: pick the last node.

## Examples

The examples here assume a DNS infrastructure component with following servers:

- `root_server_[1-20]`
- `com_server_[1-10]`
- `net_server_[1-10]`
- `org_server_[1-10]`
- `example_com_server_1`
- `example_org_server_1`

### Pick random node for all servers

Configuration:

```yaml
```

That's it. Nothing is needed as picking randomly will be de default.

### Install root servers only on node with name `root_server`

Configuration:

```yaml
bindings:
    - "root_server_*":
        - filter:
            - node_name: "root_server"
```

This filter matches all root server services (i.e., `root_server_1`, `root_server_2`, ..., `root_server_20`) and limit the name of the node to be `root_server`. The nodes can be in different AS (in fact, they need to be in different ASes, as the emulator does not allow having the same node name in the same AS.)

### Install com servers only on nodes in AS150

Configuration:

```yaml
bindings:
    - "com_server_.*":
        - filter:
            - asn: 150
```

This filter matches all com server services (i.e., `com_server_1`, `com_server_2`, ..., `com_server_10`) and limit the ASN of the node to be 150.

### Install net servers only on nodes with name start with `net_server_` and in AS151

```yaml
bindings:
    - "net_server_.*":
        - filter:
            - asn: 151
            - node_name: "net_server_.*"
```

This filter matches all net server services (i.e., `net_server_1`, `net_server_2`, ..., `net_server_10`), limit the ASN of the node to be 151, and limit the name of node to be `net_server_*`.

### Install org servers in `10.160.0.0/24` and `10.161.0.0/24`:

```yaml
bindings:
    - "org_server_[1-5]":
        - filter:
            - prefix: "10.160.0.0/24"
    - "org_server_[6-10]":
        - filter:
            - prefix: "10.161.0.0/24"
```

### Install `example.com` and `example.org`

```yaml
bindings:
    - "example_(com|org)_server_1":
        - filter:
            - node_name: "example_web"
            - any_services:
                - "WebService"
```

### Lambds

```yaml
bindings:
    - "*":
        - filter:
            - lambda: "lambda service_name, node: not node.getServices().has('DomainNameCachingService')"
```

For lambda, `service_name` is the name of the services to bind (e.g., `root_server_1`, `com_server_1`, etc.), and `node` is the node object in the emulator.