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

Default role settings in [rost_env.py](/home/seed/seed-emulator/examples/internet/BXX_rost_env/rost_env.py):

- Repository AS: `154`
- Suppressor ASes: `3`
- Suppressor target prefixes: `10.154.0.0/24`
- Current patched suppressor router: AS3 anchor router `r100`

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
cd examples/internet/BXX_rost_env
python3 rost_env.py
cd output
docker compose up -d
```

If your environment uses the legacy compose command, use `docker-compose up -d`
instead.

To stop the environment:

```bash
cd examples/internet/BXX_rost_env/output
docker compose down
```

## Quick Walkthrough

The commands below follow the current code and the tested demo flow directly.
They use one adopting AS agent container and one suppressor router.

### 1. Find An Adopting Agent Container

After the environment is up:

```bash
cd examples/internet/BXX_rost_env/output
docker ps --format '{{.Names}}' | grep rost-agent
```

For a simple walkthrough, use the AS150 agent if it is present. With the
current deterministic role selection, AS150 is an adopting AS.

Open a shell in the agent container:

```bash
docker exec -it as150h-rost-agent-10.150.0.72 bash
```

### 2. Discover The Router Helper IP

Inside the adopting agent container:

```bash
ip route show default
```

Use the default gateway as `<router-ip>`. That is the router-helper IP for this
host.

### 3. Check The Helper

Inside the adopting agent container:

```bash
curl -s http://<router-ip>:18081/healthz
curl -s http://<router-ip>:18081/rost/state | python3 -m json.tool
curl -s http://<router-ip>:18081/bird/protocols | python3 -m json.tool
curl -s http://<router-ip>:18081/bird/route
```

Expected:

- `/healthz` returns `{"status": "ok"}`
- `/rost/state` returns JSON policy state
- `/bird/protocols` returns BIRD protocol output wrapped in JSON
- `/bird/route` returns current route output wrapped in JSON

### 4. Drive Policy Through The Agent

Still inside the adopting agent container:

```bash
python3 /root/agent.py --router-ip <router-ip> --enable
python3 /root/agent.py --router-ip <router-ip> --allow 10.154.0.0/24
python3 /root/agent.py --router-ip <router-ip> --routeid 10.154.0.0/24
python3 /root/agent.py --router-ip <router-ip> --invalidate 10.154.0.0/24
python3 /root/agent.py --router-ip <router-ip> --clear-invalid 10.154.0.0/24
python3 /root/agent.py --router-ip <router-ip> --state
```

These commands exercise the existing helper-backed control path exactly as
implemented.

### 5. Inspect Router State

Open a shell on the corresponding router, for example:

```bash
docker exec -it as150r-router0 bash
```

Then inspect the generated policy and BIRD state:

```bash
cat /etc/bird/rost_policy.conf
birdc show protocols
birdc show route
birdc show route 10.154.0.0/24
birdc show route 10.154.0.0/24 all
```

Expected:

- `rost_policy.conf` reflects the helper-managed policy state
- `birdc show protocols` shows the normal router sessions
- route visibility changes follow the helper policy state
- import/export policy mutations trigger automatic router reconvergence via the
  helper

## Demo / Walkthrough

This is a concise demo flow that can be followed directly.

### Demo Script

1. Build and start the environment.
2. Enter an adopting agent container, preferably `as150h-rost-agent-10.150.0.72`.
3. Run `ip route show default` and record the default gateway as `<router-ip>`.
4. Verify helper reachability with:
   `curl -s http://<router-ip>:18081/healthz`
5. Inspect current helper and route state with:
   `curl -s http://<router-ip>:18081/rost/state | python3 -m json.tool`
   `curl -s http://<router-ip>:18081/bird/protocols | python3 -m json.tool`
   `curl -s http://<router-ip>:18081/bird/route`
6. Enable RoST behavior on the adopting router:
   `python3 /root/agent.py --router-ip <router-ip> --enable`
7. Allow the repository prefix:
   `python3 /root/agent.py --router-ip <router-ip> --allow 10.154.0.0/24`
8. Attach the RouteID-style marker:
   `python3 /root/agent.py --router-ip <router-ip> --routeid 10.154.0.0/24`
9. Invalidate that prefix on import:
   `python3 /root/agent.py --router-ip <router-ip> --invalidate 10.154.0.0/24`
10. Inspect the router with `birdc show route 10.154.0.0/24`.
11. Clear invalid state:
    `python3 /root/agent.py --router-ip <router-ip> --clear-invalid 10.154.0.0/24`
12. Re-check state with:
    `python3 /root/agent.py --router-ip <router-ip> --state`
13. Verify the static suppressor on `as3r-r100`.

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

### Import Invalidation Note

Import invalidation changes the selected route view, and the helper now
automatically triggers BGP protocol refresh for the affected policy mutations.

In the tested demo, the route-table effect could also be made visible manually
with:

```bash
birdc disable u_as2
birdc enable u_as2
sleep 3
birdc show route 10.154.0.0/24
```

This manual step is usually no longer required for the supported helper
mutations, but it remains useful if you want to force another re-import or make
the effect easier to observe. The exact session name depends on the router. On
`as150r-router0`, the upstream session name is `u_as2`.

### Suppressor Verification

The default suppressor is AS3, and the patched suppressor anchor router is
`as3r-r100`.

Open a shell on that router:

```bash
docker exec -it as3r-r100 bash
```

Then run:

```bash
grep -n "rost_static_suppressor_match" /etc/bird/bird.conf
grep -n "10.154.0.0/24" /etc/bird/bird.conf
birdc show route 10.154.0.0/24
```

Expected:

- the suppressor function is present in `bird.conf`
- the selected target prefix appears in the suppressor policy
- the suppressor still learns the route locally

The suppressor behavior here is export withholding, not local route removal.
The route can still exist locally on the suppressor while being statically
rejected for export to external neighbors on the patched edge.

## Key Files

- [rost_env.py](/home/seed/seed-emulator/examples/internet/BXX_rost_env/rost_env.py)
  - builds the topology
  - assigns roles
  - deploys repository, agent, and helper files
  - patches adopting and suppressor router BIRD config

- [agent.py](/home/seed/seed-emulator/examples/internet/BXX_rost_env/agent.py)
  - capability check client
  - helper control client

- [router_helper.py](/home/seed/seed-emulator/examples/internet/BXX_rost_env/router_helper.py)
  - helper HTTP server
  - policy-state manager
  - `birdc` integration

- [repo_server.py](/home/seed/seed-emulator/examples/internet/BXX_rost_env/repo_server.py)
  - minimal repository HTTP service

## Notes And Limitations

- This is a RoST-style environment prototype, not a full RoST implementation.
- The repository is intentionally minimal.
- Suppressor behavior is static and configured at render time only.
- Suppressor ASes do not have runtime control via helper or agent.
- The example does not modify the SEED BGP implementation.
- The example does not implement protocol-level withdraw handling.
- The suppressor patch is intentionally narrow and currently targets only the
  suppressor anchor router selected by the existing helper function.
