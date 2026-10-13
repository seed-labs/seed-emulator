# OSPF and RIP Mini Internet

B51 copies B00's complete topology into a standalone `rip.py`: 6 Internet
exchanges, 5 transit ASes, 12 stub ASes and 27 routers. AS3, AS4 and AS12 run
OSPF; AS2, AS11 and the 12 stub ASes run RIP. This gives 9 OSPF routers and
18 RIP routers. The script adds RIP policy examples and does not import B00's builder.
It demonstrates software-independent protocol policy on BIRD, FRR and mixed
backends.

The architecture follows Sections 3 and 4 of the SEEDX paper:

1. `Base` defines topology; each AS declares its IGP with `setIgpMode()`.
2. `Ospf` and `Rip` derive intents according to the AS's choice.
3. `Routing` renders the composed intents into BIRD or FRR configuration.
4. `Ibgp` uses the configured IGP to resolve its loopback-based sessions.
5. The Docker compiler and testing runner own deployment and execution.

`Rip.configure()` never writes native daemon configuration. BIRD gets a
separate `t_rip` table, selected connected prefixes and a one-way pipe into
the forwarding table. FRR gets `ripd` and a prefix-filtered connected-route
redistribution policy. Neither backend redistributes BGP routes into RIP.
OSPF and RIP coexist on different ASes using `as2.setIgpMode("rip")`.
The example does not call mask functions. Competing IGP layers on the same
router are rejected. The current MPLS layer continues to
use its existing OSPF/LDP path.

```python
as2 = base.getAutonomousSystem(2)
as2.setIgpMode("rip").setIgpInterfacePolicy("router-links")
# The same policy also applies to AS3, whose IGP remains default OSPF.
base.getAutonomousSystem(3).setIgpInterfacePolicy("router-links")
# An unset AS defaults to OSPF; use setIgpMode("ospf") to select it explicitly.
ospf = Ospf()
rip = Rip().setTimers(update=5, timeout=30, garbage=20)
emu.addLayer(ospf)
emu.addLayer(rip)
```

The AS API exposes chainable `setIgpMode("ospf"|"rip")`, `getIgpMode()` and
`hasIgpMode()`. Values are case-insensitive; unsupported modes fail at the API
boundary. Unset ASes always select OSPF. A selected protocol
needs its layer installed; missing layers produce an explicit error. Neither
method writes BIRD/FRR configuration. The shared `setIgpInterfacePolicy()` controls interface classification for both
IGPs, independently of protocol selection.

Protocol layers use only `Ospf()` and `Rip()`: their `asns` constructor argument,
`setAsns()` and `getAsns()` have been removed. AS-level `setIgpMode()` is the
only protocol-selection API. Installing only `Rip()` leaves unset ASes at
OSPF and reports the missing Ospf layer. Pure RIP scenarios explicitly select
RIP on every AS. Dump/load and Base component merging preserve AS choices;
older AS components default to OSPF, and old layer scope fields are ignored.
iBGP resolves next hops with `t_ospf` or `t_rip` according to the AS's IGP.
The current MPLS/LDP implementation requires OSPF and rejects explicit RIP in
MPLS-enabled ASes.

`setIgpInterfacePolicy()` declares how interfaces become active or passive:

| Policy | Active routing interfaces | Passive interfaces |
| --- | --- | --- |
| `all-local` | Every AS-local network, including host-only networks | External links and loopback |
| `router-links` | AS-local networks joining at least two routers | Host-only/single-router networks, external links and loopback |

Passive interfaces retain prefix advertisement; they do not send routing
updates. RIP passive Local interfaces can still receive updates. External RIP
links and loopbacks never exchange RIP, regardless of policy or overrides.
Layer stubs, masks and RIP interface options retain their existing precedence.

Without an explicit interface policy, both OSPF and RIP use `all-local`.
Changing `setIgpMode()` preserves the effective interface policy, whether it
is the shared default or an explicitly selected value. To make host-facing
Local networks passive, explicitly select `router-links` or use a layer override.
The AS also exposes `getIgpInterfacePolicy()` and `hasIgpInterfacePolicy()`.
The old `setOspfMode("legacy"|"router-transit-only")` methods remain compatibility
adapters: `legacy` maps to `all-local`, and `router-transit-only` maps to
`router-links`. New ASes have only shared IGP policy state; old saved OSPF
fields are read as a migration fallback. OSPF timers/areas and RIP metrics/
versions remain protocol-specific.

