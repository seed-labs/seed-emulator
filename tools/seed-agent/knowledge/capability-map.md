# SEED-Emulator Capability Map

A compact, evidence-backed inventory of **what SEED-Emulator can do today**. This is the single
source of truth for capability questions across all `seed-agent/` skills and agents — use it to
answer "is X supported?", "where is the example?", and "what are the limits?".

For the *design philosophy* behind these capabilities, see [`../PRINCIPLES.md`](../PRINCIPLES.md).
For the architecture, see [`architecture.md`](architecture.md).

Paths are relative to the repository root (the directory holding `seedemu/`, `examples/`,
`tools/`).

## How to use this file

- Read it as the first pass for any capability question; treat evidence paths as starting
  points, not exhaustive proof.
- If a claim matters and this file looks stale or ambiguous, inspect the repo directly.
- Keep it fresh: the [`seedemu-capability-refresh`](../skills/seedemu-capability-refresh/SKILL.md)
  skill describes how to re-derive this map from the repository. Update it when capabilities,
  examples, paths, limitations, or evidence change materially.
- Support status values: `existing`, `light top-layer development`, `substantial development`,
  `poor fit`.

## Capability Map

### Internet topology and routing emulation

- Category: `networking`
- Support: `existing`
- Summary: Build autonomous systems, Internet exchanges, routers, hosts, and BGP/IGP routing.
- Tags: internet, topology, autonomous system, ix, bgp, routing, ospf, ibgp
- Examples: `examples/basic/A00_simple_as`, `examples/basic/A01_transit_as`, `examples/internet/B00_mini_internet`
- Evidence:
  - `README.md`: Internet exchanges, autonomous systems, BGP routers, DNS infrastructure,
  - `docs/user_manual/overall_flow.md`: an Internet exchange will be automatically configured as BGP routers.
  - `docs/user_manual/bgp.md`: If we want to create a BGP router that can reach all the nodes on the Internet,
  - `seedemu/layers/Base.py`: @param create_rs (optional) create route server node for the IX or not.
- Limits: Internet scale is bounded by host resources and Docker networking limits.

### BGP security and routing incident replay

- Category: `security`
- Support: `existing`
- Summary: Replay routing incidents such as prefix hijacking and study routing policy behavior.
- Tags: bgp, prefix hijack, hijacking, route leak, routing attack, security
- Examples: `examples/yesterday_once_more/Y01_bgp_prefix_hijacking`
- Evidence:
  - `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/README.md`: 1. `demo` folder: a demonstration of the BGP prefix hijacking attack.
  - `seedemu/components/BgpAttackerComponent.py`: router.addTablePipe('t_hijack', 't_bgp', exportFilter = 'filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }')
  - `tools/DemoSystem/yesterday_once_more/01_bgp_prefix_hijacking/README.md`: The topology of our network is shown in `topology.txt` (it is only for reference purpose, the file is not used in the emulator code).
- Limits: Real interdomain policy data must be imported or approximated by scenario code.

### DNS, DNSSEC, and PKI infrastructure

- Category: `infrastructure`
- Support: `existing`
- Summary: Deploy DNS hierarchy, caching resolvers, reverse DNS, CA servers, and HTTPS certificates.
- Tags: dns, dnssec, resolver, pki, certificate, ca, https, acme
- Examples: `examples/internet/B01_dns_component`, `examples/internet/B02_mini_internet_with_dns`, `examples/internet/B25_pki`
- Evidence:
  - `docs/user_manual/internet/README.md`: - [Public Key Infrastructure (PKI)](./ca.md): Set up a PKI inside the emulator.
  - `docs/user_manual/internet/ca.md`: The `RootCAStore` class is a store containing the root CA certificate and its private key. It is used by the `CAService` to set up the PKI infrastructure and install the root CA certificate on nodes.
  - `examples/internet/B01_dns_component/README.md`: This example demonstrates how we can build a DNS infrastructure as a component.
  - `examples/internet/B02_mini_internet_with_dns/README.md`: This allows anyone to update the DNS records on this server. We have provided an example `add_record.sh` in the current folder to demonstrate how to add a record to the `example.net` server. Run the following:
