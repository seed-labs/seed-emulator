# C2DN Experiment Report

## Overview

This document describes a reproducible experiment for the paper:

- **C2DN: How to Harness Erasure Codes at the Edge for Efficient Content Delivery**
- Paper link: [NSDI 2022 paper PDF](https://www.usenix.org/system/files/nsdi22-paper-yang_juncheng.pdf)

The goal is to reproduce the paper's core mechanism in a controlled SeedEmu
environment:

- conventional edge caching becomes fragile when a cache node is unavailable
- erasure-coded edge storage can continue serving objects during the same
  failure window
- origin traffic can therefore be reduced during cache-node failure

The experiment is implemented in:

- `nsdi/CDN/c2dn/c2dn.py`

The baseline CDN example remains:

- `nsdi/CDN/cdn.py`


## Experiment Idea

The experiment compares two storage schemes behind one frontend:

1. `baseline.example.com`
   - each object is stored as one full copy on one cache node
   - if that cache node becomes unavailable, requests for that object miss and
     the frontend must fetch it from origin again

2. `c2dn.example.com`
   - each object is encoded into two data chunks and two parity chunks
   - the four chunks are placed on four different cache nodes
   - if one cache node becomes unavailable, the frontend can reconstruct the
     object from the surviving chunks without contacting origin

Object placement is computed from a deterministic hash of the object key,
independently from object size. This keeps the baseline placement reasonably
fair and avoids an artificial coupling between size class and node choice.


## What Was Added on Top of `cdn.py`

The experiment does **not** modify `nsdi/CDN/cdn.py`.
Instead, it creates a separate topology in
`nsdi/CDN/c2dn/c2dn.py`.

Compared with the baseline CDN example, this experiment adds:

1. A dedicated edge-cluster AS
   - `AS191`
   - one frontend
   - four cache nodes

2. A dedicated origin AS
   - `AS192`
   - one origin server

3. A dedicated DNS server
   - `AS150`
   - IP `10.150.0.53`
   - returns:
     - `baseline.example.com -> 10.191.0.10`
     - `c2dn.example.com -> 10.191.0.10`

4. A workload-aware frontend service
   - serves both baseline and C2DN modes
   - exposes:
     - `/object/<key>`
     - `/__stats`
     - `/__reset`
     - `/__set_cache`
     - `/__run_workload`

5. Four cache-node services
   - each stores chunks locally
   - each exposes:
     - `/chunk`
     - `/__stats`
     - `/__set`
     - `/__reset`

6. One origin service
   - serves deterministic objects of varying sizes
   - exposes:
     - `/object/<key>`
     - `/__stats`
     - `/__reset`


## Topology

The experiment uses the mini Internet as the base topology.

- clients are regular stub-AS hosts from the mini Internet
- DNS is placed in `AS150`
- the edge cluster is placed in `AS191`
- the origin is placed in `AS192`

Logical request path:

1. client
2. DNS
3. frontend
4. cache cluster or origin


## Workload Model

The frontend can run a deterministic Zipf-like workload internally.

Parameters:

- `objects`: number of distinct objects
- `requests`: total number of requests
- `failure_node`: cache node to mark unavailable
- `failure_at`: request index when the failure begins

Object sizes vary by key:

- `64 KiB`
- `128 KiB`
- `192 KiB`
- `256 KiB`

This makes `byte_miss_ratio` more meaningful than just counting request misses.

Each call to `/__run_workload`:

- resets frontend, cache, and origin state
- warms the system through actual workload requests
- marks one cache node unavailable at the configured failure point
- returns aggregate metrics together with `pre_failure` and `post_failure`
  breakdowns


## Running the Experiment

Generate the Docker output:

```bash
cd nsdi/CDN/c2dn
conda run -n seedpy310 python c2dn.py amd
```

This creates:

```bash
nsdi/CDN/c2dn/output
```

Start Docker manually:

```bash
cd nsdi/CDN/c2dn/output
docker compose build
docker compose up -d
```

Wait about 1-2 minutes for routing, DNS, and services to settle.


## Validation Commands

Validate DNS from a client, for example `AS150`:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "getent ahostsv4 baseline.example.com"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "getent ahostsv4 c2dn.example.com"
```

Run the baseline workload:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s 'http://baseline.example.com:8080/__run_workload?mode=baseline&objects=100&requests=1000&failure_node=0&failure_at=500'"
```

Run the C2DN workload:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s 'http://c2dn.example.com:8080/__run_workload?mode=c2dn&objects=100&requests=1000&failure_node=0&failure_at=500'"
```

Inspect frontend, cache, and origin counters:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.191.0.10:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.191.0.11:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.191.0.12:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.191.0.13:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.191.0.14:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.192.0.10:8080/__stats"
```


## Observed Results

The following results were obtained with:

- `objects=100`
- `requests=1000`
- `failure_node=0`
- `failure_at=500`

### Baseline Result

Observed response:

```json
{"mode": "baseline", "num_objects": 100, "num_requests": 1000, "failure_node": 0, "failure_at": 500, "request_miss_ratio": 0.181, "byte_miss_ratio": 0.2312, "origin_fetches": 181, "origin_bytes": 32636928, "recoveries": 0, "write_bytes_by_node": [3932160, 4259840, 4259840, 3932160], "write_skew_bytes": 327680, "pre_failure": {"requests": 500, "hits": 400, "misses": 100, "recoveries": 0, "origin_fetches": 100, "origin_bytes": 16384000, "client_bytes": 70582272, "request_miss_ratio": 0.2, "byte_miss_ratio": 0.2321}, "post_failure": {"requests": 500, "hits": 419, "misses": 81, "recoveries": 0, "origin_fetches": 81, "origin_bytes": 16252928, "client_bytes": 70582272, "request_miss_ratio": 0.162, "byte_miss_ratio": 0.2303}, "frontend_stats": {"requests": 1000, "hits": 819, "misses": 181, "recoveries": 0, "origin_fetches": 181, "origin_bytes": 32636928, "client_bytes": 141164544, "write_ops_by_node": [24, 26, 26, 24], "write_bytes_by_node": [3932160, 4259840, 4259840, 3932160]}, "origin_stats": {"requests": 181, "bytes_sent": 32636928}, "cache_stats": [{"up": false, "reads": 57, "writes": 24, "write_bytes": 3932160, "keys": 24}, {"up": true, "reads": 374, "writes": 26, "write_bytes": 4259840, "keys": 26}, {"up": true, "reads": 230, "writes": 26, "write_bytes": 4259840, "keys": 26}, {"up": true, "reads": 158, "writes": 24, "write_bytes": 3932160, "keys": 24}]}
```

Key observations:

- `pre_failure.origin_fetches = 100`
- `post_failure.origin_fetches = 81`
- `recoveries = 0`
- `write_skew_bytes = 327680`

Interpretation:

- the baseline warms the cache during the first half of the workload
- after `cache0` becomes unavailable, a subset of objects becomes unavailable
  at the edge and must be fetched from origin again
- the write distribution is now close to uniform, which means the failure
  behavior is no longer confounded by a biased placement rule


### C2DN Result

Observed response:

```json
{"mode": "c2dn", "num_objects": 100, "num_requests": 1000, "failure_node": 0, "failure_at": 500, "request_miss_ratio": 0.1, "byte_miss_ratio": 0.1161, "origin_fetches": 100, "origin_bytes": 16384000, "recoveries": 500, "write_bytes_by_node": [8192000, 8192000, 8192000, 8192000], "write_skew_bytes": 0, "pre_failure": {"requests": 500, "hits": 400, "misses": 100, "recoveries": 0, "origin_fetches": 100, "origin_bytes": 16384000, "client_bytes": 70582272, "request_miss_ratio": 0.2, "byte_miss_ratio": 0.2321}, "post_failure": {"requests": 500, "hits": 500, "misses": 0, "recoveries": 500, "origin_fetches": 0, "origin_bytes": 0, "client_bytes": 70582272, "request_miss_ratio": 0.0, "byte_miss_ratio": 0.0}, "frontend_stats": {"requests": 1000, "hits": 900, "misses": 100, "recoveries": 500, "origin_fetches": 100, "origin_bytes": 16384000, "client_bytes": 141164544, "write_ops_by_node": [100, 100, 100, 100], "write_bytes_by_node": [8192000, 8192000, 8192000, 8192000]}, "origin_stats": {"requests": 100, "bytes_sent": 16384000}, "cache_stats": [{"up": false, "reads": 400, "writes": 100, "write_bytes": 8192000, "keys": 100}, {"up": true, "reads": 900, "writes": 100, "write_bytes": 8192000, "keys": 100}, {"up": true, "reads": 900, "writes": 100, "write_bytes": 8192000, "keys": 100}, {"up": true, "reads": 900, "writes": 100, "write_bytes": 8192000, "keys": 100}]}
```

Key observations:

- `pre_failure.origin_fetches = 100`
- `post_failure.origin_fetches = 0`
- `post_failure.misses = 0`
- `recoveries = 500`
- `write_skew_bytes = 0`

Interpretation:

- the first half is again dominated by initial cache warm-up
- after `cache0` becomes unavailable, the frontend still reconstructs every
  object from the surviving chunks
- no additional origin traffic is generated during the failure window
- chunk writes are perfectly balanced across the four cache nodes


## What These Results Prove

This experiment supports the paper's core mechanism:

1. Under a fairer object-placement policy, the baseline no longer has a large
   artificial write skew.

2. Even under that fairer baseline, a single unavailable cache node still
   causes additional origin fetches in the conventional scheme.

3. Under the same workload and the same failure event, the C2DN-style encoded
   scheme avoids all post-failure origin fetches by reconstructing objects from
   surviving chunks.

4. The encoded scheme also distributes writes more evenly across nodes.

The most important evidence is the contrast during the failure window:

- baseline: `post_failure.origin_fetches = 81`
- C2DN: `post_failure.origin_fetches = 0`

This is the clearest signal that the encoded edge-cache layout is more robust
than the conventional single-copy baseline during cache-node failure.


## Notes on Reading Counters

Two details matter when interpreting the metrics:

1. `__run_workload` resets frontend, cache, and origin state before each run.
   Therefore, `__stats` only reflects the most recently executed workload.

2. The `pre_failure` and `post_failure` sections should not be read as a pure
   "before vs after failure" comparison of steady-state miss ratio. The first
   phase still includes initial cache warm-up, while the second phase includes
   both a warmed cache and a failure event. The more reliable failure indicator
   is the difference in post-failure origin traffic between baseline and C2DN.
