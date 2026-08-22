from __future__ import annotations

from ipaddress import ip_address
from typing import Optional

from seedemu.core import Node, Server, Service


_MANAGED_DNS_API = r'''#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


NAME_RE = re.compile(r'^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')
ID_RE = re.compile(r'^[A-Za-z0-9_.-]{1,128}$')


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def normalize(value, field='domain'):
    if not isinstance(value, str):
        raise ApiError(400, 'invalid_zone_request', '{} must be a DNS name'.format(field))
    name = value.strip().lower().rstrip('.')
    if not NAME_RE.fullmatch(name):
        raise ApiError(400, 'invalid_zone_request', '{} is invalid'.format(field))
    return name


def run(command, input_text=None, timeout=15):
    result = subprocess.run(command, input=input_text, text=True, capture_output=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError('{} failed: {}'.format(command[0],
                           (result.stderr or result.stdout).strip()))
    return result.stdout


def atomic_write(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ManagedZones:
    def __init__(self, root, master_address, secondary_address, key_file, role):
        self.root = Path(root)
        self.master_address = master_address
        self.secondary_address = secondary_address
        self.key_file = key_file
        self.role = role
        self.zone_dir = self.root / 'zones'
        self.conf_dir = self.root / 'includes'
        self.record_dir = self.root / 'records'
        for directory in (self.zone_dir, self.conf_dir, self.record_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def zone_path(self, domain):
        return self.zone_dir / ('db.' + domain)

    def conf_path(self, domain):
        return self.conf_dir / (domain + '.conf')

    def create(self, payload):
        domain = normalize(payload.get('domain') if isinstance(payload, dict) else None)
        nameservers = payload.get('nameservers', [])
        expected = ['ns1.seedemu-dns.net.', 'ns2.seedemu-dns.net.']
        supplied = sorted({str(item.get('name', '')).lower() if isinstance(item, dict)
                           else str(item).lower() for item in nameservers})
        if supplied != sorted(expected):
            raise ApiError(400, 'invalid_zone_request', 'unexpected managed nameservers')
        zone_path = self.zone_path(domain)
        changed = not self.conf_path(domain).exists()
        if changed:
            if self.role == 'master':
                serial = int(time.time())
                zone = """$TTL 300
$ORIGIN {domain}.
@ IN SOA ns1.seedemu-dns.net. hostmaster.{domain}. ({serial} 30 15 604800 30)
@ IN NS ns1.seedemu-dns.net.
@ IN NS ns2.seedemu-dns.net.
""".format(domain=domain, serial=serial)
                atomic_write(zone_path, zone)
                run(['named-checkzone', domain, str(zone_path)])
                config = ('zone "{0}" {{ type master; file "{1}"; notify yes; '
                          'also-notify {{ {2} key "managed-transfer"; }}; allow-transfer {{ key "managed-transfer"; }}; '
                          'allow-update {{ key "managed-update"; }}; }};\n').format(
                              domain, zone_path, self.secondary_address)
            else:
                config = ('zone "{0}" {{ type slave; masters {{ {1} key "managed-transfer"; }}; '
                          'file "{2}"; }};\n').format(domain, self.master_address, zone_path)
            atomic_write(self.conf_path(domain), config)
            aggregate = ''.join(
                'include "{}";\n'.format(path)
                for path in sorted(self.conf_dir.glob('*.conf'))
            )
            atomic_write(self.root / 'managed-zones.conf', aggregate)
            run(['named-checkconf'])
            run(['rndc', 'reconfig'])
        return {'domain': domain, 'status': 'ready', 'changed': changed}

    def update(self, domain_value, record_id, payload):
        domain = normalize(domain_value)
        if self.role != 'master' or not self.zone_path(domain).exists():
            raise ApiError(404, 'zone_not_found', 'managed zone does not exist')
        if not ID_RE.fullmatch(record_id):
            raise ApiError(400, 'invalid_record', 'record_id is invalid')
        owner = normalize(payload.get('name'), 'name')
        if owner != domain and not owner.endswith('.' + domain):
            raise ApiError(400, 'invalid_record', 'record is outside managed zone')
        record_type = str(payload.get('record_type', '')).upper()
        if record_type not in ('A', 'AAAA', 'CNAME'):
            raise ApiError(400, 'invalid_record', 'unsupported record type')
        ttl, value = payload.get('ttl'), str(payload.get('value', '')).strip()
        if not isinstance(ttl, int) or ttl < 0 or ttl > 2147483647 or not value:
            raise ApiError(400, 'invalid_record', 'invalid TTL or value')
        old_path = self.record_dir / (domain + '--' + record_id + '.json')
        old = json.loads(old_path.read_text()) if old_path.exists() else None
        commands = ['server 127.0.0.1', 'zone ' + domain]
        if old:
            commands.append('update delete {} {}'.format(old['name'], old['record_type']))
        commands.extend(['update delete {} {}'.format(owner, record_type),
                         'update add {} {} {} {}'.format(owner, ttl, record_type, value), 'send'])
        run(['nsupdate', '-k', self.key_file], '\n'.join(commands) + '\n')
        record = {'record_id': record_id, 'domain': domain, 'name': owner,
                  'record_type': record_type, 'ttl': ttl, 'value': value}
        atomic_write(old_path, json.dumps(record, sort_keys=True) + '\n')
        return dict(record, status='ready')

    def delete(self, domain_value, record_id, payload):
        domain = normalize(domain_value)
        path = self.record_dir / (domain + '--' + record_id + '.json')
        if not path.exists():
            return {'domain': domain, 'record_id': record_id, 'status': 'absent'}
        old = json.loads(path.read_text())
        commands = ['server 127.0.0.1', 'zone ' + domain,
                    'update delete {} {}'.format(old['name'], old['record_type']), 'send']
        run(['nsupdate', '-k', self.key_file], '\n'.join(commands) + '\n')
        path.unlink()
        return {'domain': domain, 'record_id': record_id, 'status': 'absent'}


class Handler(BaseHTTPRequestHandler):
    zones = None
    def log_message(self, fmt, *args):
        print('[managed-dns] ' + fmt % args, flush=True)
    def reply(self, status, payload):
        body = json.dumps(payload, separators=(',', ':')).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
        except (ValueError, json.JSONDecodeError) as error:
            raise ApiError(400, 'invalid_json', 'request body must be valid JSON') from error
    def route(self):
        parts = [unquote(part) for part in self.path.split('?')[0].split('/') if part]
        if parts == ['health']: return ('health', None, None)
        if parts == ['v1', 'zones']: return ('zones', None, None)
        if len(parts) == 5 and parts[:2] == ['v1', 'zones'] and parts[3] == 'records':
            return ('record', parts[2], parts[4])
        raise ApiError(404, 'not_found', 'route not found')
    def dispatch(self, method):
        try:
            kind, domain, record_id = self.route()
            if method == 'GET' and kind == 'health': result = {'status': 'ok'}
            elif method == 'POST' and kind == 'zones': result = self.zones.create(self.body())
            elif method == 'PUT' and kind == 'record': result = self.zones.update(domain, record_id, self.body())
            elif method == 'DELETE' and kind == 'record': result = self.zones.delete(domain, record_id, self.body())
            else: raise ApiError(405, 'method_not_allowed', 'method not allowed')
            self.reply(200, result)
        except ApiError as error: self.reply(error.status, {'error': {'code': error.code, 'message': error.message}})
        except Exception as error: self.reply(500, {'error': {'code': 'provisioning_failed', 'message': str(error)}})
    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_PUT(self): self.dispatch('PUT')
    def do_DELETE(self): self.dispatch('DELETE')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=8054)
    parser.add_argument('--root', required=True); parser.add_argument('--master', required=True)
    parser.add_argument('--secondary', required=True); parser.add_argument('--key-file', required=True)
    parser.add_argument('--role', choices=('master', 'secondary'), required=True)
    args = parser.parse_args(); Handler.zones = ManagedZones(args.root, args.master, args.secondary, args.key_file, args.role)
    ThreadingHTTPServer(('0.0.0.0', args.port), Handler).serve_forever()


if __name__ == '__main__': main()
'''


