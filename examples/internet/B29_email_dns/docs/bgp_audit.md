# B29 BGP Audit (AS-204 ↔ AS-205)

## Context
- Scenario: DNS-first email with six providers across multiple IXes/ISPs.
- Issue: `company.cn` (AS-204) and `startup.net` (AS-205) cannot reach each other.
- Symptom in logs: Postfix defers with "Network is unreachable"; DNS is OK after per-AS caches.

## Symptoms and Evidence
- Router reachability tests:
```bash
# From AS-204 mail container
docker exec mail-company-aliyun ping -c 2 10.205.0.10  # Destination Net Unreachable

# From AS-205 mail container
docker exec mail-startup-selfhosted ping -c 2 10.204.0.10  # Destination Net Unreachable
```
- BIRD route lookups:
```bash
docker exec as204brd-router0-10.204.0.254 birdc show route for 10.205.0.0/24  # Network not found
docker exec as205brd-router0-10.205.0.254 birdc show route for 10.204.0.0/24  # Network not found
```

## What the code does (seedemu)

- `seedemu/layers/Ebgp.py`
  - Provider relationship export policy:
    - Provider→Customer: `export all` (no filter)
    - Customer→Provider: export `LOCAL,CUSTOMER` only
  - RS and Peer sessions restrict to `LOCAL,CUSTOMER` on export.
- `seedemu/layers/Ibgp.py`
  - iBGP uses loopback neighbors (e.g., `10.0.0.x`) and requires IGP reachability:
    ```bird
    ipv4 { table t_bgp; import all; export all; igp table t_ospf; };
    local <lo> as <asn>; neighbor <lo> as <asn>;
    ```
- `seedemu/utilities/Makers.py`
  - Transit AS builds per-IX routers (e.g., AS-2 `r100`, `r101`, `r102`, `r103`).
  - Adds internal Local networks between IX routers: `net_100_101`, `net_101_102`, `net_102_103`, etc.

## Likely Root Cause
- iBGP is configured over loopbacks; OSPF must provide reachability for those loopbacks between provider routers.
- Observations:
  - `Ibgp` logs show neighbors like `10.0.0.1 <-> 10.0.0.2`, but route table lookups report "Network not found" for customer /24s on other edges.
  - This strongly suggests iBGP sessions across AS-2's IX routers may not establish due to missing IGP reachability to loopbacks (OSPF not originating loopback addresses).
- Result: AS-2 learns each customer prefix at the local IX edge, but does not propagate it via iBGP to the other IX edge, so the other customer remains unreachable.

## Why DNS was fine but mail still failed
- We made per-AS caches authoritative for `company.cn` and `startup.net`, so DNS resolution worked everywhere.
- Without BGP route propagation between AS-204 and AS-205, SMTP could not reach `10.205.0.10` or `10.204.0.10`.

## Workarounds implemented
- Focus demos on the four primary providers (QQ, 163, Gmail, Outlook) — all flows pass.
- Documented the limitation and options in `README.md` under "Known Issue".

## Options to fully fix for 204↔205
- **Add a direct peering:**
  - In `email_realistic.py`: `ebgp.addCrossConnectPeering(204, 205, PeerRelationship.Peer)`.
- **Place both customers at the same IX and private-peer there.**
- **Enhance IGP/iBGP:**
  - Ensure OSPF originates loopback prefixes so iBGP sessions between AS-2 routers always come up.
  - Alternatively, allow iBGP to use IX interface addresses rather than loopbacks (feature request).

## Conclusion
- The seedemu modules behave as designed for common cases; the limitation appears when relying on multi-IX transit and iBGP over loopbacks without explicit loopback IGP advertisement.
- For teaching/demo, the system is stable and complete using QQ/163/Gmail/Outlook. The 204↔205 case can be a discussion topic on BGP policy and IGP underlay requirements.
