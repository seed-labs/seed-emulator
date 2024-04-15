dovesnap
=================

dovesnap is a docker network provider, that works with FAUCET and OVS. This allows docker networks to make use of FAUCET's features, such as mirroring, ACLs, and Prometheus based monitoring.

Thanks to the folks who wrote the orginal [docker-ovs-plugin](https://github.com/gopher-net/docker-ovs-plugin) which is what this project was forked from.

See also https://docs.faucet.nz for FAUCET documentation, including monitoring documentation (dovesnap will supply FAUCET-based monitoring without needing configuration, when started as below).

### Requirements

* Linux host running a supported version docker (x86 and Pi are supported)
* Optionally: additional physical interfaces to connect other hosts also running dovesnap
* non-netfilter iptables. For Debian/Ubuntu, follow the legacy option at https://wiki.debian.org/iptables (this will be addressed in a future version):

```
$ sudo apt-get install nftables && sudo nft flush ruleset && sudo apt-get purge nftables
$ sudo apt-get --reinstall install iptables && sudo update-alternatives --set iptables /usr/sbin/iptables-legacy && sudo /etc/init.d/docker restart
```

### Installing as a systemd service

The `install.sh` and `uninstall.sh` scripts can be used to install and uninstall dovesnap as a systemd managed service. An upgrade can be accomplished by executing a `git pull` within `~dovesnap` as the `dovesnap` user, and restarting the service. Persistent configuration is stored in `~dovesnap/service.env`.

### QuickStart Instructions

These instructions describe the most basic use of dovesnap - creating a docker network with Internet access, where dovesnap provides all the FAUCET infrastructure. See below for more advanced usage.

**1.** Make sure you are using Docker 1.10 or later

**2.** You need to `modprobe openvswitch` on the machine where the Docker Daemon is located. Make sure that while the module is loaded, OVS is not running on the host.

```
$ sudo modprobe openvswitch
```

**3.** Create a directory for FAUCET to store its configuration:

```
$ sudo mkdir /etc/faucet
```

**4.** Start dovesnap.

`$ docker compose build && docker compose -f docker-compose.yml -f docker-compose-standalone.yml up -d`

**5.** Now you are ready to create a new network

```
$ docker network create mynet -d dovesnap --internal -o ovs.bridge.mode=nat -o ovs.bridge.dpid=0x1 -o ovs.bridge.controller=tcp:127.0.0.1:6653,tcp:127.0.0.1:6654
```

`-d dovesnap` tells docker to use dovesnap as a network provider.

`--internal` tells docker not to supply an additional network connection to containers on the new network for internet access. This is essential for dovesnap to complete control over connectivity.

`-o ovs.bridge.mode=nat` tells dovesnap to arrange NAT for the new network.

`-o ovs.bridge.dpid=0x1 -o ovs.bridge.controller=tcp:127.0.0.1:6653,tcp:127.0.0.1:6654` tell dovesnap which FAUCET will control this network (you can provide your own FAUCET elsewhere on the network, but in this example we are using a dovesnap-provided FAUCET instance).

**6.** Test it out!

```
$ docker run -d --net=mynet --rm --name=testcon busybox sleep 1h
$ docker exec -t testcon ping 4.2.2.2
```

### Advanced usage

There are several options available when creating a network, and when creating a container on a network, to access FAUCET features.

You can view dovesnap's OVS bridges using `ovs-vsctl` and `ovs-ofctl`, from within the dovesnap OVS container. You can even use `ovs-vsctl` to add other (for example, physical) ports to a dovesnap managed bridge and dovesnap will monitor them for you. However, it's recommended that you use dovesnap's own options (below) where possible.

#### Required options

`ovs.bridge.dpid=<dpid> -o ovs.bridge.controller=tcp:<ip>:<port>`

Every dovesnap network requires a DPID (for OVS and FAUCET), and at least one controller for OVS. dovesnap will provide FAUCET and Gauge processes to do forwarding and monitoring by default - at least one FAUCET is required, and one Gauge if monitoring is desired.

#### Network options

These options are supplied at `docker network create` time.

##### Bridge modes

There are three `ovs.bridge.mode` modes, `flat`, `nat`, and `routed`. The default mode is `flat`.

- `flat` causes dovesnap to provide connectivity only between containers on this docker network - not to other networks (essentially, provide a VLAN - no routing).

- `nat` causes dovesnap to provision a gateway, and NAT, for the docker network.

- `routed` causes dovesnap to provision a gateway, for the docker network. An upstream network may provide NAT if needed.

If NAT is in use, you can specify `-p <outside port>:<inside port>` when starting a container. dovesnap will provision a DNAT rule, via the network's gateway from the outside port to the inside port on that container. This mapping won't show up in `docker ps`, as dovesnap is not using docker-proxy.

You can also specify an input ACL for the gateway's port with `-o ovs.bridge.nat_acl=<acl>`, and a default ACL for container ports with `-o ovs.bridge.default_acl=<acl>`.

##### Preallocated ports

`-o ovs.bridge.preallocate_ports=10`

This requests that N ports be pre-allocated with the default ACL (if any) when the network is created. This makes container startup faster, because FAUCET network has already
been configured.

##### Userspace mode

`-o ovs.bridge.userspace=true`

This requests a user space ("netdev"), rather than kernel space switch from OVS. Certain OVS features such as meters, used to implement rate limiting, will only work on a user space bridge.

##### MAC on OVS local port

`-o ovs.bridge.ovs_local_mac=0e:01:00:00:00:03`

This option sets the MAC address of OVS' "local" port on the switch.

You can set the MAC address on a container, with `docker run --mac-address <mac>` (https://docs.docker.com/engine/reference/run/#network-settings)

##### Adding a physical port/real VLAN

`-o ovs.bridge.add_ports=eno123/8`

Dovesnap will connect `eno123` to the Docker network, and attempt to use OVS OFPort 8 (OVS will select another port number, if for some reason port 8 is already in use). You can specify more ports with commas. The OFPort specification is optional - if not present dovesnap will select the next free port number. If specifying a port, you can also specify a third parameter - the ACL name to be applied to the port.

##### Adding a physical port for coprocessing

`-o ovs.bridge.add_copro_ports=eno123/8`

Dovesnap will connect `eno123` to the Docker network as a FAUCET coprocessor port, and attempt to use OVS OFPort 8 (OVS will select another port number, if for some reason port 8 is already in use). You can specify more ports with commas. The OFPort specification is optional - if not present dovesnap will select the next free port number. If specifying a port, you can also specify a third parameter - the ACL name to be applied to the port.

##### Specifying a specific VLAN to use

`-o ovs.bridge.vlan=100`

This adds the VLAN tag of 100 for the Docker network. The default is 100.

#### Specifying an VLAN output ACL to use

`-o ovs.bridge.vlan_out_acl=allowall`

This adds the output ACL `allowall` to the VLAN used on the docker network.

NOTE: this enables use of Faucet's egress pipeline feature, which is currently experimental and works only on OVS.

##### Specifying a specific VLAN to use for the mirror tunnel

`-o ovs.bridge.mirror_tunnel_vid=200`

This sets the mirror tunnel VLAN to 200. The default is 256 + the VLAN of the network.

###### Enabling DHCP

`--ipam-driver null -o ovs.bridge.dhcp=true`

docker's IP management of this network will be disabled, and instead dhcp will request and maintain a DHCP lease for each container on the network, using `udhcpc`. `udhcpc` is run outside the container's PID namespace (so the container cannot see it), but within its network namespace. The container therefore does not need any special privileges and cannot change its IP address itself.

##### Mirroring

Dovesnap provides infrastructure to do centralized mirroring - you can have dovesnap mirror the traffic for any container on a network it controls, back to a single interface (virtual or physical). This allows you to (for example) run one centralized tcpdump process that can collect all mirrored traffic.

To use physical interface `eno99` for mirroring, for example:

`$ FAUCET_PREFIX=/etc/faucet MIRROR_BRIDGE_OUT=eno99 docker compose -f docker-compose.yml -f docker-compose-standalone.yml up -d`

If you want to mirror to a virtual interface on your host, use a veth pair. For example:

```
$ sudo ip link add odsmirrori type veth peer name odsmirroro
$ sudo ip link set dev odsmirrori up
$ sudo ip link set dev odsmirroro up
$ FAUCET_PREFIX=/etc/faucet MIRROR_BRIDGE_OUT=odsmirrori docker compose -f docker-compose.yml -f docker-compose-standalone.yml up -d
$ sudo tcpdump -n -e -v -i odsmirroro
```

From this point, any container selected for mirroring (see below) will have traffic mirrored to tcpdump running on `mirroro`

###### Mirroring across multiple hosts

You might want to run docker and dovesnap on multiple hosts, and have all the mirrored traffic from all the hosts arrive on one port on one host.

You can do this by daisy-chaining the hosts together with dedicated physical ports in a so called "mirror river". On the hosts within the chain, specify `MIRROR_BRIDGE_IN=eth77` (where `eth77` is connected to the previous host). This will cause each host to pass the mirrored traffic along to the final host.

#### Container options

These options are supplied when starting a container.

#### ACLs

`--label="dovesnap.faucet.portacl=<aclname>"`

An ACL will be applied to the port associated with the container. The ACL must already exist in FAUCET (e.g. by adding it to `faucet.yaml`).

If a container is connected to multiple dovesnap networks, it is possible to specify different ACLs per network:

`--label="dovesnap.faucet.portacl=<networkname>:<aclname>/..."`

#### Mirroring

`--label="dovesnap.faucet.mirror=true"`

The container's traffic (both sent and received) will be mirrored to a port on the bridge (see above).

If a container is connected to multiple dovesnap networks, it is possible to specify different mirror options for each network:

`--label="dovesnap.faucet.mirror=<networkname>:<true>/..."`

#### MAC prefix

`--label="dovesnap.faucet.mac_prefix=0e:99`

The prefix of the container interface's MAC address will be replaced with the specified bytes (1 to 5 bytes may be supplied).
This can be convenient when filtering traffic with tcpdump - containers with this label will have an easily identifiable MAC address.

NOTE: where this option is used, the MAC address reported by `docker inspect` will be inaccurate.

#### Visualizing dovesnap networks

Dovesnap can generate a diagram of how containers and interfaces are connected together, with some information about running containers (e.g. MAC and IP addresses). This can be useful for troubleshooting or verifying configuration.

```
$ sudo pip3 install -r requirements.txt
$ cd bin
$ ./graph_dovesnap
```

A PNG file will be created that describes the networks dovesnap controls.
