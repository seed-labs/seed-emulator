### nysernet.conf

```
options:
    nysernet_edge_router_1:
        internet_exchanges:
            - ix100:
                rs_peer: false # default to true, this overrides it
                private_peers:
                    - 12345 # just imagine this is internet2's asn

    nysernet_edge_router_2:
        internet_exchanges:
            - ix101
            - ix102
bindings:
    # nothing, base layer don't bind anything to nodes
```

### interent2.conf

```
options:
    internet2_edge_router_1:
        internet_exchanges:
            - ix100:
                private_peers:
                    - 54321 # just imagine this is nysernet's asn

bindings:
```

### dns.conf

```
options:
    enable_dnssec: true

bindings:
    com_server:
        - asn: 150
        - ...
    ...
```