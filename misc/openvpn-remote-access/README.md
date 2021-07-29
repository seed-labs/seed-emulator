### OpenVPN remote access

The `ovpn-client.ovpn` file contains the defualt OpenVPN client configuration for the OpenVPN remote access provider.

For details about remote access providers, see [example 03](/examples/A03-real-world) (real-world).

To connect to the OpenVPN server, first do `docker ps` to find out the port number:

```
$ docker ps
CONTAINER ID   IMAGE                      COMMAND                  CREATED          STATUS          PORTS                                         NAMES
b0651a9266bf   output_rnode_152_br-net0   "/start.sh"              23 minutes ago   Up 8 seconds    0.0.0.0:65001->1194/udp, :::65001->1194/udp   as152r-br-net0-192.168.160.253
f39950cf7abc   output_rnode_11872_rw      "/start.sh"              23 minutes ago   Up 10 seconds                                                 as11872r-rw-10.101.0.118
8a38c4860dc7   output_rnode_151_br-net0   "/start.sh"              23 minutes ago   Up 9 seconds    0.0.0.0:65000->1194/udp, :::65000->1194/udp   as151r-br-net0-192.168.160.254
07e45e838360   output_hnode_152_web       "/start.sh"              33 minutes ago   Up 10 seconds                                                 as152h-web-10.152.0.79
...
```

Here, two networks are configured for remote access (`AS151/net0`, `AS152/net0`). The OpenVPN servers are hosted by nodes that start with the prefix `br-` (`152_br-net0` and `151_br-net0` here). You can see their ports under the `PORTS` column. Here, `AS152/net0` are avaliable on port `65001`, and `AS151/net0` are avaliable on port `65000`.

To connect to a network, on a separate host (other then the docker host), do the followings:

```
# openvpn --config ovpn-client.ovpn --remote <docker_host> <port> 
```

Where the `<docker_host>` is the IP address or hostname of the docker host and the `<port>` is the port number of the server you would like to connect to. 

Note that it is important that you use a separate host to run the OpenVPN client. If you run it directly on the emulator host and configured the default routes, that will create a loop when the emulator tries to route the traffic to the real world (AS11872 in example 05).

If it worked, you will see something like this:

```
# openvpn --config ovpn-client.ovpn --remote 172.16.0.1 65000
Fri Jul  9 17:24:26 2021 OpenVPN 2.4.7 x86_64-pc-linux-gnu [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Apr 28 2021
Fri Jul  9 17:24:26 2021 library versions: OpenSSL 1.1.1d  10 Sep 2019, LZO 2.10
Fri Jul  9 17:24:26 2021 TCP/UDP: Preserving recently used remote address: [AF_INET]172.16.0.1:65000
Fri Jul  9 17:24:26 2021 UDP link local: (not bound)
Fri Jul  9 17:24:26 2021 UDP link remote: [AF_INET]172.16.0.1:65000
Fri Jul  9 17:24:26 2021 Peer Connection Initiated with [AF_INET]172.16.0.1:65000
Fri Jul  9 17:24:28 2021 TUN/TAP device tap0 opened
Fri Jul  9 17:24:28 2021 /sbin/ip link set dev tap0 up mtu 1500
Fri Jul  9 17:24:28 2021 /sbin/ip addr add dev tap0 10.151.0.71/24 broadcast 10.151.0.255
Fri Jul  9 17:24:28 2021 Initialization Sequence Completed
```

You are now connected to the AS151's  `net0`:

```
$ ip -4 -br ad
lo               UNKNOWN        127.0.0.1/8
ens33            UP             172.16.0.3/24
tap0             UNKNOWN        10.151.0.71/24
$ ip route
default via 172.16.0.1 dev ens33
10.151.0.0/24 dev tap0 proto kernel scope link src 10.151.0.71
172.16.0.0/24 dev ens33 proto kernel scope link src 172.16.0.3
```

However, note that there is no defualt route configured. Add the defualt routes manually if you want to use the AS151's router as your internet connection:

```
# ip route add 0.0.0.0/1 via 10.151.0.254
# ip route add 128.0.0.0/1 via 10.151.0.254
```

And you should now be able to connect to other nodes in the emulator now:

```
$ traceroute 10.152.0.79
traceroute to 10.152.0.79 (10.152.0.79), 30 hops max, 60 byte packets
 1  10.151.0.254 (10.151.0.254)  8.330 ms  8.337 ms  8.336 ms
 2  10.100.0.150 (10.100.0.150)  9.708 ms  9.724 ms  9.725 ms
 3  10.150.0.253 (10.150.0.253)  9.726 ms  10.621 ms  10.642 ms
 4  10.150.1.253 (10.150.1.253)  10.644 ms  12.077 ms  12.084 ms
 5  10.150.2.253 (10.150.2.253)  12.085 ms  12.085 ms  12.114 ms
 6  10.101.0.152 (10.101.0.152)  12.125 ms  6.454 ms  6.439 ms
 7  10.152.0.79 (10.152.0.79)  6.394 ms  10.623 ms  10.606 ms
```

**Known issue**: If you start the client before starting the emulation, it may cause the server side to fail. In such a case, the client may appear connected, but you will not be able to reach any host on the emulated network. This will also happen if you left the client running and restarted the emulator, as the client will reconnect to the server and break it again. To prevent this from happening, do not start the client unless you see the `br-xxx` node report `ready! run 'docker exec -it xxxxxxxxxxxx /bin/zsh' to attach to this node`.
