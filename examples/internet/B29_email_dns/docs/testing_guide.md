# B29 Multi-Dimensional Testing Guide

This guide provides a thorough checklist and runnable commands to validate the B29 DNS-first email example end-to-end, including: DNS, BGP, email flows (intra- and cross-domain), logging/record verification, resilience, and large-scale/roster-based automation.

- Internet Map: http://localhost:8080/map.html
- Roundcube: http://localhost:8082

## 1) Environment pre-checks

- Containers up (from `B29_email_dns/output/`):
```bash
docker-compose ps
```
- Roundcube availability:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8082
```
- BGP visibility (examples):
```bash
docker exec as100brd-ix100-10.100.0.100 birdc show protocols | grep BGP
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.202.0.0/24
```

## 2) DNS validation

- Query A and MX records from local DNS cache `10.150.0.53`:
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
```
- NXDOMAIN behavior:
```bash
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx nope.invalid  # Expect NXDOMAIN
```

## 3) Connectivity checks

- Ping and traceroute to provider mail IPs (sample):
```bash
docker exec as150h-host_0-10.150.0.71 ping -c 2 10.202.0.10
# traceroute may require installing: busybox/traceroute is included in base images
```
- Visualize via Internet Map (see the link at top).

## 4) Email flows (manual)

- Intra-domain (e.g., qq.com to qq.com):
```bash
printf "Subject: intra QQ test\n\nBody\n" | docker exec -i mail-qq-tencent sendmail user@qq.com
```
- Cross-domain (e.g., Gmail -> QQ):
```bash
printf "Subject: Gmail->QQ $(date +%s)\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
```
- Verify delivery from logs (look for LMTP Saved or INBOX stored):
```bash
docker logs --since 3m mail-qq-tencent | egrep -i "to=<user@qq.com>|stored mail into mailbox 'INBOX'|status=sent|lmtp"
```

Notes:
- Subjects include a timestamp token to help correlate with logs.
- If needed, grep by `message-id=<...>` which appears in cleanup logs.

## 5) Batch cross-domain tests

Use the batch script to exercise multiple flows and get a summary.

- Defaults:
```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
./run_cross_tests.sh
```
- Custom flows file (one "from to" pair per line, `#` for comments):
```bash
cat > pairs.txt << 'EOF'
user@qq.com user@gmail.com
user@gmail.com user@qq.com
user@163.com user@outlook.com
# intra-domain samples
user@qq.com user2@qq.com
EOF
./run_cross_tests.sh --pairs pairs.txt | tee batch_results.txt
```
- The script ensures accounts exist before sending and polls logs up to ~20s for LMTP Saved evidence.

## 6) Resilience tests

- Restart and resend (Gmail -> QQ example):
```bash
docker restart mail-gmail-google
sleep 3
printf "Subject: Gmail->QQ (after-restart) $(date +%s)\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
# Verify Saved in QQ logs
docker logs --since 3m mail-qq-tencent | egrep -i "Saved|INBOX|to=<user@qq.com>|lmtp"
```

## 7) Large-scale | quantity-based automation

For quickly adding many providers or simulating a larger email network (without DNS), use the colocated transport-map generator.

- Generate providers under `tools/output/`:
```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  python \
  tools/email_autogen.py --platform arm --providers 8 --asn-start 150
```
- Start the network (separate from B29 main `output/`):
```bash
cd tools/output && docker-compose up -d
```
- Provision many accounts (examples):
```bash
# 100 accounts on company.cn (zero-padded)
python tools/bulk_accounts.py --generate --count 100 --prefix user --domain company.cn --pad 4

# For autogen domains (e.g., seedemail.net), map domain->container if needed
python tools/bulk_accounts.py --generate --count 50 --prefix user --domain seedemail.net \
  --containers seedemail.net=mail-seedemail-net
```
- Tear down when done:
```bash
cd tools/output && docker-compose down
```

## 8) Roster-based automation (CSV)

Use `tools/bulk_accounts.py` to import a class roster or any email list.

