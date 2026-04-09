# RoST-Style Environment

This example is a RoST-style SEED environment prototype. It does not implement
the full RoST algorithm or cryptographic protocol. Its purpose is to show that
SEED can represent the environment structure and control mechanisms needed for
RoST-style experiments:

- a repository reachable over HTTP
- a host-side agent in adopting ASes
- a router-local helper that rewrites dynamic BIRD policy and runs `birdc configure`
- static suppressor-AS behavior injected at render time for selected prefixes

The example keeps the normal SEED workflow. `bird.conf` is rendered by SEED and
then patched in `rost_env.py`. Adopting ASes get dynamic policy through
`/etc/bird/rost_policy.conf`. Suppressor ASes do not run an agent or helper and
use only static render-time export withholding.

Primary reviewer-facing validation is documented in
[VALIDATION.md](./VALIDATION.md).
That guide focuses on BIRD behavior, neighbor/downstream observation, and real
reachability effects, including the default suppressor behavior and the
separate controlled experiment for downstream loss. The
implementation-oriented checks in this README are secondary debugging/detail
checks.

## What This Example Demonstrates

- A repository / agent / router-helper / BIRD split inside a SEED Internet example.
- Dynamic policy control for adopting ASes without rewriting `bird.conf` at runtime.
- A static suppressor routing role that withholds selected prefixes on export.
- Prefix-specific experiments using simple BIRD policy changes instead of protocol changes.

This example demonstrates the environment and control path. It does not claim
to implement full RoST validation, protocol signaling, or protocol-level
withdraw handling.

## Topology And Roles

The example builds a small multi-AS Internet with transit-like and stub ASes.

Default role settings in [rost_env.py](./rost_env.py):

- Repository AS: `154`
- Repository validation target: `10.154.0.0/24`
- Dynamic policy demo target: `10.153.0.0/24`
- Suppressor ASes: `3`
- Suppressor target prefixes: `10.155.0.0/24`
- Current patched suppressor router: AS3 anchor router `r100`

The example uses three distinct reviewer-facing targets: the repository prefix
`10.154.0.0/24` for repository reachability, the ordinary prefix
`10.153.0.0/24` for helper-driven dynamic policy exercises, and the suppressor
target `10.155.0.0/24` for static export-withholding checks.

Adopting ASes are selected deterministically from the configured seed and
adoption rate. With the current defaults, the adopting ASes are:

- `2`
- `4`
- `150`
- `152`
- `153`

In this example:

- adopting ASes have a host-side `rost-agent` and a router-local `router_helper.py`
- suppressor ASes have no agent and no helper runtime control
- the repository AS runs a minimal HTTP service on a normal host

## Components

### Repository

Implemented in `repo_server.py`.

- Runs on host `rost-repo`
- Default port: `18080`
- Endpoints:
  - `GET /healthz`
  - `POST /`

The repository is intentionally minimal. It is only used to demonstrate that
the agent can reach an external service in the emulated network.

### Agent

Implemented in `agent.py`.

- Runs on host `rost-agent` inside each adopting AS
- Talks to the repository over HTTP
- Talks to the router helper over HTTP
- Supports both capability checks and direct control commands

Control commands already implemented in the agent:

- `--enable`
- `--disable`
- `--allow PREFIX`
- `--disallow PREFIX`
- `--suppress PREFIX`
- `--unsuppress PREFIX`
- `--routeid PREFIX`
- `--unrouteid PREFIX`
- `--invalidate PREFIX`
- `--clear-invalid PREFIX`
- `--state`

### Router Helper

Implemented in `router_helper.py`.

- Runs inside each adopting anchor router
- Default port: `18081`
- Rewrites `/etc/bird/rost_policy.conf`
- Stores JSON state in `/etc/bird/rost_policy_state.json`
- Resets to an empty default policy state on startup unless started with `--preserve-state`
- Runs `birdc configure` after each policy change
- Automatically refreshes BGP protocols after import/export policy changes that
  affect routing decisions

Helper `GET` endpoints:

- `/healthz`
- `/rost/state`
- `/bird/protocols`
- `/bird/route`

Helper `POST` endpoints:

- `/rost/enable`
- `/rost/disable`
- `/rost/allow`
- `/rost/disallow`
- `/rost/suppress`
- `/rost/unsuppress`
- `/rost/routeid`
- `/rost/unrouteid`
- `/rost/invalidate`
- `/rost/clear-invalid`
- `/bird/configure`

### BIRD Policy Split

The policy split is the core of the example:

- `/etc/bird/bird.conf`
  - rendered by SEED
  - patched once by `rost_env.py`
  - remains static at runtime

- `/etc/bird/rost_policy.conf`
  - used only on adopting AS anchor routers
  - rewritten by `router_helper.py`
  - loaded by BIRD through an `include`

This keeps adopting-AS control policy-based and helper-driven without changing
the SEED BGP implementation itself.

## How It Works

### Adopting ASes

For adopting anchor routers, `rost_env.py` patches the rendered eBGP policy and
adds an include for `/etc/bird/rost_policy.conf`. The helper then changes only
the policy file and asks BIRD to reload it with `birdc configure`.

