#!/usr/bin/env python3
# encoding: utf-8
"""
B29 Bulk Account Utility
- Create many accounts quickly across B29 providers.
- Supports CSV import (student/teacher IDs) and synthetic generation.

CSV formats (header optional):
  - Simple emails (preferred):
      email
      alice@zju.edu.cn
      bob@zju.edu.cn
  - IDs with optional type/display/domain:
      id,type,display,domain
      3230101234,student,张三,zju.edu.cn
      T01,teacher,李老师,zju.edu.cn

Notes:
- Domains must map to existing B29 providers (qq.com, 163.com, gmail.com, outlook.com, company.cn, startup.net)
  unless you provide a mapping (e.g., zju.edu.cn => company.cn) with --domain-map.
- Requires B29 stack up (containers running) and uses docker exec to add accounts.

Usage examples:
  # Generate 100 student accounts on company.cn and 20 teachers on startup.net
  python tools/bulk_accounts.py --generate --count 100 --prefix stu --domain company.cn \
      --extra --count 20 --prefix tea --domain startup.net

  # Import CSV and map zju.edu.cn to company.cn
  python tools/bulk_accounts.py --csv class.csv --domain-map zju.edu.cn=company.cn

  # Dry-run
  python tools/bulk_accounts.py --csv class.csv --domain-map zju.edu.cn=company.cn --dry-run
"""

import argparse
import csv
import os
import shlex
import subprocess
from typing import Dict, List, Tuple

