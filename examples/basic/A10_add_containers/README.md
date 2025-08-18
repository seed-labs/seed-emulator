# Add existing containers

Note: this method is the older approach; we have introduced a new approach (listed
in another example).

In some cases, we already have a group of existing containers, 
we would like to add them to the emulator. How do we do this? 
In this example, the existing containers are put inside the
`containers` folder. We will add them to the emulator
created in this example. 


To run this example, run the emulator first, and then go to
the `containers` folder, run the new containers. These containers
will be added to the emulator. They will not show up on the Map
visualization app (we will fix this problem in the near future).
You can get into these containers and ping the other machines. 


## Adding a container to a network inside the emulator

To add a container to an existing network, we just need
to find out the name of the network, and then in 
the `docker-compose.yml` file, we define it 
as `external`. This tells docker not to create the 
network, instead, use an existing network.

```
services:
    hnode_new_host1:

        networks:
            output_net_152_net0:
                ipv4_address: 10.152.0.99

networks:
    output_net_152_net0:
      external: true
```

## Adding default route to new containers

After adding a new container to a network, we need to manually
set up its routing information. We can add the following
commands to the container's `start.sh`. 

```
ip rou del default 2> /dev/null
ip route add default via 10.151.0.254 dev eth0
```

It should be noted that running the `ip route add` command requires
privileges. We need to add the following options to the 
container setup inside `docker-compose.yml`.

```
   cap_add:
       - ALL
   privileged: true
```


