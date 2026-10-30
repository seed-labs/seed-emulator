# Y05: SQL Slammer Worm Simulator

This example recreates the propagation idea behind the SQL Slammer worm in a
safe SEED Emulator lab. It does not implement the real SQL Server overflow or
native worm code.

SQL Slammer was interesting because the worm copy fit inside one UDP packet.
An infected host sent the packet to UDP port `1434`; if the target was
vulnerable, the target immediately began sending the same kind of packet to
other hosts. There was no TCP handshake, no file transfer, and no second-stage
download.

## What This Lab Models

Y05 models the propagation mechanism:

```text
infected host
  -> sends one UDP lab replica packet to port 1434
  -> vulnerable service accepts the known lab packet
  -> target marks itself infected
  -> target starts its local bounded worm simulator
  -> new host sends the same lab packet to more targets
```

The UDP packet contains a benign replica descriptor:

```text
SQL_SLAMMER_LAB_REPLICA
```

The descriptor is saved on infected hosts at:

```text
/tmp/slammer_lab_last_replica_packet.json
```

This lets students inspect the idea that the packet itself carries the next
generation. The service does not execute arbitrary packet contents; it only
accepts the known lab packet format and starts the preinstalled simulator.

## Build

```sh
python examples/yesterday_once_more/Y05_sql_slammer/slammer_emulator.py \
  --platform amd \
  --hosts-per-as 4
```

Useful options:

```sh
--packet-rate 80
--duration 20
--patched-asns 160,170
```

`--patched-asns` makes selected ASes run a patched service that records packets
but does not become infected.

## Start The Monitor

Run this on the Docker host:

```sh
python examples/yesterday_once_more/Y05_sql_slammer/monitor_attack.py
```

The monitor prints infected hosts, generations, duplicate packets, and packet
counts from local worm logs.

## Trigger The First Infection

From AS150 `host_0`, seed one infection:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/slammer-lab/trigger_initial_infection.py 10.151.0.71
```

Then inspect the packet saved on an infected host:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  cat /tmp/slammer_lab_last_replica_packet.json
```

## Comparison With Morris Worm

Morris-style propagation is multi-stage: a compromised host obtains or
reconstructs the worm program and then runs it.

Slammer-style propagation is single-packet: the network packet itself carries
the next generation. That compactness is why SQL Slammer is a useful companion
to Morris Worm in this incident collection.

## Safety Boundaries

- No real SQL Server exploit.
- No native shellcode.
- No public Internet scanning.
- The worm reads only `/opt/slammer-lab/targets.txt`.
- Targets are restricted to lab prefixes such as `10.`.
- Packet rate and duration are bounded by command-line options.