- Limits: Certificate transparency and public CA ecosystem behavior need extra modeling.

### Traffic generation and network measurement

- Category: `measurement`
- Support: `existing`
- Summary: Generate TCP/UDP/custom traffic with iperf3, D-ITG, and Scapy and collect logs.
- Tags: traffic, measurement, iperf, ditg, scapy, throughput, latency, ddos
- Examples: `examples/internet/B28_traffic_generator`
- Evidence:
  - `docs/developer_manual/11-traffic-service.md`: `TrafficServiceType` is an enumeration of the different types of traffic services that can be used in the Emulator. If a new traffic service is added, this enumeration should be updated to include the new traffic service type.
  - `examples/internet/B28_traffic_generator/README.md`: For iPerf3 Traffic Generator, the logs are in `/root/iperf3_generator.log` file. For D-ITG Traffic Generator, the logs are in `/root/ditg_generator.log` file. The contents of the log files are shown below.
  - `seedemu/services/TrafficService/traffic_service.py`: if server_type in [TrafficServiceType.IPERF_RECEIVER, TrafficServiceType.DITG_RECEIVER]:
- Limits: High-rate traffic fidelity depends on local host CPU, kernel, and Docker limits.

### Closed-lab malware and botnet experiment replay

- Category: `security`
- Support: `existing`
- Summary: Create controlled botnet, worm, DDoS, and malware spread scenarios inside an emulator.
- Tags: botnet, malware, worm, mirai, morris, ddos, c2, attack
- Examples: `examples/internet/B22_botnet`, `examples/yesterday_once_more/Y02_morris_worm`, `examples/yesterday_once_more/Y03_mirai`
- Evidence:
  - `docs/designs/botnet.md`: This demonstration shows how can we build a botnet service in a pretty complex network. All the code can be found on [09-botnet-in-as](https://github.com/seed-labs/SEEDEmulator/tree/feature-merge/examples/09-botnet-in-as) example.
  - `examples/internet/B22_botnet/README.md`: We have modified the code (`botnet-base.py`) since the video was recorded,
  - `examples/yesterday_once_more/README.md`: We recreate some of the notorious Internet attacks and incidents:
  - `examples/yesterday_once_more/Y03_mirai/README.md`: We have provided demos for this attack in the following folders using different displaying methods:
- Limits: Only closed emulation outputs are in scope; real-world attack execution is out of scope.

### Privacy and overlay network services

- Category: `overlay`
- Support: `existing`
- Summary: Run Tor, IPFS/Kubo, CDN, email, and other application-layer services on emulated networks.
- Tags: tor, darknet, privacy, ipfs, kubo, cdn, email, overlay, content delivery
- Examples: `examples/internet/B23_darknet_tor`, `examples/internet/B26_ipfs_kubo`, `examples/internet/B30_CDN`, `examples/internet/B29_email_dns`
- Evidence:
  - `examples/internet/B23_darknet_tor/README.md`: When we design labs based on darknet, we need to find ways to show students that Tor is
  - `docs/user_manual/internet/kubo.md`: If you have a large number of nodes that you would like to install Kubo on, you may want to do this more dynamically. This can be done with iteration, and is used in the [Kubo example](../../examples/internet/B26_ipfs_kubo/README.md).
  - `examples/internet/B26_ipfs_kubo/README.md`: This is designed to be a very simple example depicting how to install IPFS Kubo on many nodes.
  - `examples/internet/B30_CDN/README.md`: - CDN explicitly writes policy-specific include content through `setIncludeContent(...)`
- Limits: Protocol-specific fidelity depends on service implementation depth.

### Blockchain and oracle-network emulation

- Category: `blockchain`
- Support: `existing`
- Summary: Emulate Ethereum PoA/PoW/PoS, smart contracts, faucets, Chainlink, Monero, and explorers.
- Tags: blockchain, ethereum, pos, pow, poa, smart contract, chainlink, oracle, monero, validator
- Examples: `examples/blockchain/D00_ethereum_poa`, `examples/blockchain/D01_ethereum_pos`, `examples/blockchain/D31_chainlink`, `examples/blockchain/D60_monero`
- Evidence:
  - `docs/user_manual/blockchain/README.md`: - [Build a blockchain emulator (POA)](../../../examples/blockchain/D00_ethereum_poa)
  - `examples/blockchain/D00_ethereum_poa/README.md`: blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)
  - `examples/blockchain/D01_ethereum_pos/README.md`: supported consensus option: ConsensusMechanism.POA, ConsensusMechanism.POW, ConsensusMechanism.POS
  - `examples/blockchain/D31_chainlink/README.md`: Chainlink is a decentralized oracle network designed to securely connect smart
