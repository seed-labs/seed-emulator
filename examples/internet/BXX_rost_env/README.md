# RoST-Style Environment

This example is a first draft of a RoST-style SEED environment. It is meant to
provide a clean Internet emulation skeleton that can later host RoST-related
components, but it is not a full implementation of the RoST algorithm.

The scenario keeps the standard SEED example structure: it builds a small demo
Internet, assigns experiment roles, deploys component hosts, and compiles the
result into Docker artifacts.

The environment is intended to include:

- normal ASes
- adopting ASes that will later run agent software
- one repository AS that will later host the repository service
- one suppressor AS that represents a routing-policy role in the network

In this model:

- the agent is a software component that runs on hosts in adopting ASes
- the repository is a software component that runs on a host in the repository AS
- the suppressor is not an application component; it is expressed through
  routing and BGP policy behavior in a central AS

The main functions in `rost_env.py` are:

- `build_base_topology()`: creates a small connected demo Internet of about 10
  ASes, including several transit-like ASes and several edge/stub-like ASes.
- `assign_rost_roles()`: assigns repo, suppressor, and adopting AS roles
  independently from topology construction.
- `deploy_rost_components()`: adds RoST component hosts. Adopting ASes still
  receive `rost-agent` hosts prepared with a manual `agent.py` script, while
  the repository AS receives a `rost-repo` host that runs a minimal mock
  `repo_server.py` service. Each adopting AS also installs a minimal
  `router_helper.py` onto its anchor router so the external agent can query
  router state over HTTP instead of running `birdc` locally. Phase 1 keeps this
  topology-neutral by reusing an existing AS-local network that is already
  attached to the anchor router, rather than creating a new router-facing
  network.
- `apply_special_policies()`: reserved hook for future suppressor-specific
  BGP and routing-policy logic. In the current code, this function installs a
  suppressor-specific SEED hook that targets the `Ebgp` layer and marks the
  suppressor routers as the future injection point for BIRD/BGP policy changes.
- `main()`: runs the full build flow and compiles the emulation in the normal
  SEED style.

This draft is intentionally conservative. It aims to be a realistic SEED
scenario skeleton that can be extended later with actual agent code, richer
repository behavior, and special routing policies.

## Architecture (Phase 1)

Phase 1 models the RoST component split conservatively:

- the agent runs on a normal host container and remains external to the router
- the router continues to run BIRD inside the router container
- a small `router_helper.py` service runs inside the router container
- the agent communicates with the router through `router_helper.py` over HTTP
- `router_helper.py` wraps `birdc` and exposes only a small read-only API
- the agent also communicates with the repository over HTTP

In other words, the agent does not execute `birdc` locally. Router-local BIRD
state is accessed through the helper, which is closer to the RoST paper's
"external agent talking to router via CLI/API" model.

### Phase 1 Diagram

```text
+------------+      HTTP       +-----------+      HTTP       +-----------------+      local CLI      +------+
| Repository | <-------------> |   Agent   | <-------------> |  Router Helper  | <-----------------> | BIRD |
| repo_host  |                 | rost-agent|                 | router container |                     | birdc|
+------------+                 +-----------+                 +-----------------+                     +------+
```

## Repository Service

The repository host now runs an intentionally minimal mock HTTP service on port
`18080`, avoiding SEED-reserved tooling ports such as `8080`. The service is
implemented in `repo_server.py` and is copied onto the `rost-repo` host during
emulation rendering.

The repository is only a mock receiver/responder. It remains reachable over the
network so future agent code can contact it, but it does not implement real
repository logic yet.

Available endpoints:

- `POST /`: accepts a simple message body and returns `{"status": "received"}`
- `/healthz`: returns a minimal health response

## Agent Script

Adopting ASes now receive a one-shot `agent.py` script on their `rost-agent`
host. This script is only a capability demonstration:

- it does not run as a daemon
- it does not perform RoST validation or decision logic
- it does not control routers yet

When run manually, the agent:

- prints basic startup information
- calls `GET /healthz` on the repository
- sends a small message to `POST /`
- calls the local AS router-helper over HTTP
- queries `GET /bird/protocols` and `GET /bird/route` through that helper
- prints a final placeholder note showing where future router-control logic
  would be added

