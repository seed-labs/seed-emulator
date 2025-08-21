# Add existing containers



## Adding an existing container

We have implemented an API called `attachCustomContainer` in the `Docker` compiler class. 
It allows us to add a pre-constructed docker compose entry to the `docker-compose.yml`
file. The network field of this entry can be dynamically constructed through the `asn`, `net`, 
`ip_address` arguements. The API also allow users to provide port-forwarding and 
environment-variables arguements. 


```
DOCKER_COMPOSE_ENTRY = """\
    seedemu-busybox:
        image: busybox:latest
        container_name: seedemu_busybox
        privileged: true
        command: bash -c "
                   ip route del default  &&
                   ip route add default via 10.150.0.254 &&
                   tail -f /dev/null
                 "
"""

docker = Docker(platform=platform)
docker.attachCustomContainer(compose_entry = DOCKER_COMPOSE_ENTRY,
                 asn=150, net='net0', ip_address='10.150.0.80',
                 port_forwarding="9090:80/tcp", env=['a=1', 'b=2'])

emu.compile(docker, './output', override=True)
```

If the asn field is not provided, the container will be attached to 
the default network provided by the docker. This network is not reachable from inside 
the emultor. If the `ip_address` is not provided, the actual IP address will either 
be provided by docker, or by the DHCP server (if such as server is present and the 
container is configured to use DHCP). 


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



## Adding default route to new containers

After adding a new container to a network, we need to manually
set up its routing information. We can add the following
commands to the docker compose entry when building the container (the 
assumption is that we already know the IP address of the router); 
we can also run these commands after the container is up and the IP address 
of the router is known. 

```
ip rou del default 2> /dev/null
ip route add default via 10.150.0.254 dev eth0
```


## Adding an existing container and show it on the map

In contrast to `Adding an existing container`, only the node_name and show_on_map parameters are added to the attachCustomContainer api

```python

docker.attachCustomContainer(compose_entry = DOCKER_COMPOSE_ENTRY, 
                       asn=150, net='net0', ip_address='10.150.0.80',
                       port_forwarding="9090:80/tcp", node_name='seedemu-busybox', show_on_map=True)
```

## Notes

In this example, the custom container can be displayed on the map,
but it cannot be operated on like other containers.
We will resolve this issue in the future. 


