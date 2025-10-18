# B29 DNS-First Email System - Completion Summary

## Status: ✅ Core Functionality Working

Cross-domain email delivery is **fully functional** for the primary providers (QQ, 163, Gmail, Outlook). DNS SERVFAIL issues have been resolved, and the system is ready for demos and testing.

---

## What Was Fixed

### 1. DNS SERVFAIL Root Cause
- **Problem**: Malformed zone files in `as150h-dns-cache-10.150.0.53` caused `SERVFAIL` for MX lookups.
- **Solution**: 
  - Replaced zone files with correct FQDN records (avoiding `$ORIGIN`/`@` syntax).
  - Validated all zones with `named-checkzone`.
  - Restarted named.
- **Result**: All six mail domains (`qq.com`, `163.com`, `gmail.com`, `outlook.com`, `company.cn`, `startup.net`) now resolve MX correctly on the central cache.

### 2. Per-AS DNS Caches
- **Problem**: Providers couldn't reach the central DNS cache (`10.150.0.53`) across AS boundaries.
- **Solution**:
  - Added per-AS local DNS caches at `10.{ASN}.0.53` for AS-200 through AS-205.
  - Each cache forwards only the six mail zones to their authoritative NS or serves them as master zones.
  - Updated `EmailService` to inject per-provider DNS into compose (`dns: 10.{ASN}.0.53`).
- **Result**: Providers resolve DNS locally without cross-AS dependencies.

### 3. Authoritative NS for company.cn and startup.net
- **Problem**: The authoritative NS containers for `ns-company-cn` and `ns-startup-net` were not created or not running named.
- **Solution**:
  - Made the central cache (`10.150.0.53`) authoritative for all six domains as a fallback.
  - Made per-AS caches for AS-204 and AS-205 authoritative (master zones) for `company.cn` and `startup.net`.
- **Result**: DNS resolution works for all six domains from all providers.

---

## Verified Working

### Cross-Domain Email Delivery
- **QQ → Gmail**: ✅ Delivered and saved
- **Gmail → QQ**: ✅ Delivered and saved
- **QQ → 163**: ✅ Delivered and saved
- **163 → Outlook**: ✅ Delivered and saved
- **163 → Gmail**: ✅ Delivered and saved
- **Outlook → QQ**: ✅ Delivered and saved

**Evidence**: Receiver logs show `postfix/lmtp[...] status=sent (... Saved)` and `dovecot: lmtp(...) stored mail into mailbox 'INBOX'`.

### DNS Resolution
- **Central cache (`10.150.0.53`)**: All six domains resolve MX correctly.
- **Per-AS caches**: QQ, 163, Gmail, Outlook providers resolve all domains.
- **Company/Startup caches**: Resolve all domains locally as master zones.

### Resilience
- **After restart**: Both QQ and Gmail containers were restarted; cross-domain sends still delivered successfully.

---

## Known Limitations

### BGP Routing Issue (AS-204 ↔ AS-205)
- **Problem**: `company.cn` (AS-204) and `startup.net` (AS-205) cannot reach each other due to missing BGP routes.
  - Both are now customers of AS-2 (电信), but peered at different IXes (AS-204 at IX-101, AS-205 at IX-100).
  - AS-2's iBGP mesh is not properly propagating customer routes between its routers.
  - This appears to be a SEED Emulator BGP configuration limitation with multi-IX ISPs and customer route propagation.
- **Impact**: Cross-domain email between `admin@company.cn` and `founder@startup.net` fails with "Network is unreachable".
- **Workaround**: Use the first four providers (QQ, 163, Gmail, Outlook) for demos and testing. They are all reachable from each other and represent the most common real-world scenarios.
- **Future Fix**: 
  - Add direct peering between AS-204 and AS-205 at the same IX.
  - Or investigate SEED Emulator's iBGP route propagation for multi-IX ISPs.
  - Or use a simpler topology with all providers on the same IX.

---

## Code Changes