## Router Helper

Each adopting AS installs a minimal `router_helper.py` on its anchor router.
The helper listens on port `18081` and wraps a small allowlist of BIRD queries:

- `GET /healthz`
- `GET /bird/protocols`
- `GET /bird/route`

This keeps the agent external to the router while still letting it inspect
router-local BIRD state using a network API, which is closer to the RoST paper
model than running `birdc` inside the agent container.

Neither the repository nor the agent implements the RoST algorithm in this
example. They only demonstrate host-level placement, network reachability, and
basic inspection flow inside the SEED environment.

## Manual Validation

After compiling and starting the emulation, the current Phase 1 environment can
be validated manually with the following checks.

### 1. Test The Repository From A Reachable Host

From a host that can reach the repository:

```bash
curl http://<repo-host-ip>:18080/healthz
curl -X POST http://<repo-host-ip>:18080/ -H 'Content-Type: application/json' -d '{"message":"hello"}'
```

Expected behavior:

- `/healthz` returns a small JSON health response
- `POST /` returns `{"status": "received"}`

### 2. Test The Router Helper Locally On The Router

Open an adopting AS anchor router container and run:

```bash
curl http://127.0.0.1:18081/healthz
curl http://127.0.0.1:18081/bird/protocols
curl http://127.0.0.1:18081/bird/route
```

This verifies that:

- `router_helper.py` started correctly inside the router container
- the helper can invoke `birdc`
- BIRD state is readable through the helper API

### 3. Test The Router Helper From The Agent Host

Open an adopting AS `rost-agent` host and determine the helper IP:

```bash
ip route show default
```

Use the default gateway IP as the router-helper IP. In this example, the helper
runs on the colocated anchor router that serves as the `rost-agent` host's
default gateway on the reused AS-local network.

Then test the helper over the network:

```bash
curl http://<default-gateway-ip>:18081/healthz
curl http://<default-gateway-ip>:18081/bird/protocols
curl http://<default-gateway-ip>:18081/bird/route
```

This verifies the external-agent model directly: the agent-side network can
reach the router-side helper without entering the router container.

### 4. Run The Agent End-To-End

From an adopting AS `rost-agent` host, run:

```bash
/root/agent.py --repo-host <repo-host-ip> --repo-port 18080 --router-host <default-gateway-ip> --router-port 18081
```

Where:

- `<repo-host-ip>` is the IP address of the `rost-repo` host inside the
  emulated network
- `<default-gateway-ip>` is the router-helper IP reachable from the agent host

The agent should:

- report repository health-check success/failure
- report repository `POST /` success/failure
- report router-helper health success/failure
- report `birdc show protocols` output through `/bird/protocols`
- report `birdc show route` output through `/bird/route`

## Project Phases

- Phase 1: Read-only router visibility via helper. Completed. The agent is
  external to the router, the helper runs inside the router container, and the
  helper exposes read-only BIRD visibility over HTTP.
- Phase 2: Router control via helper. Planned. The helper will be extended to
  support controlled router-policy changes, such as policy updates and
  attribute modification, while keeping the agent external.
- Phase 3: Suppressor AS behavior via routing policy. Planned. The suppressor
  remains a routing-policy role implemented on routers, not an agent/helper
  application deployment.

## Future Suppressor Experiments

Future revisions can use this example to verify suppressor behavior at the
network layer. For example:

- inspect route propagation across the AS graph before and after policy changes
- observe which ASes continue to receive or stop receiving certain routes
- study how withdrawal-related behavior changes when suppressor policies are
  enabled
- compare ordinary AS behavior with suppressor-AS behavior using router state
  and BGP visibility tools

## Current Assumptions And Limitations

- The suppressor hook is installed and grounded in SEED's hook model, but it
  does not yet implement real withdrawal suppression.
- `agent.py` is installed on adopting AS `rost-agent` hosts for manual
  execution only; this example does not yet orchestrate automatic startup.
- `router_helper.py` is installed only on the anchor router of each adopting AS
  in this first phase; it is not yet a generic multi-router control plane.
- For transit-like adopting ASes, Phase 1 reuses one existing internal
  router-connected network for component reachability. This avoids changing the
  original Internet topology, but it is still only a temporary management-plane
  scaffold.
