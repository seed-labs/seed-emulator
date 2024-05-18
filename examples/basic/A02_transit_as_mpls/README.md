# Transit AS (MPLS)

This topology of this example is exactly the same as that in `A01-transit-as`. 
The only difference in this example is that we will now use MPLS instead of OSPF and
IBGP in the transit network. With MPLS, non-edge routers don't need to carry
the BGP routing table at all. Non-edge routes only need to keep track of a
small amount of MPLS labels, which greatly reduces the resources needed on
non-edge routes.


## Step 0: host system support

MPLS requires support from the Linux kernel; for this example to work properly,
load the MPLS kernel module on the emulator host with the following command, as
root:

```
# modprobe mpls_router
```

## Import and create required components

In this setup, only the `Mpls` layer is new, so we will only
discuss this layer.

- The `Mpls` layer automatically sets up MPLS. The default behavior for the MPLS layer are as follow:
    - First, it classifies router nodes as edge routers and non-edge routers. Routers with at least one connection to an internet exchange or to a network with host role nodes connected are considered as edge routers. All other routers are considered as non-edge routers.
    - Then, for all edge routers, it setup LDP, OSPF and IBGP full mesh sessions between them. For all non-edge routers, it setup only LDP and OSPF.

```python
mpls = Mpls()
```

## Create a transit autonomous system

### Configure MPLS

Unlike OSPF and IBGP, MPLS needs to be explicitly enabled for an autonomous system. This can be done by `Mpls::enableOn`:

```python
mpls.enableOn(150)
```

The `enableOn` call takes on parameter, the ASN to enable MPLS on.

Here, only `r1` and `r4` are edge routers; thus, IBGP session will only be set up between them. `r2` and `r3` will only participate in OSPF and LDP. The topology looks like this:

```
       |  AS150's MPLS backbone                         |
       |          ____________ ibgp ___________         |
       |         /                             \        |
as151 -|- as150_r1 -- as150_r2 -- as150_r3 -- as150_r4 -|- as152 
       |                                                |
```

Since `r2` and `r3` don't carry the tables from AS151 and AS152, traceroute will look like this:

```
HOST: 0e58e675b98b Loss%   Snt   Last   Avg  Best  Wrst StDev
 1.|-- 10.152.0.254  0.0%    10    0.1   0.1   0.1   0.1   0.0
 2.|-- 10.101.0.150  0.0%    10    0.1   0.1   0.1   0.2   0.0
 3.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
 4.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
 5.|-- 10.150.0.254  0.0%    10    0.1   0.1   0.1   0.2   0.0
 6.|-- 10.100.0.151  0.0%    10    0.3   0.2   0.1   0.3   0.1
 7.|-- 10.151.0.71   0.0%    10    0.2   0.2   0.1   0.3   0.0
```

The two missing hops are `r2` and `r3`. We can also validate that the network is indeed running on MPLS by `tcpdump`:

```
root@d5d8ad0d6d48 / # tcpdump -i net1 -n mpls
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on net1, link-type EN10MB (Ethernet), capture size 262144 bytes
19:39:33.831880 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 1, length 64
19:39:33.832051 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 1, length 64
19:39:34.877246 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 2, length 64
19:39:34.877314 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 2, length 64
^C
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```