The internal `_igp_metadata.py` module owns both protocols' default values,
timer validation and interface-intent storage. The separate `_rip_metadata.py`
module has been removed. iBGP calculates each router's lookup table once:
`t_ospf` for actual OSPF intent, `t_rip` for RIP, and `master4` for the existing
MPLS path or a router without an IGP intent. RR/full-mesh helpers require this
explicit mapping; they have no implicit `master4` parameter default.
Source changes are explained in
[rip1009.md](../../../rip1009.md).
RIP's BIRD configuration now uses four top-level `RoutingFileTemplates`
entries, matching OSPF's template organization. FRR selects one `igp_body`
from the router's actual OSPF/RIP identity before combining BGP and MPLS.

The 2026-10-09 source revision passed validation: 147 regressions, four
static CI checks, all three real backends, and an ordinary mixed down/up
restart. Each real run passed 4,386 interface ping directions. Earlier
validation sections below describe earlier source versions. Those runtime
results predate the unified `all-local` default; current changes and validation
are recorded in [codex_worklog.md](codex_worklog.md). The 2026-10-09 acceptance
is recorded in
[Section 19 of add_rip.md](../../../add_rip.md#19-2026-10-09as-唯一选择协议删除层范围与空-render).

## Select RIP in a B00 copy

Add `Rip` to B00's existing `seedemu.layers` import, explicitly select RIP on
its ASes, and replace the Ospf layer:

```python
for asn in base.getAsns():
    base.getAutonomousSystem(asn).setIgpMode("rip")
emu.addLayer(Rip())
```

The earlier automatic one-line replacement has been removed to keep the AS
default OSPF. B00's original source remains unchanged in the repository.
Its existing `example.yaml` and `test_runtime.py` can be reused.
The class and registered layer are both named `Rip`, following the `Ospf` naming style.

## Policy APIs

The precedence is **layer defaults < network options < router options <
interface options**. Setters are chainable and update partial declarations.
Getter results are copies. References to nonexistent ASes, routers or
interfaces fail during composition.

```python
from seedemu.layers import Rip

base.getAutonomousSystem(2).setIgpMode("rip")
base.getAutonomousSystem(150).setIgpMode("rip")
base.getAutonomousSystem(151).setIgpMode("rip")
rip = Rip().setTimers(update=5, timeout=30, garbage=20)
rip.setDefaults(metric=1, split_horizon=True, poison_reverse=True)
rip.setNetworkOptions(2, "net_100_101", metric=2)
rip.setRouterOptions(2, "r101", metric=3, advertise_loopback=True)
rip.setInterfaceOptions(2, "r101", "net_100_101", metric=4)
rip.setNetworkOptions(150, "net0", passive=True)
rip.markAsStub(151, "net0")
emu.addLayer(rip)
```

For example, `net_100_101` has receive metric 2 on `r100` and 4 on `r101`.
The other interfaces of `r101` inherit its router metric 3. RIP uses hop
metrics; it has no OSPF area or OSPF link-type concept.

All fields below are optional. `setDefaults()` sets layer defaults;
`setNetworkOptions(asn, netname, **options)` sets a shared network policy;
`setRouterOptions(asn, router, **options)` sets a router policy;
`setInterfaceOptions(asn, router, netname, **options)` specializes one interface.

| Field | Default | Meaning / supported scopes |
| --- | --- | --- |
| `update` | 30 | Periodic update interval, seconds; all scopes |
| `timeout` | 180 | Route expiration interval, seconds; all scopes |
| `garbage` | 120 | Retention after expiration, seconds; all scopes |
| `metric` | 1 | Receive-side hop increment, integer 1–15; all scopes |
| `version` | 2 | Send and receive RIP version 1 or 2; all scopes |
| `passive` | Topology-derived | Suppress outgoing updates; all scopes |
| `split_horizon` | `True` | Avoid announcing learned routes back on their incoming interface; all scopes |
| `poison_reverse` | `True` | Advertise those reverse routes as unreachable when split horizon is enabled; all scopes |
| `enabled` | `True` | Participation / advertisement; router scope disables that router |
| `advertise_loopback` | `True` | Include the router's `/32` loopback; defaults and router scope |

Timers must be integers in 1–65535 and `timeout > update`. BIRD supports
interface timer overrides. FRR has router-wide timers: all participating
interfaces of a router must resolve to the same timer tuple, otherwise
rendering reports an explicit capability error. FRR receive metrics use an
inbound offset that replaces its normal +1 increment. FRR also requires each
timer to be at least 5 seconds; smaller values are supported only by BIRD.
RIPv2 is the default
for the classless B00 address plan; RIPv1 retains its classful limitations.
RIP metric 16 means unreachable, so the layer rejects interface metrics above
15. RIP is suitable for small AS interiors rather than large-diameter ASes.

Internal networks with two or more routers exchange updates by default;
host-only links are passive. Passive RIP interfaces can still receive updates,
as in BIRD and FRR. Loopbacks and external IX/cross-connect interfaces only
contribute connected prefixes: they never exchange RIP messages, even if a
user requests `passive=False` there. This keeps routing exchanges inside each
AS while providing the prefixes needed for BGP next-hop resolution.

`maskNetwork(asn, netname)` excludes both RIP exchange and RIP advertisement;
`maskAsn(asn)` disables RIP in that AS. These explicit masks take precedence
over option overrides. `markAsStub(asn, netname)` forces passive operation.
`setInterfaceOptions(..., enabled=False)` excludes a single attachment. The
`dummy0` interface can be selected to customize loopback advertisement.
Layer-wide `enabled=False` can be overridden on selected networks or interfaces;
an explicitly disabled router remains excluded.
RIP masks do not change the independent BGP export policy.
Disabling RIP on a router keeps its other protocol declarations; iBGP falls
back to the forwarding table there and needs independently supplied next-hop
reachability if its peers are not directly reachable.

Introspection methods include `getDefaults()`, `getTimers()`,
`getNetworkOptions(asn, netname)`, `getRouterOptions(asn, router)`,
`getInterfaceOptions(asn, router, netname)`, `getStubs()`,
`getMaskedNetworks()`, `getMaskedAsns()`, `isMasked(asn, netname)` and
`getConfiguration()`. The default RIP merger preserves these declarations,
unions masks, and rejects conflicting scoped options or conflicting nondefault
layer defaults. A layer value equal to the class default yields to a nondefault
value from the other component.

Backend syntax and protocol semantics follow the official
[BIRD RIP guide](https://bird.nic.cz/doc/bird-2.19.0.html#rip) and
[FRR RIP guide](https://docs.frrouting.org/en/stable-8.4/ripd.html), with exact
FRR CLI syntax verified against
[FRR 8.4.4's command definitions](https://github.com/FRRouting/frr/blob/frr-8.4.4/ripd/rip_cli.c).

## Files and execution

| File | Role |
| --- | --- |
| `rip.py` | Standalone B00 topology with per-AS OSPF/RIP selection and RIP policy examples |
| `example.yaml` | User-editable lifecycle manifest; selects mixed backends and built-in ping probes |
| `test_runtime.py` | Read-only discovery, live OSPF/RIP/BGP checks and all-interface ordinary ping |
| `README.md` | Architecture, API and execution guide |
| `codex_worklog.md` | Implementation commands and validation evidence |
| `output/` | Generated Dockerfiles, node configuration and Compose deployment |

Script options: `--platform amd|arm` (default `amd`), `--output PATH`
(default `output/` beside the script), `--backend bird|frr|mixed` (default
`mixed`), `--hosts-per-as N` (default 2), `--dumpfile PATH` (optional,
unrendered component), `--override` (default), `--no-override` (optional, refuse
overwriting output), and B00's `--skip-render` option.

B51 now uses the same ordinary Docker address mode as B00:
`Docker(platform=platform)` with `selfManagedNetwork=False` by default.
Docker inspect, SEED metadata and container interfaces all use the real
emulated addresses. There is no transport pool or startup address replacement.
`seedemu/compiler/Docker.py` has been restored to the repository's HEAD.

This mode runs with host `net.bridge.bridge-nf-call-iptables=0`, which is
already persisted on this server at the user's request. Users do not need to
set it again for each experiment. The example does not change host sysctls or
add firewall exemptions; its lifecycle uses the same deployment as the
ordinary compile/build/up commands below.

For a network that remains running, use the ordinary user workflow from the
repository root:

```sh
python3 examples/internet/B51_rip/rip.py
docker compose -f examples/internet/B51_rip/output/docker-compose.yml build
docker compose -f examples/internet/B51_rip/output/docker-compose.yml up -d
```

After routing protocols converge, an ordinary `ping 10.2.0.254` inside
`as163brd-router0-10.163.0.254` uses a valid IX source and return path.

From the repository root, the lifecycle consumes `example.yaml`, compiles
`rip.py` into `output/`, builds the images, starts the containers, verifies
readiness and reachability, then runs protocol/route checks:

```sh
python3 seedemu/testing/cli.py all examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
```

`all` tears down containers at the end, including on failure. For manual
inspection, run stages individually and call `down` when finished:

```sh
python3 seedemu/testing/cli.py compile examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
python3 seedemu/testing/cli.py build examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
python3 seedemu/testing/cli.py up examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
python3 seedemu/testing/cli.py probe examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
python3 seedemu/testing/cli.py test examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
python3 seedemu/testing/cli.py down examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
```

The mixed topology uses FRR in AS3, AS2/r101 and AS12/r104. Other AS routers
use BIRD; route servers retain BIRD. To compile homogeneous AS-router
backends instead, change `compile.args` to `[--backend, bird]` or
`[--backend, frr]`. Outputs include readiness/probe/test summaries,
`b51-runtime-test.json`, and command logs under the artifact directory.
The custom tests verify the declared IGP on every router, same-AS loopbacks
learned through that IGP, established BGP sessions and RIP receive metrics in
both directions. They also run ordinary pings from every host and AS router
to every other node's physical interface addresses. With default settings this
covers 4386 directions, including all 600 host-to-host directions. The previous
management network used to demonstrate masking has been removed.

The GitHub workflow includes B51 in both compilation and runtime matrices,
and runs RIP / existing routing regression tests in its static job.

## Reachability expectations

B51 marks IX peering LANs as direct networks using `setDirect(True)`.
The existing BGP connected-prefix export therefore advertises both AS-local
networks and IX LANs. Ordinary router pings can use their IX source addresses,
and container-name addresses remain reachable across ASes. No `ping -I` is
required for hosts and AS border routers after protocol convergence.

Loopbacks continue to provide AS-local IGP/iBGP reachability. Global loopback
announcement is a separate BGP policy. B51's Docker deployment and IX
announcement do not depend on the IGP backend.
Historical failures, temporary diagnostic controls and current user-workflow
validation are recorded in `codex_worklog.md` and
[the RIP change document](../../../add_rip.md).


## Earlier RIP-only user-workflow validation (2026-10-08)

Ordinary compile/build/up passed with host bridge netfilter kept at 1 and
without firewall exemptions or a bound ping source. All 25 hosts and 27 AS
border routers reached every other node's real interface addresses:
B00/OSPF 4386/4386, B00's one-line RIP replacement 4386/4386, and B51 mixed
4488/4488 (including management addresses). Each host-to-host matrix passed
600/600. The original B00 and B51 runtime checks passed 9/9 and 72/72.
Full results, protocol/FIB checks and source-preservation traces are in
`ci-artifacts/rip/user-workflow-20261007/acceptance-summary.json`.

## Earlier self-managed OSPF/RIP validation (2026-10-08)

All three backends completed real compilation, ordinary Docker Compose build
and up. Host `bridge-nf-call-iptables` stayed at 0 throughout. Validation added
no firewall exemptions or source-bound pings.

| AS-router backend | Runtime checks | Ordinary interface ping directions | Host-to-host directions |
| --- | --- | --- | --- |
| BIRD | 118/118 | 4386/4386 | 600/600 |
| FRR | 145/145 | 4386/4386 | 600/600 |
| mixed (default) | 124/124 | 4386/4386 | 600/600 |

Each deployment had 9 OSPF and 18 RIP routers. Every emulated node's real
addresses and transport gateway routes were correct. Native protocol, BGP
and learned-route checks passed; BIRD-only checks applied to the BIRD/mixed
cases. Ordinary down removed the previous, BIRD and FRR project networks
completely before the next up.

The default mixed deployment was left running from this example's `output/`:
59 running services and two successful build-only dummy services. Regression
tests passed 105/105; static CI passed manifest, whitespace, compileall and
import-smoke checks. Evidence is saved in
[acceptance-summary.json](../../../ci-artifacts/rip/ospf-rip-coexist-20261008/acceptance-summary.json)
and the adjacent command logs, unit/static results and `final-services.json`.
The file-by-file explanation is in
[Section 14 of add_rip.md](../../../add_rip.md#14-2026-10-08b51-同时演示-ospf-和-rip).

## Earlier ordinary Docker validation (2026-10-08)

After restoring Docker.py to HEAD and disabling self-managed networking in B51,
all three backends passed actual compile/build/up with host bridge netfilter
kept at its persisted value of 0. The default mixed network also passed a
normal down/up cycle and the complete checks again:

| Scenario | Runtime checks | Ordinary interface ping directions | Host-to-host directions |
| --- | --- | --- | --- |
| BIRD | 118/118 | 4386/4386 | 600/600 |
| FRR | 145/145 | 4386/4386 | 600/600 |
| mixed | 124/124 | 4386/4386 | 600/600 |
| mixed after down/up | 124/124 | 4386/4386 | 600/600 |

Every real interface address matched both Docker inspect and SEED metadata
on all 58 emulated nodes. Normal down left no project networks, and each
subsequent up succeeded. Protocol/route and applicable BIRD FIB checks passed.
No host settings, firewall exemptions or bound ping sources were introduced.
Regression tests passed 105/105 and static CI passed all four stages.

The ordinary mixed deployment was left running in the default `output/`, with
59 running services and two successful build-only dummy services. The server
continues to use bridge netfilter value 0; users can rerun the three ordinary
commands above without setting it again. Evidence for that run is in
[acceptance-summary.json](../../../ci-artifacts/rip/docker-revert-20261008/acceptance-summary.json)
and the file-by-file rollback explanation is in
[Section 15 of add_rip.md](../../../add_rip.md#15-2026-10-08按用户要求恢复-dockerpy-原版).

## Earlier AS IGP API validation (2026-10-08)

B51 now selects RIP through `as2.setIgpMode("rip")` and the equivalent calls
on AS11 and the stub ASes. AS3, AS4 and AS12 remain unset and run default
OSPF. Both layers are registered without AS scopes or masks. Regression tests
passed 128/128, including default selection, layer order, BIRD/FRR rendering,
serialization, component merging and legacy calls. Static CI passed all four
stages.

All three backends passed actual ordinary compile/build/up, followed by a
normal mixed down/up cycle and the full checks again:

| Scenario | Runtime checks | Ordinary interface ping directions | Host-to-host directions |
| --- | --- | --- | --- |
| BIRD | 118/118 | 4386/4386 | 600/600 |
| FRR | 145/145 | 4386/4386 | 600/600 |
| mixed | 124/124 | 4386/4386 | 600/600 |
| mixed after down/up | 124/124 | 4386/4386 | 600/600 |

All 58 nodes' real addresses matched Docker inspect and metadata. Protocol,
learned-route, BGP and applicable BIRD FIB checks passed. Normal down left no
project networks. Host bridge netfilter remained 0; validation used ordinary
pings without source binding or firewall exemptions.

The default mixed network is left running in `output/`: 59 running services
and two successful build-only dummy services. Docker.py remains exactly at
HEAD. Detailed evidence is in
[acceptance-summary.json](../../../ci-artifacts/rip/as-igp-mode-20261008/acceptance-summary.json),
with final service and documentation checks beside it. API rules and this
round's file-by-file changes are in
[Section 16 of add_rip.md](../../../add_rip.md#16-2026-10-08将-igp-选择移到-as-api).

## Final AS-only IGP validation (2026-10-09)

The final source passed 147 regressions and all four static CI checks. All
three backends compiled and built with ordinary Docker addressing, then
passed real deployments; mixed also passed an ordinary down/up restart.

| Deployment | Runtime checks | Ordinary interface ping directions | Host pairs (included) |
| --- | --- | --- | --- |
| bird | 118/118 | 4386/4386 | 600/600 |
| frr | 145/145 | 4386/4386 | 600/600 |
| mixed | 124/124 | 4386/4386 | 600/600 |
| mixed-restart | 124/124 | 4386/4386 | 600/600 |

Each run checked all 25 hosts and 27 routers against the other nodes' actual
interface addresses, plus protocol state and applicable BIRD RIB/FIB checks.
AS163 router0 reached all 84 other interface addresses in every run. AS2's
four routers also passed every target. OSPF remained active on 9 routers and
RIP on 18, with all 58 nodes' actual/Docker/metadata addresses consistent.

The default mixed deployment remains running (59 running services; two
build helpers exited successfully). `Docker.py` and B00 are unchanged from
HEAD, `selfManagedNetwork` is off, and the server's bridge value stays 0.
No firewall exemptions, injected static routes, or bound-source ping were
used. Source hashes were unchanged during the tests. This validation covers
the current amd platform and default topology; it is not a performance run.

See the [final report](../../../ci-artifacts/rip/as-only-igp-20261009/validation-report.md)
and [full change record](../../../add_rip.md#19-2026-10-09as-唯一选择协议删除层范围与空-render).
Both requested documents now live in the repository root, as confirmed by
the user; their source links and all README references have been updated.