_UPDATE_KEY = 'key "managed-update" { algorithm hmac-sha256; secret "YWdlbnQtbWFuYWdlZC11cGRhdGUta2V5"; };\n'
_TRANSFER_KEY = 'key "managed-transfer" { algorithm hmac-sha256; secret "YWdlbnQtbWFuYWdlZC10cmFuc2Zlci1rZXk="; };\n'


class AgentManagedDnsServer(Server):
    """BIND master/secondary for zones created at runtime."""

    def __init__(self):
        super().__init__()
        self.__role: Optional[str] = None
        self.__master: Optional[str] = None
        self.__secondary: Optional[str] = None

    def setMaster(self, secondary: str) -> AgentManagedDnsServer:
        self.__role, self.__secondary = "master", str(ip_address(secondary))
        return self

    def setSecondary(self, master: str) -> AgentManagedDnsServer:
        self.__role, self.__master = "secondary", str(ip_address(master))
        return self

    def install(self, node: Node):
        assert self.__role is not None, "managed DNS role is not configured"
        root = "/var/lib/seedemu-managed-dns"
        node.addSoftware("bind9 bind9-utils bind9-dnsutils python3")
        node.setFile("/etc/bind/managed-transfer.key", _TRANSFER_KEY)
        node.setFile("/etc/bind/named.conf", 'include "/etc/bind/named.conf.options";\ninclude "/etc/bind/named.conf.local";\n')
        node.setFile("/etc/bind/named.conf.options", 'options { directory "/var/cache/bind"; recursion no; dnssec-validation no; allow-query { any; }; };\n')
        if self.__role == "master":
            node.setFile("/etc/bind/managed-update.key", _UPDATE_KEY)
            node.setFile("/etc/bind/named.conf.local", 'include "/etc/bind/managed-update.key";\ninclude "/etc/bind/managed-transfer.key";\ninclude "/var/lib/seedemu-managed-dns/provider.conf";\ninclude "/var/lib/seedemu-managed-dns/managed-zones.conf";\n')
            node.setFile(root + "/managed-zones.conf", "")
            node.setFile(root + "/provider.conf", 'zone "seedemu-dns.net" { type master; file "/var/lib/seedemu-managed-dns/zones/db.seedemu-dns.net"; notify yes; also-notify { %s; }; allow-transfer { key "managed-transfer"; }; };\n' % self.__secondary)
            node.setFile(root + "/zones/db.seedemu-dns.net", '$TTL 300\n$ORIGIN seedemu-dns.net.\n@ IN SOA ns1.seedemu-dns.net. hostmaster.seedemu-dns.net. (1 30 15 604800 30)\n@ IN NS ns1.seedemu-dns.net.\n@ IN NS ns2.seedemu-dns.net.\nns1 IN A 10.161.0.53\nns2 IN A 10.162.0.53\n')
            node.setFile(root + "/api.py", _MANAGED_DNS_API)
            node.appendStartCommand("mkdir -p {0}/zones {0}/includes {0}/records && chown -R bind:bind {0}".format(root))
            node.appendStartCommand("service named start")
            node.appendStartCommand("python3 {0}/api.py --root {0} --master 127.0.0.1 --secondary {1} --key-file /etc/bind/managed-update.key --role master".format(root, self.__secondary), fork=True)
        else:
            node.setFile("/etc/bind/named.conf.local", 'include "/etc/bind/managed-transfer.key";\ninclude "/var/lib/seedemu-managed-dns/provider.conf";\ninclude "/var/lib/seedemu-managed-dns/managed-zones.conf";\n')
            node.setFile(root + "/managed-zones.conf", "")
            node.setFile(root + "/provider.conf", 'zone "seedemu-dns.net" { type slave; masters { %s key "managed-transfer"; }; file "/var/lib/seedemu-managed-dns/zones/db.seedemu-dns.net"; };\n' % self.__master)
            node.setFile(root + "/api.py", _MANAGED_DNS_API)
            node.appendStartCommand("mkdir -p {} && chown -R bind:bind {}".format(root, root))
            node.appendStartCommand("service named start")
            node.appendStartCommand("python3 {0}/api.py --root {0} --master {1} --secondary 127.0.0.1 --key-file /dev/null --role secondary".format(root, self.__master), fork=True)

    def print(self, indent: int) -> str:
        return " " * indent + "AgentManagedDnsServer({})\n".format(self.__role)


class AgentManagedDnsService(Service):
    def __init__(self):
        super().__init__(); self.addDependency("Base", False, False)
    def getName(self) -> str: return "AgentManagedDnsService"
    def _createServer(self) -> AgentManagedDnsServer: return AgentManagedDnsServer()
    def print(self, indent: int) -> str: return " " * indent + "AgentManagedDnsService\n"
