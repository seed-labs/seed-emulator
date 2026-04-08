# Reviewer Validation

This file is the primary reviewer-facing validation guide for the RoST-style
example. It prioritizes externally meaningful evidence:

- repository reachability
- BIRD route presence and absence
- BIRD route detail and export visibility
- downstream or neighbor observation
- real routing effects after helper-driven policy changes

Helper state JSON, generated policy files, and wrapper/config inspection remain
useful, but they are secondary implementation/debugging checks and are listed
separately at the end.

## Validation Targets

- Repository validation target: `10.154.0.0/24`
- Dynamic policy demo target: `10.153.0.0/24`
- Suppressor validation target: `10.155.0.0/24`

These are intentionally separated:

- `10.154.0.0/24` is used only for repository-related validation.
- `10.153.0.0/24` is used for helper-driven dynamic control validation.
- `10.155.0.0/24` is used for suppressor validation.

## Build And Start

```bash
cd nsdi/rost
python3 rost_env.py amd
cd output
docker-compose up -d
```

Use `python3 rost_env.py arm` instead on ARM64 hosts.

For the walkthrough below, use:

- adopting agent container: `as150h-rost-agent-10.150.0.72`
- adopting router: `as150r-router0`
- suppressor router: `as3r-r100`

## Primary Reviewer-Facing Validation

### 1. Repository Reachability

Open a shell in the adopting agent container:

```bash
docker exec -it as150h-rost-agent-10.150.0.72 bash
```

Discover the adopting router IP:

```bash
ip route show default
```

Use the default gateway as `<router-ip>`.

Find the repository host IP:

```bash
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' as154h-rost-repo
```

Use that value as `<repo-ip>`, then verify that the agent can reach the
repository service:

```bash
python3 /root/agent.py \
  --repo-host <repo-ip> \
  --repo-port 18080 \
  --router-host <router-ip> \
  --router-port 18081
```

Primary evidence on the adopting router:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.154.0.0/24
birdc show route 10.154.0.0/24 all
```

Reviewer-facing conclusion:

- repository prefix `10.154.0.0/24` is reachable by default
- the agent can reach the repository service in AS154
- BIRD on AS150 sees `10.154.0.0/24`

### 2. Dynamic Import Control

On the adopting router, confirm the ordinary non-repository target is present
before invalidation:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.153.0.0/24
birdc show route 10.153.0.0/24 all
```

From the adopting agent container, enable control and invalidate the route:

```bash
docker exec -it as150h-rost-agent-10.150.0.72 bash
ip route show default
python3 /root/agent.py --router-ip <router-ip> --enable
python3 /root/agent.py --router-ip <router-ip> --invalidate 10.153.0.0/24
```

Re-check on the adopting router:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.153.0.0/24
```

Validated result:

- `10.153.0.0/24` is initially visible on AS150
- after `invalidate 10.153.0.0/24`, `birdc show route 10.153.0.0/24` on AS150 becomes `Network not found`

Clear the invalid state and check again:

```bash
docker exec -it as150h-rost-agent-10.150.0.72 bash
python3 /root/agent.py --router-ip <router-ip> --clear-invalid 10.153.0.0/24
docker exec -it as150r-router0 bash
birdc show route 10.153.0.0/24
```

Validated result:

- after `clear-invalid 10.153.0.0/24`, the route reappears

### 3. RouteID / Export-Side Attribute Control

The export-side attribute mutation is visible when control is applied on the
upstream router in AS2 and observed from downstream AS150.

On the AS2 adopting agent, discover the router IP and apply the controls:

```bash
docker exec -it as2h-rost-agent-10.2.0.72 bash
ip route show default
python3 /root/agent.py --router-ip <router-ip> --enable
python3 /root/agent.py --router-ip <router-ip> --allow 10.153.0.0/24
python3 /root/agent.py --router-ip <router-ip> --routeid 10.153.0.0/24
```

Observe the route on AS150:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.153.0.0/24 all
```

Validated result:

- after enabling control on AS2 and applying `allow 10.153.0.0/24` and
  `routeid 10.153.0.0/24`
- AS150 receives the route with `BGP.community: (65000,100)`

### 4. Suppressor Validation

#### Default Topology Behavior

The suppressor validation target is `10.155.0.0/24`. In the default topology,
the reviewer-facing evidence is edge-level withholding on AS3, not guaranteed
downstream loss.

Confirm that AS3 still has the route locally and does not export it on the
patched edge:

```bash
docker exec -it as3r-r100 bash
birdc show route 10.155.0.0/24
birdc show route export p_rs100 10.155.0.0/24
```

Observe the downstream router separately:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.155.0.0/24
birdc show route 10.155.0.0/24 all
```

Validated interpretation:

- AS3 locally retains `10.155.0.0/24`
- AS3 withholds `10.155.0.0/24` on the patched export edge
- downstream routers may still retain visibility of the prefix
- BGP may select an alternate path in the default topology

This is suppressor edge-level withholding, not guaranteed downstream loss.

#### Controlled Experiment: Removing Alternate Paths

To demonstrate complete downstream loss, remove AS2's alternate propagation
paths and allow BGP to reconverge.

On AS2:

```bash
docker exec -it as2r-r100 bash
birdc disable p_rs100
birdc disable p_rs102
```

Then inspect the downstream observer again:

```bash
docker exec -it as150r-router0 bash
birdc show route 10.155.0.0/24
```

Validated interpretation:

- after disabling `p_rs100` and `p_rs102` on AS2 and waiting for reconvergence
- `birdc show route 10.155.0.0/24` on AS150 returns `Network not found`

This controlled experiment shows that once alternate propagation paths are
removed, the suppressor's export withholding produces complete downstream loss
of the prefix at the documented observer.

## Secondary Implementation / Debugging Checks

These checks are useful for debugging or code review, but they are not the
primary behavioral evidence.

### Helper Runtime State

From an adopting agent container:

```bash
curl -s http://<router-ip>:18081/rost/state | python3 -m json.tool
```

Useful checks:

- helper starts from an empty/default state on a fresh run
- helper mutations update the stored state as expected

### Helper State And Generated Policy Files

From an adopting router:

```bash
cat /etc/bird/rost_policy_state.json
cat /etc/bird/rost_policy.conf
```

Useful checks:

- `rost_policy_state.json` reflects the helper state
- `rost_policy.conf` reflects the generated BIRD functions

### Static Config / Wrapper Inspection

From an adopting router:

```bash
grep -n 'include "/etc/bird/rost_policy.conf"' /etc/bird/bird.conf
grep -n "rost_export_is_allowed" /etc/bird/bird.conf
grep -n "rost_import_is_invalid" /etc/bird/bird.conf
```

From the suppressor router:

```bash
grep -n "rost_static_suppressor_match" /etc/bird/bird.conf
grep -n "10.155.0.0/24" /etc/bird/bird.conf
```

Useful checks:

- wrapper functions are present
- the suppressor target appears in the static suppressor policy

### Helper Response Inspection

From an adopting agent container:

```bash
curl -s -X POST http://<router-ip>:18081/bird/configure | python3 -m json.tool
curl -s http://<router-ip>:18081/bird/protocols | python3 -m json.tool
```

Useful checks:

- helper reports `birdc configure` status
- helper reports BGP refresh results
