# Y11: Smurf and Fraggle Attacks

This example recreates the core mechanism of the historical Smurf attack and Fraggle attack 
inside a controlled SEED Emulator lab. They both use direct broadcast to launch denial-of-service
attacks. Smurf uses ICMP while Fraggle uses UDP.

The example uses the mini-Internet topology from
`examples/internet/B00_mini_internet`. It then turns AS152 into a vulnerable
directed-broadcast network with many hosts. In the Smurf attack, the attacker sends ICMP echo
requests to AS152's directed broadcast address while spoofing the victim's
source IP address. Hosts on the AS152 LAN respond to the victim, amplifying the
attacker's traffic.

The Fraggle variant uses the same topology and directed-broadcast behavior, but
the attacker sends spoofed UDP packets to the AS152 directed broadcast address.
Each AS152 host runs a bounded UDP chargen-like lab daemon and sends a UDP
reply to the spoofed victim address.


## Roles

- Attacker: AS150 `host_0`.
- Victim: AS151 `host_0`. The default victim's address is: `10.151.0.71`
- Legitimate client: AS153 `host_0`. It probes the victim's HTTP service five
  times per second and serves latency and goodput measurements to the frontend.
- AS152 `router0`: vulnerable router with directed broadcast forwarding enabled.
- AS152 `host_0` ... `host_N`: amplifier hosts that respond to broadcast pings
  and run the UDP Fraggle amplifier daemon.

- The default directed broadcast address is `10.152.0.255`
- The default Fraggle UDP service port is `19`
- The default victim-side UDP reply port is `7000`


## Generate the Emulator

From the example folder,

```sh
python ./emulator.py --platform amd
```

To change the number of amplifier hosts on the AS152 LAN, use the `--target-hosts` option (the default value is quite low, so to see the desired DoS effect, use a large number).
The existing `10.152.0.0/24` network supports at most 252 amplifier hosts. A
larger experiment must use a wider subnet rather than assigning more addresses
inside this `/24`.

```sh
python ./emulator.py --platform amd --target-hosts 200
```

The generated Docker files are placed in the`output` folder. We can go to this folder, build the container images and start the emulator.


## Launch and Visualize the Attacks

After building and running the emulator, we can launch the attack and visualize the attack impact.
The best way to see the attack effect is from the victim's point of view. This example installs the
Traffic Visualizer web application on the victim container. It starts automatically and passively
captures incoming attack traffic with `tcpdump`.

The shared server, base dashboard, synthetic HTTP service, and health probe are
loaded from `tools/TrafficVisualizer`. This example owns their addresses,
startup wiring, capture configuration, thresholds, and a frontend extension
that presents the Smurf/Fraggle-specific results. AS151 runs the independent
HTTP service on port `8000`. AS153 probes its latency five times per second and
measures HTTP goodput every five seconds. The probe serves those measurements
on host port `8082`, and the browser fetches them directly instead of routing
health data through the victim. The dashboard is published
on the host at the following URL. Open this address in a browser.

```text
http://localhost:8081
```

Trigger the Smurf attack from another terminal with the following commands. Adjust the
interval value to control the attack speed. Find the value that can congest
the victim's network, so the attack impact is clearly visible.

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/demo/trigger_attack.sh --count 100 --payload-size 1200 --interval 0.05
```

Trigger Fraggle with:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/demo/trigger_attack.sh --mode fraggle --count 100 --payload-size 1200 --interval 0.05
```

The visualization shows matching packet and IP-layer byte totals, values
observed during the previous second, and an animation whose density and marker
size reflect the recent traffic. The Victim Impact panel separately shows the
legitimate service's current latency, recent success rate, failures, current
and average goodput, and separate latency and goodput timelines. Higher cyan
latency bars are worse; higher green goodput bars are better; red means a probe
failed. Packet statistics come from the victim endpoint, while health data
comes from the host-forwarded probe endpoint:

```text
http://127.0.0.1:8080/api/stats
http://localhost:8082/api/health
```

The default three-packet commands demonstrate amplification but may not consume
enough resources to degrade the HTTP service on a fast host. To experiment with
service impact, increase `--count` gradually while watching the impact panel.
Keep the emulator isolated and stop once the intended effect is visible.


