## Demo Checklist & Teaching Guide

- Use the step-by-step demo guide in `temp_docs/DEMO-TEACH.md` for a classroom-ready flow:
  - Accounts, DNS MX, intra-domain delivery, simple BGP views, and connectivity tests.
  - Includes copy-paste commands and expected outputs.
  - Start Roundcube for live UI validation.

## Related Documentation

- EmailService API design (plan): `EmailService_design/API_SPEC.md`
- BGP audit notes: `docs/bgp_audit.md`
- Multi-dimensional testing guide: `docs/testing_guide.md`
- Completion summary and known limitations: `COMPLETION_SUMMARY.md`
# B29 Email (DNS-first) Example

A realistic multi-ISP, multi-IX email system that prioritizes DNS-based mail routing (MX records) and exposes a webmail frontend with Roundcube. This example is derived from the ES-29-1 experiment and integrates the reusable `EmailService` helper to programmatically attach mail providers during Docker compilation.

- Internet Map: http://localhost:8080/map.html
- Roundcube Webmail: http://localhost:8082

For a comprehensive step-by-step validation checklist, see:
- Multi-Dimensional Testing Guide: `docs/testing_guide.md`

## Scope & Status

- This repository’s maintained focus is the B29 example: `examples/internet/B29_email_dns/`.
- Earlier drafts (e.g., `29`, `29-1`) are legacy and not maintained for demos. Use B29 for all teaching and validation.

## Overview

- 6 realistic providers (simulated): `qq.com`, `163.com`, `gmail.com`, `outlook.com`, `company.cn`, `startup.net`.
- Full DNS hierarchy: Root, TLDs (.com, .net, .cn), and authoritative DNS for each email domain.
- Multi-IX + multi-ISP transport: Beijing-IX(100), Shanghai-IX(101), Guangzhou-IX(102), Global-IX(103); ISPs AS-2/3/4.
- Users and DNS cache in AS-150 (`10.150.0.53`).
- Roundcube connects to all providers for end-to-end demo and testing.

## Prerequisites

- Linux host with Docker and docker-compose.
- Python environment for SEED emulator (e.g., `seed-emulator` conda env) and repo root on `PYTHONPATH`.

## Quick Start

```bash
# 1) Generate
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  /home/parallels/miniconda3/envs/seed-emulator/bin/python email_realistic.py arm

# 2) Build and start
cd output
docker-compose build --no-cache
docker-compose up -d
cd ..

# 3) Accounts + Roundcube (http://localhost:8082)
./manage_roundcube.sh accounts
./manage_roundcube.sh start
```

Verify DNS MX quickly:
```bash
cd output
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
cd ..
```

## Design

- Base internet with multiple IXes and ISPs, plus user AS `150` and provider ASes `200..205`.
- Email servers use `docker-mailserver` configured for plaintext demo (not production).
- DNS-first routing: Postfix uses DNS (MX lookup) to find remote SMTP.
- `EmailService` integrates providers during compilation.

Key files:
- `email_realistic.py`: builds the topology, DNS, six providers, and attaches using `EmailService(platform=f"linux/{platform}", mode="dns", dns_nameserver="10.150.0.53")`.
- `docker-compose-roundcube.yml`: Roundcube compose with container names `roundcube-webmail-b29` / `roundcube-db-b29`.
- `manage_roundcube.sh`: helper to create accounts, start/stop Roundcube, and basic checks.

## Managing Roundcube

```bash
./manage_roundcube.sh start     # Start Roundcube
./manage_roundcube.sh stop      # Stop Roundcube
./manage_roundcube.sh restart   # Restart
./manage_roundcube.sh status    # Basic web check (8082)
./manage_roundcube.sh logs      # Follow Roundcube logs
./manage_roundcube.sh accounts  # Create demo accounts on all providers
```

## Validation

- DNS (from local cache `10.150.0.53`):
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
```
- BGP:
```bash
docker exec as100brd-ix100-10.100.0.100 birdc show protocols | grep BGP
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.202.0.0/24
```
- Email cross-delivery (command line):
```bash
# QQ -> Gmail
printf "Subject: QQ->Gmail\n\nBody\n" | docker exec -i mail-qq-tencent sendmail user@gmail.com
# Verify delivery (Saved) in Gmail logs
docker logs --tail 100 mail-gmail-google

