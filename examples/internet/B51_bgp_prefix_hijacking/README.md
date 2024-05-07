# BGP Attack: Network Prefix Hijacking

This example demonstrates how to launch the network prefix hijacking
attack inside the emulator. It uses the mini-Internet built from 
Example-B00 as the base.


# Creating a Malicious Autonomous System

We will create a new autonomous system (`AS-199`) and use it as the 
attacker. We attack its BGP router to Internet exchange `ix-105`, and peer
it with `AS-2`. It should be noted that the peering relationship should 
be set to `Unfiltered`, or the attack approach in this example will not 
work. The attack will still work if we choose to use the `Provider` relationship, but
the setup will be more complicated. For the sake of simplicity, we 
choose to use the `Unfiltered` type.

```
as199 = base.createAutonomousSystem(199)

as199.createRouter('router0').joinNetwork('net0').joinNetwork('ix105')
ebgp.addPrivatePeerings(105, [2],  [199], PeerRelationship.Unfiltered)
```

# Hijacking AS-153's Network Prefix

We would like to use `AS-199` to hijack the network `10.153.0.0/24`. 
To do that, we need to modify the BGP setup on the BGP router inside
`AS-199`. We have only set up one BGP router. Go to this container,
go to the `/etc/bird` folder, and open the BGP configuration file `bird.conf`.
The `vim` and `nano` editors are already installed inside the container. 
Add the following to the end of the configuration file.
We announce two network prefixes `10.153.0.0/25` and `10.153.0.128/25`, which 
completely cover the prefix `10.153.0.0/24` announced by `AS-153`. 
Any IP address inside `10.153.0.0/24` will match two IP prefixes, one 
announced by the attacker, and the other one announced by 
`AS-153`, but the one announced by the attacker has a longer
match (25 bits, compared to the 24 bits from `AS-153`), so the 
attacker's prefix will be selected by all the BGP routers on
the Internet.


```
protocol static hijacks {
    ipv4 {
        table t_bgp;
    };
    route 10.153.0.0/25 blackhole   { bgp_large_community.add(LOCAL_COMM); };
    route 10.153.0.128/25 blackhole { bgp_large_community.add(LOCAL_COMM); };
}
```

Note: in the real world, the longest prefix allowed in the DFZ is /24. So
realistically, a /25 prefix will not be accepted by any of the peers, and
therefore hijacking with /25 prefixes will not work (but one can still hijack a
/23 with two /24s with the same principle). In our emulator, we did not enforce
the maximum prefix length. 

After making the change, ask the BGP router to reload configuration file
using the following command.

```
# birdc configure
```


# Testing

We can pick any hosts on the emulator Internet, run the following command, 
and we will not be able to get any reply, because the packets are hijacked
by `AS-199` and sent to a blackhole.

```
ping 10.153.0.71
```

To see where the packets go, we can start the map tool, set the 
filter to `icmp`. We will see that all the ping packets are rerouted to
`AS-199`. 

On the map, we can go to `AS-199`'s BGP router, click the `Disable` button
to disable its BGP session. We will see immediately that the traffic 
gets rerouted back to `AS-153`, and our ping program gets the replies.
We can enable the BGP session again to start the attack. 


**Additional exercise**: Instead of using `/25` in the hijacked network prefix, 
we can try `/24`, `/26`, etc, and see how it works. These additional exercises
will help students better understand how the attack works.


# Hijacking Network Prefixes from a Real Autonomous System

It will be more fun to launch such an attack on the real autonomous system,
but without doing real damages to the real world. This is made possible 
by the emulator. We can add a real-world autonomous system inside the emulator.

The emulator built by Example-B00 already includes a real-world AS, `AS-11872`.
It announces several network prefixes to the emulator, and these network 
prefixes are real and they are owned by the real-world `AS-11872`. 
Inside the emulator, packets going to these network prefixes 
will be routed to the emulated `AS-11872` autonomous system, which
will then forward the packets to their real destination 
on the real Internet. Responses will come back to this emulated 
autonomous system, and be routed to the sender inside the emulator. 

By connecting the emulated Internet with the real Internet, our emulator
becomes a shadow Internet. Packets to a real-world destination will traverse
through our shadow Internet first, before getting into the real Internet. 
Therefore, for many attacks that cannot (legally and/or technically) 
be launched on the real Internet, they can be launched on the shadow
Internet. Users will observe and feel the same impact as if the attack 
were launched against the real Internet. 