B29_DOMAIN_CONTAINER = {
    'qq.com': 'mail-qq-tencent',
    '163.com': 'mail-163-netease',
    'gmail.com': 'mail-gmail-google',
    'outlook.com': 'mail-outlook-microsoft',
    'company.cn': 'mail-company-aliyun',
    'startup.net': 'mail-startup-selfhosted',
}


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def parse_domain_map(arg: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not arg:
        return mapping
    for item in arg.split(','):
        item = item.strip()
        if not item:
            continue
        if '=' not in item:
            raise SystemExit(f"Invalid domain-map entry: {item}")
        src, dst = item.split('=', 1)
        mapping[src.strip()] = dst.strip()
    return mapping


def parse_container_map(arg: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not arg:
        return mapping
    for item in arg.split(','):
        item = item.strip()
        if not item:
            continue
        if '=' not in item:
            raise SystemExit(f"Invalid containers entry: {item}")
        dom, ctn = item.split('=', 1)
        mapping[dom.strip()] = ctn.strip()
    return mapping


def container_exists(name: str) -> bool:
    rc, out, _ = run_cmd(['bash', '-lc', f"docker ps --format '{{{{.Names}}}}' | grep -Fx {shlex.quote(name)} || true"])
    return (out.strip() == name)


def resolve_container(domain: str, domain_map: Dict[str, str], container_map: Dict[str, str]) -> Tuple[str, str]:
    # map domain if needed
    mapped = domain_map.get(domain, domain)
    # explicit container mapping wins
    if mapped in container_map:
        return mapped, container_map[mapped]
    # known B29 mapping
    ctn = B29_DOMAIN_CONTAINER.get(mapped)
    if ctn:
        return mapped, ctn
    # autogen fallback: mail-<safe(domain)>
    safe = mapped.replace('.', '-').replace('_', '-')
    fallback = f"mail-{safe}"
    if container_exists(fallback):
        return mapped, fallback
    raise SystemExit(f"No container for domain '{domain}' (mapped: '{mapped}'). Provide --domain-map or --containers.")


def add_account(email: str, password: str, domain_map: Dict[str, str], container_map: Dict[str, str], dry_run: bool = False) -> bool:
    # email must be local to one of the containers' domains (possibly mapped)
    if '@' not in email:
        raise ValueError(f"invalid email: {email}")
    local, domain = email.split('@', 1)
    mapped_domain, container = resolve_container(domain, domain_map, container_map)
    # If mapping applied, rewrite email
    rewritten = f"{local}@{mapped_domain}"
    if dry_run:
        print(f"DRY: create {rewritten} on {container}")
        return True
    cmd = [
        'docker', 'exec', '-i', container,
        'bash', '-lc', f"printf {shlex.quote(password + '\n' + password + '\n')} | setup email add {shlex.quote(rewritten)}"
    ]
    rc, out, err = run_cmd(cmd)
    if rc == 0:
        print(f"OK: {rewritten} on {container}")
        return True
    else:
        print(f"ERR: {rewritten} on {container} -> rc={rc} out={out} err={err}")
        return False


def gen_accounts(prefix: str, count: int, start: int, domain: str, pad: int = 0) -> List[str]:
    def fmt(i: int) -> str:
        s = str(i)
        return s.zfill(pad) if pad > 0 else s
    return [f"{prefix}{fmt(i)}@{domain}" for i in range(start, start + count)]


def load_csv(path: str, default_domain: str, student_domain: str, teacher_domain: str) -> List[str]:
    emails: List[str] = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        r = csv.reader(f)
        rows = list(r)
        # skip header if present
        if rows and rows[0] and rows[0][0] and rows[0][0].lower() in ('id', '学号', '编号', 'email', '邮箱'):
            rows = rows[1:]
        for row in rows:
            if not row:
                continue
            # if any cell looks like an email, take it directly
            cells = [c.strip() for c in row if c and c.strip()]
            direct = next((c for c in cells if '@' in c), None)
            if direct:
                emails.append(direct)
                continue

            # otherwise, construct from id and domain selection
            sid = (cells[0] if cells else '').strip()
            # try to pick explicit domain if present in 2nd-4th columns
            dom_candidates = []
            if len(row) > 3 and row[3].strip():
                dom_candidates.append(row[3].strip())
            if len(row) > 2 and row[2].strip():
                dom_candidates.append(row[2].strip())
            if len(row) > 1 and row[1].strip():
                dom_candidates.append(row[1].strip())
            dom = ''
            dom = next((d for d in dom_candidates if '.' in d), '')
            if not dom:
                # fallback: default domain if provided
                if default_domain:
                    dom = default_domain
                else:
                    # legacy fallback by type or ID prefix
                    typ = (row[1] or '').strip().lower() if len(row) > 1 else ''
                    if sid.startswith('T') or typ in ('teacher', 't', '老师'):
                        dom = teacher_domain
                    else:
                        dom = student_domain
            if sid and dom:
                emails.append(f"{sid}@{dom}")
    return emails


def main():
    ap = argparse.ArgumentParser(description='B29 bulk account helper')
    ap.add_argument('--csv', help='CSV file path for import')
    ap.add_argument('--domain-map', help='Mapping foo.edu.cn=company.cn,bar.edu.cn=startup.net')
    ap.add_argument('--generate', action='store_true', help='Generate synthetic accounts')
    ap.add_argument('--prefix', default='user', help='Prefix for generated accounts')
    ap.add_argument('--count', type=int, default=0, help='Number of generated accounts')
    ap.add_argument('--start', type=int, default=1, help='Start index for generated accounts')
    ap.add_argument('--domain', default='company.cn', help='Domain for generated accounts')
    ap.add_argument('--pad', type=int, default=0, help='Zero-pad width for numeric suffix when generating (e.g., 4)')
    ap.add_argument('--default-domain', default='', help='Default domain when CSV row has no domain or email-only list is IDs (overrides student/teacher)')
    ap.add_argument('--student-domain', default='company.cn', help='Legacy default when CSV row has no domain')
    ap.add_argument('--teacher-domain', default='startup.net', help='Legacy default when CSV row has no domain')
    ap.add_argument('--password', default='password123')
    ap.add_argument('--containers', help='Explicit domain=container mappings, comma-separated (for autogen/custom)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    domain_map = parse_domain_map(args.domain_map or '')
    container_map = parse_container_map(args.containers or '')

    targets: List[str] = []
    if args.csv:
        targets.extend(load_csv(args.csv, args.default_domain, args.student_domain, args.teacher_domain))
    if args.generate and args.count > 0:
        targets.extend(gen_accounts(args.prefix, args.count, args.start, args.domain, args.pad))
    if not targets:
        raise SystemExit('no accounts to create; use --csv or --generate with --count')

    ok = 0; fail = 0
    for email in targets:
        if add_account(email, args.password, domain_map, container_map, dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1
    print(f"Summary: created={ok} failed={fail} total={ok+fail}")
    if fail:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