For policy mutations that change import/export decisions (`allow`, `disallow`,
`suppress`, `unsuppress`, `invalidate`, `clear-invalid`), the helper then
automatically refreshes BGP protocols by cycling the router's BGP sessions with
`birdc disable <protocol>` and `birdc enable <protocol>`.

The helper renders the following functions into `rost_policy.conf`:

- `rost_is_enabled()`
- `rost_export_is_allowed()`
- `rost_export_is_suppressed()`
- `rost_apply_export_attributes()`
- `rost_import_is_invalid()`

At a high level, export handling on adopting routers is:

```text
if !(original_seed_export_condition) then reject;
if !rost_is_enabled() then accept;
if !rost_export_is_allowed() then reject;
if rost_export_is_suppressed() then reject;
rost_apply_export_attributes();
accept;
```

Import handling adds a prefix-specific invalidation check before the original
SEED import logic.

### Suppressor ASes

Suppressor behavior is static and render-time only.

- configured by `SUPPRESSOR_ASES`
- controlled by `SUPPRESSOR_TARGET_PREFIXES`
- injected directly into the rendered `bird.conf`
- no agent
- no helper
- no runtime daemon

On the patched suppressor router, the export wrapper becomes:

```text
if !(original_seed_export_condition) then reject;
if net ~ [ suppressor target prefixes ] then reject;
accept;
```

This means the suppressor still learns the route locally, but refuses to export
the selected prefixes across the patched eBGP edge.

## Build And Run

From this example directory:

```bash
cd nsdi/rost
python3 rost_env.py amd
cd output
docker-compose up -d
```

Use `python3 rost_env.py arm` instead on ARM64 hosts.

To stop the environment:

```bash
cd nsdi/rost/output
docker-compose down
```

## Secondary Implementation / Debugging Checks

Use [VALIDATION.md](./VALIDATION.md)
for the primary reviewer-facing behavior checks. The sections below are mainly
for implementation review and debugging.

### Repository Check

From an adopting agent container, you can also exercise the repository and
helper capability check mode directly:

```bash
python3 /root/agent.py \
  --repo-host <repo-ip> \
  --repo-port 18080 \
  --router-host <router-ip> \
  --router-port 18081
```

This performs:

- repository health check
- repository `POST /`
- helper health check
- `birdc show protocols` via the helper
- `birdc show route` via the helper

Repository-specific checks should continue to use the repository service in
AS154. The primary validation guide intentionally uses the separate
ordinary prefix `10.153.0.0/24` instead of the repository prefix.

### Import Invalidation Note

Import invalidation changes the selected route view, and the helper now
automatically triggers BGP protocol refresh for the affected policy mutations.

In the tested demo, the route-table effect could also be made visible manually
with:

```bash
birdc disable u_as2
birdc enable u_as2
sleep 3
birdc show route 10.153.0.0/24
```

This manual step is usually no longer required for the supported helper
mutations, but it remains useful if you want to force another re-import or make
the effect easier to observe. The exact session name depends on the router. On
`as150r-router0`, the upstream session name is `u_as2`.

### Suppressor Verification

The default suppressor is AS3, and the patched suppressor anchor router is
`as3r-r100`.

Use [VALIDATION.md](./VALIDATION.md)
for the primary downstream/behavioral suppressor check. The commands here are
implementation/debugging checks on the suppressor router itself.

Open a shell on that router:

```bash
docker exec -it as3r-r100 bash
```

Then run:

```bash
grep -n "rost_static_suppressor_match" /etc/bird/bird.conf
grep -n "10.155.0.0/24" /etc/bird/bird.conf
birdc show route 10.155.0.0/24
birdc show route export p_rs100 10.155.0.0/24
```

Expected:

- the suppressor function is present in `bird.conf`
- the selected target prefix appears in the suppressor policy
- the suppressor still learns the route locally
- `birdc show route export p_rs100 10.155.0.0/24` shows that the route is withheld on that edge

The suppressor behavior here is export withholding, not local route removal.
The route can still exist locally on the suppressor while being statically
rejected for export to external neighbors on the patched edge.

## Key Files

- [rost_env.py](./rost_env.py)
  - builds the topology
  - assigns roles
  - deploys repository, agent, and helper files
  - patches adopting and suppressor router BIRD config

- [agent.py](./agent.py)
  - capability check client
  - helper control client

- [router_helper.py](./router_helper.py)
  - helper HTTP server
  - policy-state manager
  - `birdc` integration

- [repo_server.py](./repo_server.py)
  - minimal repository HTTP service

## Notes And Limitations

- This is a RoST-style environment prototype, not a full RoST implementation.
- The repository is intentionally minimal.
- Suppressor behavior is static and configured at render time only.
- Suppressor ASes do not have runtime control via helper or agent.
- The example does not modify the SEED BGP implementation.
- The example does not implement protocol-level withdraw handling.
- Adopting-router helper state is reset to an empty baseline on startup unless
  `router_helper.py` is launched manually with `--preserve-state`.
- The suppressor patch is intentionally narrow and currently targets only the
  suppressor anchor router selected by the existing helper function.