### `email_realistic.py`
- **`configure_dns_system()`**:
  - Added per-AS DNS caches (`dns-cache-{asn}`) bound to `10.{ASN}.0.53`.
  - Each cache forwards the six mail zones to their authoritative NS.
- **`run()`**:
  - Injects per-provider DNS into compose via `EmailService.add_provider(..., dns=f"10.{ASN}.0.53")`.

### `seedemu/services/EmailService.py`
- **`add_provider(..., dns: Optional[str])`**: Added optional `dns` parameter.
- **Compose generation**: Prefers per-provider `dns` over global nameserver.
- **Postfix config**: Keeps DNS-first routing (`relayhost=`, `smtp_host_lookup=dns`, `smtp_dns_support_level=enabled`).

### Zone Files (Authoritative, FQDN Style)
- Created in `temp_dns_zones/` for all six domains.
- Copied to `/etc/bind/zones/` in:
  - `as150h-dns-cache-10.150.0.53` (all six domains).
  - `as204h-dns-cache-10.204.0.53` (`company.cn`, `startup.net`).
  - `as205h-dns-cache-10.205.0.53` (`company.cn`, `startup.net`).
- Validated with `named-checkzone` and loaded by named.

---

## Documentation Delivered

### Quick Demo Guide
- **Location**: `examples/internet/B29_email_dns/temp_docs/quick_demo_guide.md`
- **Contents**: 
  - Start, test via CLI, Roundcube, batch automation, CSV import.
  - Code pointers to `email_realistic.py`, `EmailService.py`, DNS service classes.
  - Practical notes on DNS warm-up, queues, logs.

### Testing Guide (Updated)
- **Location**: `examples/internet/B29_email_dns/docs/testing_guide.md`
- **New Section 12**: DNS pre-heating and per-AS cache fallback.
  - Design explanation.
  - Verification commands for per-AS caches and central cache.
  - Troubleshooting SERVFAIL.

---

## How to Verify

### Quick CLI Tests
```bash
# QQ → Gmail
printf "Subject: QQ->Gmail $(date +%s)\n\nBody\n" | docker exec -i mail-qq-tencent sendmail user@gmail.com
docker logs --since 2m mail-gmail-google | egrep -i "Saved|INBOX|lmtp|status=sent" | tail -n 50

# Gmail → QQ
printf "Subject: Gmail->QQ $(date +%s)\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
docker logs --since 2m mail-qq-tencent | egrep -i "Saved|INBOX|lmtp|status=sent" | tail -n 50
```

### DNS Checks
```bash
# Central cache (all six domains)
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx company.cn

# Per-AS cache (QQ provider)
docker exec as200h-dns-cache-10.200.0.53 nslookup -type=mx gmail.com 127.0.0.1
```

### Batch Test
```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
./run_cross_tests.sh
```
**Expected**: 6 passes (QQ, 163, Gmail, Outlook flows), 2 fails (company ↔ startup due to BGP routing).

---

## Recommended Next Steps

1. **Demo with Primary Providers**: Use QQ, 163, Gmail, Outlook for classroom demos and testing. They are fully functional.
2. **Fix BGP Routing**: Add peering between AS-204 and AS-205, or configure AS-2/AS-3 to transit customer traffic properly.
3. **Roundcube**: Start with `./manage_roundcube.sh start` and test in-UI send/receive.
4. **Batch Automation**: Use `./run_cross_tests.sh` with custom `--pairs` file for targeted flows.
5. **CSV Import**: Use `tools/bulk_accounts.py` to provision accounts from class rosters.

---

## Summary

- **DNS SERVFAIL**: ✅ Fixed (zone files corrected, per-AS caches added).
- **Cross-domain email**: ✅ Working for QQ, 163, Gmail, Outlook.
- **Resilience**: ✅ Tested (restart and resend successful).
- **Documentation**: ✅ Delivered (quick demo guide, testing guide updated).
- **Known issue**: BGP routing between AS-204 and AS-205 (workaround: use first four providers).

The system is **ready for demos, testing, and classroom use**.