- Limits: Public-chain economics and large peer populations require parameterized approximations.

### SCION Internet architecture emulation

- Category: `future-internet`
- Support: `existing`
- Summary: Build SCION ISDs, ASes, SCION/BGP coexistence scenarios, and bandwidth tests.
- Tags: scion, future internet, isd, path aware, bandwidth test, bgp coexistence
- Examples: `examples/scion/S01_scion`, `examples/scion/S02_scion_bgp_mixed`, `examples/scion/S03_bandwidth_tester`
- Evidence:
  - `examples/scion/README.md`: This directory contains examples of using the SCION Internet architecture within the SEED-Emulator.
  - `examples/scion/S01_scion/README.md`: For non-core ASes must additionally specify which core AS is signing the non-core AS's certificates with a call to `scion_isd.setCertIssuer()`.
  - `examples/scion/S02_scion_bgp_mixed/README.md`: scion_isd.setCertIssuer((1, asn), issuer=150)
  - `examples/scion/S03_bandwidth_tester/README.md`: The SCION bandwidth tester is available as the service `ScionBwtestService` which has to be included and instantiated.
- Limits: SCION feature coverage follows the local SCION service implementation.

### Docker, distributed, cloud, and hybrid deployment

- Category: `deployment`
- Support: `existing`
- Summary: Compile emulations to Docker, distributed Docker, GCP Terraform, graph outputs, and hybrid access setups.
- Tags: docker, distributed, gcp, terraform, hybrid, real world, vpn, openvpn, graphviz
- Examples: `examples/basic/A03_real_world`, `examples/internet/B50_bring_your_own_internet`
- Evidence:
  - `docs/user_manual/compiler.md`: GCP (Google Cloud Platform) Distributed Docker (`GcpDistributedDocker`) compiler
  - `docs/user_manual/internet/README.md`: - [Hybrid Emulation 1: including physical devices](../../../examples/internet/B50_bring_your_own_internet/)
  - `examples/basic/A03_real_world/README.md`: - Start a VPN server, listen for incoming connections on the for-service bridge network, so the emulator host can port-forward to the VPN server and allow hosts in the real world to connect.
  - `examples/internet/B50_bring_your_own_internet/README.md`: [2. Distributed Emulators(switch verstion)](#distributed-emulation-switch-version)
- Limits: Distributed deployments need external Docker Swarm, cloud, or network setup.

### Visualization and observability

- Category: `observability`
- Support: `existing`
- Summary: Visualize network topology, service nodes, traffic, and graphable layer outputs.
- Tags: visualization, internet map, map, graph, graphviz, observability, dashboard
- Examples: `examples/basic/A04_visualization`, `examples/internet/B06_internet_map`
- Evidence:
  - `docs/user_manual/visualization.md`: the following flag. The Internet map host will then be added to
  - `docs/user_manual/internet_map.md`: User Manual: The Internet Map Visualization App
  - `docs/user_manual/compiler.md`: a `toGraphviz` method, to convert the graph into graphviz dot file.
  - `tools/InternetMap2/README.md`: The Internet Map runs inside an independent container. We can use the `docker-compose.yml` file inside this folder to bring up the container.
- Limits: Experiment-specific metrics may require custom log parsers or dashboards.

---

For paper-reproduction matching heuristics and the paper-fit guide that build on this map, see
[`../agents/paper-researcher/paper-fit-guide.md`](../agents/paper-researcher/paper-fit-guide.md).
