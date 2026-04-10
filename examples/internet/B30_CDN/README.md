# CDNService Baseline Example

This example validates the new `CDNService` and its integration with
`DomainNameService`.

The current design keeps the two services loosely coupled:

- DNS explicitly exposes an include file through `setInclude(...)`
- CDN explicitly writes policy-specific include content through `setIncludeContent(...)`

The topology is built on top of the mini Internet and models a simple CDN with:

- one authoritative DNS server
- three edge sites
- one shared origin
- one service domain: `www.example.com`

The CDN uses region-aware DNS answers:

- East clients resolve to `10.181.0.100`
- West clients resolve to `10.182.0.100`
- Central clients resolve to `10.183.0.100`

All three edge nodes proxy to the same origin at `10.184.0.10`.


## Topology

The example reuses the base topology from
`examples/internet/B00_mini_internet`.

CDN components:

- DNS: `AS150`, `10.150.0.53`
- East edge: `AS181`, `10.181.0.100`
- West edge: `AS182`, `10.182.0.100`
- Central edge: `AS183`, `10.183.0.100`
- Shared origin: `AS184`, `10.184.0.10`


## Running

Generate the Docker output:

```bash
conda run -n seedpy310 python examples/internet/B30_CDN/cdn.py amd
```

This creates:

```bash
examples/internet/B30_CDN/output
```

Build and start the topology manually:

```bash
cd examples/internet/B30_CDN/output
DOCKER_BUILDKIT=0 docker compose build
docker compose up -d
```

Wait about 10-20 seconds for services to start.


## Verifying

East client:

```bash
docker exec as150h-host_0-10.150.0.71 sh -lc 'getent ahostsv4 www.example.com'
docker exec as150h-host_0-10.150.0.71 sh -lc 'env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY curl --noproxy "*" -s -D - http://www.example.com:8080/ -o /dev/null'
```

West client:

```bash
docker exec as152h-host_0-10.152.0.71 sh -lc 'getent ahostsv4 www.example.com'
docker exec as152h-host_0-10.152.0.71 sh -lc 'env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY curl --noproxy "*" -s -D - http://www.example.com:8080/ -o /dev/null'
```

Central client:

```bash
docker exec as154h-host_0-10.154.0.71 sh -lc 'getent ahostsv4 www.example.com'
docker exec as154h-host_0-10.154.0.71 sh -lc 'env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY curl --noproxy "*" -s -D - http://www.example.com:8080/ -o /dev/null'
```

Expected results:

- East resolves to `10.181.0.100`
- West resolves to `10.182.0.100`
- Central resolves to `10.183.0.100`
- HTTP responses include:
  - `X-CDN-Origin: global_origin`
  - `X-CDN-Origin-IP: 10.184.0.10`
  - `X-CDN-Edge`
  - `X-CDN-Region`
  - `X-CDN-Edge-IP`


## What This Example Exercises

This example checks that:

- `CDNService` can bind virtual origin and edge nodes to concrete hosts
- final edge and origin configuration is rendered before container startup
- `DomainNameService` can host CDN-generated BIND views through an include file
- region-aware DNS steering and HTTP proxying work end to end


## Files

- `examples/internet/B30_CDN/cdn.py`: baseline CDN built with `CDNService`
- `examples/internet/B30_CDN/output`: generated Docker deployment
