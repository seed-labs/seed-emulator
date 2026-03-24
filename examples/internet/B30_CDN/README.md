# Simple CDN

This example builds a simple CDN on top of the mini Internet example.

The deployment includes:

- Three DNS servers, one in each region
- Three CDN edge nodes
- Three CDN origin nodes
- A single service domain: `www.example.com`

Each client uses a region-aware DNS server order. The DNS servers rewrite
`www.example.com` based on the client's source subnet and return the edge IP of
the East, West, or Central CDN site. Each edge node runs `nginx` and reverse
proxies requests to its local origin node, which also runs `nginx` and returns
a small JSON payload identifying the selected site.


## Topology

This example reuses the base topology from
[B00_mini_internet](/Users/bruce/seed-emulator/examples/internet/B00_mini_internet).

The CDN sites are:

- `nyc` for East
- `sjc` for West
- `chi` for Central

The DNS servers are placed in:

- `AS150` at `10.150.0.53`
- `AS152` at `10.152.0.53`
- `AS154` at `10.154.0.53`


## Running

Generate the Docker output with:

```bash
python ./cdn.py amd
```

This creates the output directory:

```bash
./output
```

Start the emulation manually:

```bash
cd output
docker compose build
docker compose up -d
```

Wait about 1-2 minutes for BGP, DNS, and `nginx` to settle.


## Verifying

From an East client:

```bash
docker exec -it as150h-host_0-10.150.0.71 sh -lc "cat /etc/resolv.conf"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "getent ahostsv4 www.example.com"
docker exec -it as150h-host_0-10.150.0.71 sh -lc "curl --noproxy '*' -s http://www.example.com:8080/"
```

From a West client:

```bash
docker exec -it as152h-host_0-10.152.0.71 sh -lc "getent ahostsv4 www.example.com"
docker exec -it as152h-host_0-10.152.0.71 sh -lc "curl --noproxy '*' -s http://www.example.com:8080/"
```

From a Central client:

```bash
docker exec -it as154h-host_0-10.154.0.71 sh -lc "getent ahostsv4 www.example.com"
docker exec -it as154h-host_0-10.154.0.71 sh -lc "curl --noproxy '*' -s http://www.example.com:8080/"
```

The DNS answers should point to different edge IPs for different regions, and
the JSON response should identify the selected CDN site.