# Gmail -> QQ
printf "Subject: Gmail->QQ\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
# Verify delivery (Saved) in QQ logs
docker logs --tail 100 mail-qq-tencent
```
- Webmail (Roundcube): http://localhost:8082
  - Use accounts created by `./manage_roundcube.sh accounts` (password `password123`).

### Intra-domain tests (self-send)

Quickly verify each provider can deliver locally to its own domain.

```bash
# QQ (qq.com)
printf "Subject: self QQ\n\n" | docker exec -i mail-qq-tencent sendmail user@qq.com

# 163 (163.com)
printf "Subject: self 163\n\n" | docker exec -i mail-163-netease sendmail user@163.com

# Gmail (gmail.com)
printf "Subject: self gmail\n\n" | docker exec -i mail-gmail-google sendmail user@gmail.com

# Outlook (outlook.com)
printf "Subject: self outlook\n\n" | docker exec -i mail-outlook-microsoft sendmail user@outlook.com

# Company (company.cn)
printf "Subject: self company\n\n" | docker exec -i mail-company-aliyun sendmail admin@company.cn

# Startup (startup.net)
printf "Subject: self startup\n\n" | docker exec -i mail-startup-selfhosted sendmail founder@startup.net
```

Check logs for Saved/INBOX evidence:

```bash
docker logs --since 2m <mail-container> | egrep -i "stored mail into mailbox 'INBOX'|status=sent|Saved"
```

### DNS checks (central vs per-AS caches)

- Central cache (AS-150):
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
```

Note: Central cache may return SERVFAIL for domains whose authoritative NS resides behind currently unreachable AS paths during certain BGP topologies. Prefer per-AS caches (below) or direct authoritative queries in demos.

- Per-AS caches (authoritative-forward preference):
```bash
# In provider AS (preferable for demos)
docker exec as200h-dns-cache-10.200.0.53 nslookup -type=mx gmail.com 127.0.0.1
docker exec as201h-dns-cache-10.201.0.53 nslookup -type=mx qq.com 127.0.0.1
docker exec as202h-dns-cache-10.202.0.53 nslookup -type=mx outlook.com 127.0.0.1
docker exec as203h-dns-cache-10.203.0.53 nslookup -type=mx 163.com 127.0.0.1

# Company / Startup
docker exec as204h-dns-cache-10.204.0.53 nslookup -type=mx company.cn 127.0.0.1
docker exec as205h-dns-cache-10.205.0.53 nslookup -type=mx startup.net 127.0.0.1
```

## Robustness Checks

- NXDOMAIN MX:
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx nope.invalid  # Expect NXDOMAIN
```
- Restart-and-resend:
```bash
docker restart mail-gmail-google
sleep 3
printf "Subject: Gmail->QQ (retry)\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
```
- Roundcube availability:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8082
```

### Batch cross-domain tests

Run the provided batch test to validate multiple cross-domain flows end-to-end and print a summary:

```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
./run_cross_tests.sh
# Example:
# PASS: user@qq.com -> user@gmail.com
# ...
# Summary: passes=8 fails=0 total=8
```

### Automation generator (transport-map) quick validation

Optionally validate the automation generator that builds a small transport-map email network. The script now lives alongside B29 at `tools/email_autogen.py`.

Note: Stop B29 first to avoid Docker compose name/network conflicts.

```bash
# 0) Stop B29 if running
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns/output && docker-compose down && cd -

# 1) Generate a 3-domain auto network (transport-map)
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  /home/parallels/miniconda3/envs/seed-emulator/bin/python \
  tools/email_autogen.py --platform arm --domains seedemail.net corporate.local smallbiz.org --asn-start 150

# 2) Bring it up and test
cd tools/output && docker-compose up -d && cd ../..
printf "password123\npassword123\n" | docker exec -i mail-seedemail-net setup email add alice@seedemail.net
printf "password123\npassword123\n" | docker exec -i mail-corporate-local setup email add admin@corporate.local
printf "password123\npassword123\n" | docker exec -i mail-smallbiz-org setup email add bob@smallbiz.org
printf "Subject: seed->corp\n\nBody\n" | docker exec -i mail-seedemail-net sendmail admin@corporate.local
printf "Subject: corp->smb\n\nBody\n" | docker exec -i mail-corporate-local sendmail bob@smallbiz.org
printf "Subject: smb->seed\n\nBody\n" | docker exec -i mail-smallbiz-org sendmail alice@seedemail.net

# 3) Tear down to keep environment clean
cd tools/output && docker-compose down && cd ../..

### Bulk accounts (CSV/generate)

Use `tools/bulk_accounts.py` to create many accounts quickly on B29 providers.

Examples:

```bash
# Generate 100 student accounts on company.cn and 20 teachers on startup.net
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
python tools/bulk_accounts.py --generate --count 100 --prefix stu --domain company.cn
python tools/bulk_accounts.py --generate --count 20 --prefix tea --domain startup.net --start 1