### Change capacity at runtime

To see the impact of the DoS attack, let's put a limit on the ingress link. This way,
the attacker's packets can exhaust the bandwidth of the victim's network.
No limit is enabled by default. The following command sets the limit on the gateway
to `15mbit`, essentially limiting the ingress bandwidth of the AS151 network.

```sh
docker compose -f output/docker-compose.yml exec brdnode_151_router0 \
  /opt/demo/traffic_visualizer/network_control.py set \
  --subnet 10.151.0.0/24 --rate 15mbit
```

Inspect or remove the limit by replacing `set --rate 15mbit` with `status` or
`clear`.


Internet Map is still useful for seeing packets move through the topology, but
the victim dashboard makes the key lesson clearer: a small number of spoofed
requests can cause many hosts to send replies to the victim.


## How The Smurf Attack Is Enabled

A Smurf attack needs three technical conditions. Modern networks usually break
at least one of them; this example deliberately enables all three inside the
emulator.

First, the attacker must be able to send an ICMP echo request with a spoofed
source address. In this example, AS150 runs:

```text
/opt/demo/smurf_attack.py
```

This script opens a raw socket and builds a packet manually. The packet's
source address is set to the victim, `10.151.0.71`, while the destination is the
AS152 directed broadcast address, `10.152.0.255`.

Second, the router for the target LAN must forward directed broadcast packets.
Normally, routers no longer do this. We enables it on AS152 `router0` using:

```sh
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.bc_forwarding=1
sysctl -w net.ipv4.conf.default.bc_forwarding=1
```

The example also writes `1` to every existing interface-specific
`bc_forwarding` file under:

```text
/proc/sys/net/ipv4/conf/*/bc_forwarding
```

This makes AS152 `router0` forward a packet addressed to `10.152.0.255` onto
the AS152 LAN as a broadcast.

Third, hosts on the target LAN must answer broadcast ICMP echo requests.
Modern Linux hosts normally ignore these requests. We change this behavior on
the AS152 amplifier hosts with:

```sh
sysctl -w net.ipv4.icmp_echo_ignore_broadcasts=0
```

For Smurf, when the spoofed packet reaches the AS152 LAN, many AS152 hosts receive the
same broadcast echo request. Each host sends an ICMP echo reply to the spoofed
source address, so the replies go to AS151 `host_0`, the victim.


## How The Fraggle Attack Is Enabled

The Fraggle attack also depends on the directed broadcast, which is already enabled 
on AS152 `router0. We also run the following UDP daemon on each AS152 hosts:


```text
/opt/demo/fraggle_amplifier.py
```

This is a small lab-only UDP daemon. It listens on UDP port `19`, accepts lab
traffic from `10.*` addresses, and sends a bounded chargen-like response back
to the packet source. When the attacker spoofs the source address as the
victim, all amplifier replies go to AS151 `host_0`.

The amplification factor depends mainly on the number of AS152 hosts. If
`--target-hosts 30` is used, one spoofed broadcast request can produce replies
from many of those 30 hosts.

## Standard Test Runner

This example follows the `examples/sample` pattern:

```sh
python seedemu/testing/cli.py all examples/yesterday_once_more/Y11_smurf_attack/example.yaml \
  --artifact-dir ci-artifacts/y11-smurf-attack
```

The runtime test verifies:

- the directed-broadcast router and amplifier hosts are generated;
- AS152 router has `bc_forwarding` enabled;
- AS152 hosts respond to broadcast ICMP echo requests;
- the victim receives multiple ICMP echo replies after the attacker sends
  spoofed echo requests to `10.152.0.255`.
- AS152 hosts run the bounded UDP Fraggle amplifier daemon;
- the victim receives multiple UDP replies after the attacker sends spoofed UDP
  requests to `10.152.0.255:19`.
- AS151 runs the legitimate HTTP service and AS153 runs the external probe;
- the probe API serves latency and goodput measurements directly to the frontend.

## Safety

Run this only inside an isolated emulator. The example deliberately recreates an
unsafe historical router behavior that modern routers normally disable. The
Fraggle UDP service is a lab daemon with bounded response size and lab-prefix
filtering; it is not intended to be exposed outside the emulator.
