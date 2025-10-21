# B29 Email (DNS-first)

A realistic multi-ISP, multi-IX email system using DNS-based MX routing with a Roundcube webmail frontend. This is the single source of truth for running and validating the B29 scenario.

- Internet Map: http://localhost:8080/map.html
- Roundcube: http://localhost:8082

## Status
- Clean, internally validated demo scenario (no ad-hoc hot patches).
- Deterministic classroom setup; demo-mode security (DKIM/DMARC/SPF not enforced).

## Requirements
- Linux host with Docker and docker-compose
- Python environment and repo root on PYTHONPATH

## Quick Start
```bash
# 1) Generate
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
PYTHONPATH=/home/parallels/seed-email-system:$PYTHONPATH \
  /home/parallels/miniconda3/envs/seed-emulator/bin/python email_realistic.py arm

# 2) Start
cd output
docker-compose up -d
cd ..

# 3) Accounts + Roundcube (http://localhost:8082)
./manage_roundcube.sh accounts
./manage_roundcube.sh start
```

## Quick Verify
- DNS MX from AS-150 cache
```bash
cd output
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx qq.com
docker exec as150h-dns-cache-10.150.0.53 nslookup -type=mx gmail.com
cd ..
```

- Cross-domain (examples)
```bash
# QQ -> Gmail
printf "Subject: QQ->Gmail\n\nHi\n" | docker exec -i mail-qq-tencent sendmail user@gmail.com
# Outlook -> Company
printf "Subject: Outlook->Company\n\nHi\n" | docker exec -i mail-outlook-microsoft sendmail admin@company.cn
# Startup -> 163
printf "Subject: Startup->163\n\nHi\n" | docker exec -i mail-startup-selfhosted sendmail user@163.com
```

- Check delivery logs (look for Saved/status=sent)
```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns
for f in \
  output/mail-gmail-google-data/mail-logs/mail.log \
  output/mail-company-aliyun-data/mail-logs/mail.log \
  output/mail-163-netease-data/mail-logs/mail.log
{ do echo "=== $f ==="; [ -f "$f" ] && grep -E "Saved|status=sent" "$f" | tail -n 20 || echo missing; echo; }; done
```

- Optional: disable milters at runtime for deterministic tests
```bash
cd output
for c in mail-qq-tencent mail-163-netease mail-gmail-google mail-outlook-microsoft mail-company-aliyun mail-startup-selfhosted; do
  docker exec "$c" sh -c "postconf -e smtpd_milters= && postconf -e non_smtpd_milters= && postconf -e milter_default_action=accept && postfix reload" || true
done
cd ..
```

- Optional: full 30-flow matrix (see inline snippet below)
```bash
cd /home/parallels/seed-email-system/examples/internet/B29_email_dns/output
containers=(mail-qq-tencent mail-163-netease mail-gmail-google mail-outlook-microsoft mail-company-aliyun mail-startup-selfhosted)
domains=(qq.com 163.com gmail.com outlook.com company.cn startup.net)
ok=0; fail=0; total=0
for i in 0 1 2 3 4 5; do
  for j in 0 1 2 3 4 5; do
    if [ "$i" -ne "$j" ]; then
      total=$((total+1))
      from_c=${containers[$i]}; from_d=${domains[$i]}; from_addr="user@$from_d"
      to_c=${containers[$j]}; to_d=${domains[$j]}; to_addr="user@$to_d"
      printf "Subject: %s->%s\nTo: %s\nFrom: %s\n\nHi\n" "$from_d" "$to_d" "$to_addr" "$from_addr" | docker exec -i "$from_c" sh -c "sendmail -t" || true
      delivered=0
      for k in 1 2 3 4 5 6 7 8 9 10 11 12; do
        if docker exec "$to_c" sh -c "grep -E \"(Saved|stored mail into mailbox .*INBOX|status=sent .* to=<$to_addr>)\" -n /var/log/mail/mail.log" >/dev/null 2>&1; then delivered=1; break; fi
        sleep 1
      done
      if [ "$delivered" -eq 1 ]; then echo "OK $from_d -> $to_d"; ok=$((ok+1)); else echo "FAIL $from_d -> $to_d"; fail=$((fail+1)); fi
    fi
  done
done
printf "SUMMARY: OK=%d FAIL=%d TOTAL=%d\n" "$ok" "$fail" "$total"
```

## Cleanup
```bash
./manage_roundcube.sh stop || true
cd output && docker-compose down && cd ..
```

## Notes
- Demo-only configuration. Do not use in production.
- Run a single internet-map example at a time to avoid resource/port conflicts.
