# Add existing containers



## Adding an existing container

We have implemented an API called `attachCustomContainer` in the `Docker` compiler class. 
It allows us to add a pre-constructed docker compose entry to the `docker-compose.yml`
file. The network field of this entry can be dynamically constructed through the `asn`, `net`, 
`ip_address` arguements. The API also allow users to provide port-forwarding and 
environment-variables arguements. 

```
DOCKER_COMPOSE_ENTRY = """\
    {name}:
        image: busybox:latest
        container_name: {name}
        privileged: true
        command: /bin/sh -c "
                   ip route del default  &&
                   ip route add default via {default_route} &&
                   tail -f /dev/null
                 "
"""

# Attach an existing container to the emulator
docker.attachCustomContainer(
                compose_entry = DOCKER_COMPOSE_ENTRY.format(name="busybox", 
                                 default_route=emu.getDefaultRouterByAsnAndNetwork(150, 'net0')),
                asn=150, net='net0', ip_address='10.150.0.80',
                port_forwarding="9090:80/tcp", env=['a=1', 'b=2'])


emu.compile(docker, './output', override=True)
```

If the `asn` field is not provided, the container will be attached to 
the default network provided by the docker. This network is not reachable from inside 
the emultor. If the `ip_address` is not provided, the actual IP address will either 
be provided by docker, or by the DHCP server (if such as server is present and the 
container is configured to use DHCP). 

When a new container is attached to a network, we need to set up its routing information. 
In the example above, the container is attached to AS-150's `net0`, so we need to use 
the router on this network. The following API helps us get the default router
of a specified network.    

```
emu.getDefaultRouterByAsnAndNetwork(150, 'net0'))
```

We use the result from the API above to set the default router of the container. 
These two commands are already included in the docker compose entry. 

```
ip rou del default 2> /dev/null
ip route add default via 10.150.0.254 dev eth0
```

It should be noted that running the `ip route add` command requires privileges. 
We need to add the following options to the docker compose entry:

```
   privileged: true
```


## Adding the Internet MAP

We can add the Internet MAP tool (an independent container) to the emulator using 
the `attachInternetMap` API, which is a wrapper for the `attachCustomContainer` API (with
the docker compose entry hardcoded. In the future, we will develop useful tools for
the emulator, and they can be added in such a way. 

```
docker.attachInternetMap(asn=150, net='net0', ip_address='10.150.0.90',
                  port_forwarding='8080:8080/tcp', env=['a=1', 'b=2'])

```






## Adding an existing container and show it on the map

If we want the added container to show up on the InternetMap visualization tool, we just need to provide the `node_name` and `show_on_map` parameters.

```python
docker.attachCustomContainer(
                compose_entry = DOCKER_COMPOSE_ENTRY.format(name="busybox2", 
                            default_route=emu.getDefaultRouterByAsnAndNetwork(150, 'net0')),
                asn=150, net='net0', ip_address='10.150.0.81',
                port_forwarding="9091:80/tcp",
                node_name='busybox2', show_on_map=True)

```

## Notes

In this example, the custom container can be displayed on the map, but it cannot be operated on like other containers. We will resolve this issue in the future. 


