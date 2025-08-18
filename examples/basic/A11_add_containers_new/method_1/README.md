# Add existing containers



## Adding an existing container

We have implemented an API called `attachCustomer` in the `Docker` compiler class. 
It allows us to add a pre-constructed docker compose entry to the `docker-compose.yml`
file. The network and the port-forwarding field of this entry can be 
dynamically constructed through the `asn`, `net`, `ip_address`, and `port-forwarding` arguements. 

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
                 port_forwarding="9090:80/tcp")
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
                  port_forwarding='8080:8080/tcp')
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

If the container uses DHCP, typically, the default route will be provided by the DHCP server.


## Notes

It should be noted that for the added containers to show up on the Internet Map tool,
they should provide the required meta data and have some required software installed.
In this example, these are not done, so they will not show up on the Map. 
We will resolve this issue in the future. 


