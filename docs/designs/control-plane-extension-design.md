# SEED Control Plane Extension Design

这份文档说明本分支对 SEED routing control plane 的核心改造：FRR 作为 Router backend，ExaBGP 作为 control-plane speaker service，Looking Glass 作为 route-state observer service。目标是把新能力放在 SEED 已有抽象边界内，而不是把 demo 逻辑写进运行脚本。

## Design Position

- BIRD 和 FRR 是 `Router` 的 routing daemon backend。默认仍是 BIRD；FRR 通过 `createRouter(..., routingBackend="frr")` 选择。
- `Ebgp`、`Ibgp`、`Ospf` 只记录协议 intent：peer、relationship、route policy、OSPF active/passive interface。
- `Routing` 统一读取 intent，并根据 router backend 渲染 daemon-specific config：BIRD 写 `/etc/bird/bird.conf`，FRR 写 `/etc/frr/frr.conf`。
- ExaBGP 不是完整 transit router backend。它是通过 `ExaBgpService + Binding` 安装到 IX-facing 或 router-facing host 的 BGP speaker service。
- Looking Glass 是观察 service。Classic Looking Glass 读取当前 route-state；ExaBGP dashboard 读取 event stream。二者服务不同观察语义。

## Core File Map

| Concern | File / class | Role |
| --- | --- | --- |
| Router API | `seedemu/core/AutonomousSystem.py::createRouter` | Adds `routingBackend`, defaulting to `bird`. |
| Router state | `seedemu/core/Node.py::Router` | Stores backend through `setRoutingBackend()` and exposes labels/attributes for renderers and tools. |
| Intent metadata | `seedemu/layers/_bgp_metadata.py` | Stores BGP session intent, export policy, communities, connected export, and OSPF interface intent. It must stay backend-neutral and must not contain daemon templates. |
| Protocol intent | `seedemu/layers/Ebgp.py`, `Ibgp.py`, `Ospf.py` | Records routing relationships without choosing BIRD or FRR syntax. |
| Daemon templates | `seedemu/layers/routing_templates.py` | Stores BIRD and FRR daemon templates under `BirdFileTemplates` and `FrrFileTemplates`. |
| Daemon rendering | `seedemu/layers/Routing.py` | Renders BIRD/FRR backend configuration from the same intent model. |
| ExaBGP speaker | `seedemu/services/ExaBgpService.py` | Installs speaker host config, live control FIFO, event log, dashboard, and injects peer-router BGP intent. |
| Looking Glass | `seedemu/services/BgpLookingGlassService.py` | Installs route-state proxy/frontend and registers observed routers with `.addRouter(asn, name)`. |

## FRR Backend Flow

Example API:

```python
as2.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("ix101")
```

Flow:

```text
AutonomousSystem.createRouter(...)
-> Router.setRoutingBackend("frr")
-> Ebgp/Ibgp/Ospf record backend-neutral intent
-> _bgp_metadata stores session and OSPF metadata
-> Routing.render() selects backend
-> Routing._configure_frr_router()
-> /etc/frr/frr.conf + zebra/bgpd/ospfd
```

This keeps topology, protocol intent, and runtime daemon syntax separate. A mixed topology can use BIRD and FRR routers at the same time without changing the `Ebgp`, `Ibgp`, or `Ospf` APIs.

IX route servers currently remain BIRD-only. `Ebgp.addRsPeer()` records
route-server and participant-router BGP intent, and `Routing` renders the BIRD
route-server peer blocks from that intent. Selecting FRR for a route-server
node is explicitly rejected until FRR route-server behavior has a dedicated
design and runtime validation.

Runtime evidence for FRR examples should include:

- FRR routers have `/etc/frr/frr.conf`.
- FRR routers do not start BIRD.
- `vtysh` shows BGP summary, OSPF neighbors, and BGP routes.
- BIRD routers in the same topology still work with `birdc`.

## ExaBGP Service Flow

Example API:

```python
as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")

exabgp.install("as180_exabgp") \
    .setLocalAsn(180) \
    .addPeer("router0", router_asn=2, router_relationship="customer") \
    .addAnnouncement("198.51.100.0/24")

emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))
```

`addPeer()` creates a two-sided control-plane relationship:

```text
ExaBgpService.addPeer(...)
-> ExaBgpServer._resolve_peer()
   finds the shared IX/router-facing network
   resolves speaker address and peer-router address
-> ExaBgpServer._install_router_peer()
   calls install_router_bgp_session(router, ...)
   records eBGP intent on the peer router
-> ExaBgpServer.install()
   writes /etc/exabgp/exabgp.conf and live/event tooling on the speaker host
-> Routing.render()
   renders the peer-router intent into BIRD or FRR config
```

The service may add routing intent to its peer router, but it does not directly edit the peer router daemon config. Daemon-specific output still belongs to `Routing`.

Current scope:

- Supported: directly connected IX-facing or router-facing eBGP speaker.
- Supported: static announcements, live announce/withdraw, event logs, dashboard.
- Not claimed: arbitrary remote or multihop peer, iBGP transit, OSPF transit, full BIRD/FRR router replacement.

## Looking Glass Service Flow

Example API:

```python
looking_glass.install("bgp_lg") \
    .addRouter(2, "router0") \
    .setFrontendPort(5000) \
    .setProxyPort(8000)

emu.addBinding(Binding("bgp_lg", filter=Filter(asn=2, nodeName="looking-glass")))
```

Flow:

```text
BgpLookingGlassService
-> BgpLookingGlassServer.addRouter(asn, name)
-> install route-state proxy on the observed router
-> wait for BIRD socket or FRR/vtysh based on router backend
-> install frontend on the service host
-> expose route-state API/page
```

Looking Glass reads current route state. It should not be described as an ExaBGP event stream. ExaBGP dashboard and Classic Looking Glass are complementary evidence views:

- route-state: what the router currently selects and exports.
- event-stream: what the speaker announced, withdrew, or logged over time.

## Validation Matrix

| Example | Purpose | Required evidence |
| --- | --- | --- |
| `A12_bgp_mixed_backend` | BIRD/FRR mixed router backend | generated FRR config, no BIRD on FRR routers, `vtysh` BGP/OSPF/routes, `birdc` still works on BIRD routers |
| `A13_exabgp_control_plane` | IX-facing ExaBGP speaker service | speaker host config, native ExaBGP pipes, live FIFO, static route learned by peer, live announce/withdraw reflected in peer route table |
| `A14_bgp_event_looking_glass` | route-state vs event-stream observability | Classic LG route-state API/page, ExaBGP dashboard events, route table confirms announced/withdrawn prefixes |
| `B30_mini_internet_exabgp_ix` | ExaBGP service in a larger Internet topology | multiple peer routers learn static and live prefixes, dashboard logs events, withdraw removes routes |

## Design Boundaries

- Keep BIRD/FRR backend selection on `Router`.
- Keep protocol semantics in `Ebgp`, `Ibgp`, `Ospf`, and `_bgp_metadata`.
- Keep daemon-specific config generation in `Routing`.
- Keep ExaBGP as `Service + Binding`; do not present it as a full transit router backend.
- Keep route-state and event-stream views separate.
- Do not reintroduce legacy `FrrBgp` layer shims or ExaBGP router backends;
  `Router` backends are limited to `bird` and `frr`.
