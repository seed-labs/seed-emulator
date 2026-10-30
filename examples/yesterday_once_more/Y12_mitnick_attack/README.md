# Y12: Mitnick Attack Support Tools

This folder starts with a lab-only TCP sequence oracle for demonstrating why
predictable TCP sequence numbers made old IP-based trust attacks possible.

Modern Linux TCP sequence numbers are randomized, so this helper gives the
attacker controlled visibility into selected TCP metadata on the target LAN.
It is intended only for isolated SEED Emulator labs.

## TCP Sequence Oracle

```text
tcp_sequence_oracle.py
```

Run it on a host in the target network:

```sh
sudo python3 tcp_sequence_oracle.py --iface net0 --port 9090
```

The container needs raw-packet privileges, such as `CAP_NET_RAW` or privileged
mode, because the script uses a Linux `AF_PACKET` raw socket.

The oracle records only TCP header metadata:

- source and destination IP;
- source and destination port;
- TCP sequence number;
- TCP acknowledgement number;
- TCP flags;
- window size;
- payload length.

It does not capture application payloads.

## Query Examples

Ask for a summary:

```sh
printf 'summary' | nc -u -w1 10.150.0.80 9090
```

Ask for recent packets involving a target:

```sh
printf 'query src=10.150.0.71 dport=514 limit=3' | nc -u -w1 10.150.0.80 9090
```

JSON queries are also supported:

```sh
printf '{"command":"query","dst":"10.150.0.71","dport":514,"limit":5}' | \
  nc -u -w1 10.150.0.80 9090
```

## Safety Boundaries

- Designed for isolated emulator networks.
- Defaults to recording only traffic with source or destination matching `10.`.
- Defaults to answering only clients matching `10.`.
- Records TCP metadata only, not packet payloads.
- Does not change kernel TCP sequence generation.

This helper is a bridge between historical attack mechanics and modern kernels:
students can observe or retrieve sequence-number information without weakening
the host kernel globally.