# Import CSV (map zju.edu.cn to company.cn)
python tools/bulk_accounts.py --csv tools/sample_class.csv --domain-map zju.edu.cn=company.cn

# Dry-run
python tools/bulk_accounts.py --csv tools/sample_class.csv --domain-map zju.edu.cn=company.cn --dry-run

# Email-only CSV (preferred). If your roster already contains emails:
# tools/emails.csv content:
#   email\n
#   alice@zju.edu.cn\n
#   bob@zju.edu.cn
python tools/bulk_accounts.py --csv tools/emails.csv

# IDs-only CSV and apply a default domain for realism (no teacher/student role distinction needed):
python tools/bulk_accounts.py --csv tools/ids.csv --default-domain zju.edu.cn
```
## Cleanup

```bash
# Stop Roundcube
authdir=$(pwd)
./manage_roundcube.sh stop

# Stop the emulation (from output/)
cd output
docker-compose down
cd "$authdir"
```

## Directory Layout

```
B29_email_dns/
├── email_realistic.py              # Build & compile DNS-first email system
├── manage_roundcube.sh             # Roundcube management & demo accounts
├── docker-compose-roundcube.yml    # Roundcube compose (b29 container names)
├── roundcube-config/               # Roundcube customization
├── templates/                      # Web templates (optional UI)
├── static/                         # Static assets
├── tools/                          # Helper tools (email_autogen.py, bulk_accounts.py)
├── temp_docs/                      # Legacy mixed-language docs (archived)
└── output/                         # Generated compose for SEED emulation
```

## Notes / Limitations

- Demo-only configuration; plaintext protocols enabled for pedagogy. Do not use in production.
- DKIM/DMARC/SPF are not hardened; logs include spam/AV pipeline for completeness.
- Concurrent runs with other internet-map examples may conflict; run one example at a time.

### Known Issue: AS-204 (company.cn) ↔ AS-205 (startup.net) BGP reachability

- Symptom: cross-domain mail between `admin@company.cn` and `founder@startup.net` may fail with "Network is unreachable".
- Cause (likely): with both AS-204 and AS-205 as customers of AS-2 (Telecom) but at different IXes, iBGP within AS-2 may not propagate customer routes across its IX routers as expected in the current seedemu defaults. See audit in `docs/bgp_audit.md`.
- Impact on demos: all primary providers (QQ, 163, Gmail, Outlook) are fully functional. Batch tests typically show 6 passes, 2 fails.
- Workarounds:
  - Keep demos to the first four providers (QQ, 163, Gmail, Outlook) — all flows work and cover real-world scenarios.
  - Or add a direct cross-connect peering to force reachability:
    - In `email_realistic.py` after `configure_bgp_peering(...)`, consider: `ebgp.addCrossConnectPeering(204, 205, PeerRelationship.Peer)`.
  - Or place AS-204 and AS-205 at the same IX and use a private peering there.
  - Or simplify topology to a single IX for all providers.

## Credits

## Automation: DNS-first and Transport modes

- **DNS-first (recommended for B29)**
  - Postfix relies on MX via DNS: `smtp_host_lookup = dns`.
  - In `email_realistic.py`, `EmailService(platform=..., mode="dns", dns_nameserver="10.150.0.53")` and per-provider override `dns=f"10.{ASN}.0.53"` are used when calling `add_provider(...)` and `attach_to_docker(...)`.
  - Pros: realistic, minimal hardcoding; aligns with internet mail.

- **Transport-map mode (explicit next-hop)**
  - Set `EmailService(..., mode="transport")` and expose ports including submission/imaps if needed.
  - The service generates `/etc/postfix/transport` mapping `domain -> smtp:[ip]:25` for every other domain.
  - Pros: deterministic, avoids DNS in teaching controlled experiments.
  - To switch in B29: change instantiation in `email_realistic.py` to `mode="transport"` and re-generate.

- **Tools for automation**
  - `tools/email_autogen.py`: build small multi-domain email networks with either approach; generates output/ and compose to bring up quickly.
  - `tools/bulk_accounts.py`: generate/import accounts (CSV/IDs/emails) across providers for classroom rosters.
  - See examples in sections above for usage patterns.

Based on SEED Emulator examples; extended with a reusable `EmailService` helper for provider attachment.
