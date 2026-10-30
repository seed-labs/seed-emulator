# Y10: NTP-Like Amplification

This example recreates the core idea behind historical NTP amplification
incidents inside a controlled SEED Emulator lab. It uses the mini-Internet
topology from `examples/internet/B00_mini_internet`, then adds a few vulnerable
NTP-like UDP services.

The service is intentionally not a real NTP daemon. It is a small Python program
that accepts a tiny monitor-style request and returns a much larger response.
This makes the amplification mechanism clear and avoids depending on obsolete
NTP packages.

## Topology

The base topology is B00. Y10 adds these roles:

- AS150 `host_0`: attacker host, with `/opt/ntp-like/trigger_attack.py`.
- AS151 `host_0`: victim host, with a UDP sink on port `9000`.
- AS153 `host_0`: legitimate client that measures the victim HTTP service.
- AS152 `host_0`: NTP-like amplifier.
- AS160 `host_0`: NTP-like amplifier.
- AS171 `host_0`: NTP-like amplifier.

The amplifier daemon listens on UDP port `123`. A direct `monlist` request is
answered by the amplifier itself. The example also enables a lab-only reflection
simulation command so the attacker can make the amplifiers send their larger
responses to the victim without using raw source-IP spoofing.

## Visualizing The Attack

The clearest way to see the attack is from the victim's point of view. Y10
installs the shared Traffic Visualizer on AS151 `host_0`. It starts
automatically, captures only UDP replies to the victim's port `9000`, and is
published on the host at:

```text
http://localhost:8081
```

Open that URL and trigger the attack from AS150:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/ntp-like/trigger_attack.sh
```

One round sends one request to each of the three amplifiers. Use `--rounds` to
repeat the attack and `--interval` to control the delay between individual
requests. The defaults are one round and 0.2 seconds:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/ntp-like/trigger_attack.sh --rounds 10 --interval 0.05
```

The normal output is flushed after every request so progress is visible while
the attack runs. The `--json` mode instead emits one valid JSON document after
all requests finish.

The generic area displays packet and IP-byte totals, rates, and packet-flow
animation. Y10's extension compares the fixed 64-byte request IP packet with
the average response IP packet and displays the resulting IP-layer byte
amplification as a number and scale. With the default 1,200-byte response
payload, the response IP packet is 1,228 bytes and the scale is approximately
19.2x.

AS151 also runs the shared synthetic HTTP service on port `8000`. AS153 probes
its latency five times per second and measures HTTP goodput every five seconds.
The probe serves its measurements on host port `8082`, and the browser fetches
them directly instead of retrieving them through the victim.
The extension shows the service's health, current latency, success rate,
failures, current and average goodput, and separate latency and goodput
timelines. This makes it possible to compare the incoming amplified traffic
with its effect on legitimate users. The extension files remain example-owned;
the capture agent, HTTP service, probe, runtime controls, and base dashboard are
shared in `tools/TrafficVisualizer`.

The two browser data endpoints are:

```text
http://localhost:8081/api/stats
http://localhost:8082/api/health
```

### Change capacity at runtime

Y10 installs the shared link controller on AS151's gateway. No limit is enabled
by default. For example, limit traffic entering the victim network to 15 Mbps:

```sh
docker compose -f output/docker-compose.yml exec brdnode_151_router0 \
  /opt/ntp-like/traffic_visualizer/network_control.py set \
  --subnet 10.151.0.0/24 --rate 15mbit
```

Replace `set --rate 15mbit` with `status` to inspect the queue or `clear` to
remove it. `tc` controls egress from the router's AS151-facing interface, which
is ingress traffic from the victim network's point of view. Attack responses
therefore compete with legitimate inbound requests for the limited bandwidth.

## Build

From the repository root:

```sh
python examples/yesterday_once_more/Y10_ntp_amplification/emulator.py --platform amd
```

The generated Docker files are placed in:

```text
examples/yesterday_once_more/Y10_ntp_amplification/output
```

## Manual Attack Trigger

After starting the emulator, run the trigger from the attacker container:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/ntp-like/trigger_attack.sh
```

For example, `--rounds 5 --interval 0.1` sends 15 reflection requests in total,
one every 0.1 seconds: five requests to each of the three default amplifiers.

The default victim is `10.151.0.71:9000`. The default amplifiers are:

```text
10.152.0.71
10.160.0.71
10.171.0.71
```

To run direct queries instead of reflection simulation:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/ntp-like/trigger_attack.py --json
```

To inspect victim-side traffic:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  tail -n 20 /var/log/ntp-like-victim.log
```

## Standard Test Runner

This example follows the `examples/sample` pattern:

```sh
python seedemu/testing/cli.py all examples/yesterday_once_more/Y10_ntp_amplification/example.yaml \
  --artifact-dir ci-artifacts/y10-ntp-amplification
```

The manifest checks that representative B00 services are running and that the
attacker can reach the victim and one amplifier. The custom runtime test checks:

- the attacker, victim, and amplifier containers exist;
- the NTP-like daemons are running;
- direct queries produce amplified responses;
- the reflection simulation causes the victim UDP sink to receive traffic;
- the victim service and router-side runtime link controller are installed;
- the legitimate client reports latency and goodput measurements.

## Safety

Run this only inside an isolated emulator. The daemon has an allowlist and the
reflection simulation is token-gated, but it is still intentionally modeling a
dangerous class of UDP amplification behavior.
