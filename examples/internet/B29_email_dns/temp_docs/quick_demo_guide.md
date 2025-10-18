# B29 Quick Demo Guide (DNS-first, multi-provider)

This guide is for fast in-class demos and reviews. It shows how to start the system, test cross-domain mail in CLI and Roundcube, run automation, and point to the key code where logic is implemented.

- Internet Map: http://localhost:8080/map.html
- Roundcube: http://localhost:8082

## 1) Start and prepare

```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns

# Generate (use python)
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  python email_realistic.py arm

# Start
cd output && docker-compose up -d && cd ..

# Create demo accounts for all providers
./manage_roundcube.sh accounts

# Start Roundcube
./manage_roundcube.sh start
```

Accounts for login (password: `password123`):
- user@qq.com
- user@163.com
- user@gmail.com
- user@outlook.com
- admin@company.cn
- founder@startup.net

## 2) DNS check (MX)

Use the local DNS cache (AS-150):
```bash
cd output
# MX lookup (gmail/qq)
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
cd ..
```
Tip: the mail containers are configured to use per-AS local DNS (e.g., `10.200.0.53` for AS-200), so DNS lookups work without crossing AS boundaries.

## 3) CLI email tests (manual)

- QQ → Gmail:
```bash
printf "Subject: QQ->Gmail $(date +%s)\n\nBody\n" | docker exec -i mail-qq-tencent sendmail user@gmail.com
# Receiver logs
docker logs --since 3m mail-gmail-google | egrep -i "to=<user@gmail.com>|Saved|INBOX|lmtp"
```

- Gmail → QQ:
```bash
printf "Subject: Gmail->QQ $(date +%s)\n\nBody\n" | docker exec -i mail-gmail-google sendmail user@qq.com
# Receiver logs
docker logs --since 3m mail-qq-tencent | egrep -i "to=<user@qq.com>|Saved|INBOX|lmtp"
```

If you see `postdrop: unable to look up public/pickup`, wait ~5–10s after container start and retry; ensure accounts exist (use `./manage_roundcube.sh accounts`).

## 4) Roundcube webmail

- Open http://localhost:8082
- Login with any of the accounts above
- Send messages cross-domain and verify inboxes

## 5) Batch cross-domain automation

```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
./run_cross_tests.sh

# Custom pairs
cat > pairs.txt << 'EOF'
user@qq.com user@gmail.com
user@gmail.com user@qq.com
user@163.com user@outlook.com
admin@company.cn founder@startup.net
EOF
./run_cross_tests.sh --pairs pairs.txt | tee batch_results.txt
```

The script ensures recipients exist and polls logs (~20s) for LMTP/Saved evidence.

## 6) Bulk accounts (CSV / generate)

Tool: `tools/bulk_accounts.py`.

Examples:
```bash
# Generate 100 student accounts on company.cn (zero-padded)
python tools/bulk_accounts.py --generate --count 100 --prefix stu --domain company.cn --pad 4

# Import email-only CSV (preferred)
python tools/bulk_accounts.py --csv tools/emails.csv

# IDs-only CSV with a default domain
python tools/bulk_accounts.py --csv tools/ids.csv --default-domain zju.edu.cn

# Map real domain to internal provider for testing
python tools/bulk_accounts.py --csv tools/sample_class.csv --domain-map zju.edu.cn=company.cn

# For custom/autogen containers
python tools/bulk_accounts.py --csv tools/emails.csv --containers zju.edu.cn=mail-zju-edu-cn
```
Notes:
- Real domains like `gmail.com`/`outlook.com` exist in B29; you can import/generate accounts directly.
- In universities, students and teachers often share the same suffix (e.g., `@zju.edu.cn`), so no need to split roles.

## 7) Optional: fast transport-map network (no DNS)

Tool: `tools/email_autogen.py`.
```bash
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  python tools/email_autogen.py --platform arm --domains seedemail.net corporate.local smallbiz.org --asn-start 150
cd tools/output && docker-compose up -d
```
Create accounts and send with the same `sendmail` flow, then:
```bash
cd tools/output && docker-compose down
```

## 8) Code pointers and logic

- `email_realistic.py` (build system):
  - `run()` orchestrates layers and compiles to `output/`.
  - `configure_mail_servers()` defines six providers and ports.
  - `configure_dns_system()` sets up Root/TLD/authoritative DNS and adds per-AS local caches (`10.{ASN}.0.53`).
- `seedemu/services/EmailService.py` (container attach):
  - DNS-first Postfix config via template: `relayhost =`, `smtp_host_lookup = dns`, `smtp_dns_support_level = enabled`.
  - Per-provider `dns:` injection to compose (`10.{ASN}.0.53`).
- `DomainNameService` / `DomainNameCachingService`:
  - Authoritative zones for each email domain (A/MX), and caching resolvers.

## 9) Practical notes

- Allow 2–10 seconds for DNS and mail services to warm up on cold start.
- Use receiver container logs to verify delivery (`Saved`, `INBOX`, `lmtp`).
- Use `postqueue -p` inside sender to inspect deferred messages.
- Avoid running multiple examples simultaneously to prevent compose/network conflicts.