- Preferred: email-only CSV
```
email
alice@zju.edu.cn
bob@zju.edu.cn
```
- If you want to map a real school domain to an internal provider for testing:
```bash
python tools/bulk_accounts.py --csv tools/sample_class.csv --domain-map zju.edu.cn=company.cn
```
- If your CSV uses IDs only (no emails), set a default domain:
```bash
# CSV: just IDs per line (or first column) -> default domain applied
python tools/bulk_accounts.py --csv ids.csv --default-domain zju.edu.cn
```
- With autogen/custom providers:
```bash
python tools/bulk_accounts.py --csv emails.csv \
  --containers zju.edu.cn=mail-zju-edu-cn
```

Notes:
- In many universities, both students and teachers share the same email suffix (e.g., `@zju.edu.cn`). You don’t need to distinguish roles; use the same domain for all recipients.
- Real external providers like `gmail.com` and `outlook.com` already exist in B29; you can generate or import accounts for them directly.

## 9) Logging and record verification

- Tail recent logs for a provider and grep by recipient or tokens:
```bash
docker logs --since 5m mail-163-netease | egrep -i "message-id|status=sent|Saved|INBOX|lmtp|to=<user@163.com>"
```
- Check Postfix queue if needed:
```bash
docker exec -it mail-qq-tencent postqueue -p
```

## 10) Extending with custom domains

For classroom realism (e.g., `zju.edu.cn`, `tsinghua.edu.cn`, `pku.edu.cn`):
- Quick path: keep B29 DNS-first core as-is; use `tools/email_autogen.py` to spin additional providers (transport-map) with your chosen domains.
- Account provisioning: map the school domains to autogen containers via `--containers`, or use `--domain-map` to map to an existing B29 domain like `company.cn`.

If you need to permanently add a domain into the DNS-first B29 core, you’ll need to update `email_realistic.py` in:
- `configure_mail_servers()` to add the provider (name, domain, ASN, IPs, ports)
- `configure_dns_system()` to add A/MX, authoritative NS, and binding
- `configure_bgp_peering()` to transit-peer the new AS with an ISP

## 11) Capturing results for grading / reports

- Save batch results to a file:
```bash
./run_cross_tests.sh --pairs pairs.txt | tee batch_results.txt
```
- Record environment info:
```bash
docker-compose ps
birdc show protocols | grep BGP
```

---

This guide intentionally mirrors real-world mail routing and validation workflows while staying pragmatic for teaching and demonstrations.

## 12) DNS pre-heating and fallback (per-AS caches)

DNS lookups may transiently fail immediately after bring-up while BIND and caches warm up. In B29 we deploy per-AS local DNS caches for each provider (e.g., `10.200.0.53` for AS-200) so providers never depend on cross-AS reachability to `10.150.0.53`.

- Design
  - Each provider AS has a local cache at `10.{ASN}.0.53`.
  - These caches forward only the six mail zones to their authoritative NS: `qq.com.`, `163.com.`, `gmail.com.`, `outlook.com.`, `company.cn.`, `startup.net.`
  - The central cache `10.150.0.53` can also serve authoritative zones for the same domains as a fallback.

- Quick verification (per-AS caches)
```
# From QQ provider cache (AS-200):
docker exec as200h-dns-cache-10.200.0.53 nslookup -type=mx gmail.com 127.0.0.1
# From Gmail provider cache (AS-202):
docker exec as202h-dns-cache-10.202.0.53 nslookup -type=mx qq.com 127.0.0.1
```

- Quick verification (central cache authoritative)
```
# MX must resolve for all six mail domains
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx 163.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx outlook.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx company.cn
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx startup.net
```

- Troubleshooting SERVFAIL
  - Validate zone files: `named-checkzone <zone> /etc/bind/zones/<zone>.zone`
  - Ensure records use FQDNs (avoid `$ORIGIN`/`@` if unsure about context).
  - Restart named after fixes: `service named restart`
  - Re-try the MX queries above.
