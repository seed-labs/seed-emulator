from __future__ import annotations

from ipaddress import ip_address
from typing import Iterable, Optional

from seedemu.core import Node, Server, Service


_PROVISIONER_API = r'''#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen


DOMAIN_RE = re.compile(r'^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?\.?$')


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def normalize_name(value, field):
    if not isinstance(value, str):
        raise ApiError(400, 'invalid_delegation_request', '{} must be a DNS name'.format(field))
    name = value.strip().lower().rstrip('.')
    if not DOMAIN_RE.fullmatch(name):
        raise ApiError(400, 'invalid_delegation_request', '{} is invalid'.format(field))
    return name + '.'


def parse_request(payload, parent_zone):
    if not isinstance(payload, dict):
        raise ApiError(400, 'invalid_delegation_request', 'request body must be an object')
    domain = normalize_name(payload.get('domain'), 'domain')
    if not domain.endswith('.' + parent_zone) or domain == parent_zone:
        raise ApiError(400, 'invalid_delegation_request', 'domain is outside the parent zone')
    raw_nameservers = payload.get('nameservers')
    if not isinstance(raw_nameservers, list) or len(raw_nameservers) < 2:
        raise ApiError(400, 'invalid_delegation_request', 'at least two nameservers are required')
    nameservers = []
    for item in raw_nameservers:
        value = item.get('name') if isinstance(item, dict) else item
        name = normalize_name(value, 'nameserver')
        if name not in nameservers:
            nameservers.append(name)
    if len(nameservers) < 2:
        raise ApiError(400, 'invalid_delegation_request', 'at least two unique nameservers are required')
    return domain, nameservers


def run_command(command, input_text=None, timeout=10):
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError('{} failed: {}'.format(command[0], detail))
    return result.stdout


def query_records(server, name, record_type):
    output = run_command(
        [
            'dig', '+noall', '+answer', '+authority', '+time=1', '+tries=1',
            '@' + server, name, record_type,
        ],
        timeout=3,
    )
    records = []
    for line in output.splitlines():
        fields = line.split()
        if (
            len(fields) >= 5
            and fields[2].upper() == 'IN'
            and fields[3].upper() == record_type.upper()
        ):
            records.append(' '.join(fields[4:]).lower())
    return sorted(records)


class ParentDelegationProvisioner:
    def __init__(self, parent_zone, master, secondaries, verify_timeout,
                 managed_master, managed_secondaries, managed_port, parent_key):
        self.parent_zone = normalize_name(parent_zone, 'parent_zone')
        self.master = master
        self.secondaries = list(secondaries)
        if not self.secondaries:
            raise ValueError('at least one parent DNS secondary is required')
        if len(self.secondaries) != len(set(self.secondaries)):
            raise ValueError('parent DNS secondary addresses must be unique')
        if self.master in self.secondaries:
            raise ValueError('parent DNS master and secondaries must be distinct')
        self.verify_timeout = verify_timeout
        self.managed_master = managed_master
        self.managed_secondaries = list(managed_secondaries)
        self.managed_port = managed_port
        self.parent_key = parent_key

    def request(self, server, method, path, payload):
        body = json.dumps(payload, separators=(',', ':')).encode()
        request = Request('http://{}:{}{}'.format(server, self.managed_port, path),
                          data=body, method=method,
                          headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=10) as response:
                data = response.read()
                return json.loads(data) if data else {}
        except HTTPError as error:
            raise RuntimeError('managed DNS {} returned HTTP {}: {}'.format(
                server, error.code, error.read().decode(errors='replace'))) from error
        except URLError as error:
            raise RuntimeError('managed DNS {} is unreachable: {}'.format(server, error.reason)) from error

    def provision(self, payload):
        domain, nameservers = parse_request(payload, self.parent_zone)
        expected = sorted(nameservers)
        changed = query_records(self.master, domain, 'NS') != expected
        if changed:
            commands = [
                'server {}'.format(self.master),
                'zone {}'.format(self.parent_zone),
                'update delete {} NS'.format(domain),
            ]
            commands.extend(
                'update add {} 300 NS {}'.format(domain, nameserver)
                for nameserver in nameservers
            )
            commands.append('send')
            run_command(['nsupdate', '-k', self.parent_key], '\n'.join(commands) + '\n')

        deadline = time.monotonic() + self.verify_timeout
        master_records = []
        while time.monotonic() < deadline:
            master_records = query_records(self.master, domain, 'NS')
            secondary_records = {
                server: query_records(server, domain, 'NS')
                for server in self.secondaries
            }
            if master_records == expected and all(
                records == expected for records in secondary_records.values()
            ):
                master_soa = query_records(self.master, self.parent_zone, 'SOA')
                secondary_soa = {
                    server: query_records(server, self.parent_zone, 'SOA')
                    for server in self.secondaries
                }
                if master_soa and all(
                    records == master_soa for records in secondary_soa.values()
                ):
                    return {
                        'domain': domain.rstrip('.'),
                        'status': 'delegated',
                        'changed': changed,
                        'nameservers': nameservers,
                        'master': self.master,
                        'secondaries': self.secondaries,
                        'soa': master_soa[0],
                    }
            time.sleep(0.5)
        raise ApiError(
            503,
            'delegation_not_converged',
            'parent master and all secondaries did not converge before the timeout',
        )

    def provision_zone(self, payload):
        domain, _ = parse_request(payload, self.parent_zone)
        for server in self.managed_secondaries:
            self.request(server, 'POST', '/v1/zones', payload)
        master_result = self.request(self.managed_master, 'POST', '/v1/zones', payload)
        delegation = self.provision(payload)
        self.verify_managed(domain)
        return {'domain': domain.rstrip('.'), 'status': 'active',
                'changed': master_result.get('changed', False),
                'delegation': delegation}

    def verify_managed(self, domain):
        expected_ns = ['ns1.seedemu-dns.net.', 'ns2.seedemu-dns.net.']
        deadline = time.monotonic() + self.verify_timeout
        while time.monotonic() < deadline:
            master_ns = query_records(self.managed_master, domain, 'NS')
            master_soa = query_records(self.managed_master, domain, 'SOA')
            secondary_values = [
                (query_records(server, domain, 'NS'), query_records(server, domain, 'SOA'))
                for server in self.managed_secondaries
            ]
            if (master_ns == expected_ns and master_soa and
                    all(ns == expected_ns and soa == master_soa for ns, soa in secondary_values)):
                return
            time.sleep(0.5)
        raise ApiError(503, 'managed_zone_not_converged',
                       'managed DNS master and secondary did not converge')

    def record(self, method, domain, record_id, payload):
        domain = normalize_name(domain, 'domain')
        path = '/v1/zones/{}/records/{}'.format(
            quote(domain.rstrip('.'), safe=''), quote(record_id, safe=''))
        result = self.request(self.managed_master, method, path, payload)
        name = payload.get('name')
        record_type = payload.get('record_type')
        if method == 'DELETE':
            deadline = time.monotonic() + self.verify_timeout
            while time.monotonic() < deadline:
                if all(not query_records(server, name, record_type)
                       for server in [self.managed_master] + self.managed_secondaries):
                    return result
                time.sleep(0.5)
        else:
            expected = [str(payload.get('value')).lower().rstrip('.') +
                        ('.' if str(record_type).upper() == 'CNAME' else '')]
            deadline = time.monotonic() + self.verify_timeout
            while time.monotonic() < deadline:
                if all(query_records(server, name, record_type) == expected
                       for server in [self.managed_master] + self.managed_secondaries):
                    return result
                time.sleep(0.5)
        raise ApiError(503, 'record_not_converged',
                       'managed DNS record did not converge')


class Handler(BaseHTTPRequestHandler):
    provisioner = None
    server_version = 'SeedEmuParentDelegationProvisioner/1.0'

    def log_message(self, fmt, *args):
        print('[parent-delegation] ' + fmt % args, flush=True)

    def reply(self, status, payload):
        body = json.dumps(payload, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            return json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as error:
            raise ApiError(400, 'invalid_json', 'request body must be valid JSON') from error

    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'status': 'ok', 'service': 'parent-delegation-provisioner'})
        else:
            self.reply(404, {'error': {'code': 'not_found', 'message': 'route not found'}})

    def do_POST(self):
        try:
            if self.path == '/v1/delegations':
                result = self.provisioner.provision(self.read_json())
            elif self.path == '/v1/zones':
                result = self.provisioner.provision_zone(self.read_json())
            else:
                raise ApiError(404, 'not_found', 'route not found')
            self.reply(200, result)
        except ApiError as error:
            self.reply(error.status, {'error': {'code': error.code, 'message': error.message}})
        except Exception as error:
            self.reply(500, {'error': {'code': 'provisioning_failed', 'message': str(error)}})

    def dispatch_record(self, method):
        try:
            parts = [unquote(part) for part in self.path.split('?')[0].split('/') if part]
            if len(parts) != 5 or parts[:2] != ['v1', 'zones'] or parts[3] != 'records':
                raise ApiError(404, 'not_found', 'route not found')
            self.reply(200, self.provisioner.record(method, parts[2], parts[4], self.read_json()))
        except ApiError as error:
            self.reply(error.status, {'error': {'code': error.code, 'message': error.message}})
        except Exception as error:
            self.reply(500, {'error': {'code': 'provisioning_failed', 'message': str(error)}})

    def do_PUT(self):
        self.dispatch_record('PUT')

    def do_DELETE(self):
        self.dispatch_record('DELETE')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8053)
    parser.add_argument('--parent-zone', default='com.')
    parser.add_argument('--master', required=True)
    parser.add_argument('--secondary', action='append', required=True)
    parser.add_argument('--verify-timeout', type=float, default=30)
    parser.add_argument('--managed-master', required=True)
    parser.add_argument('--managed-secondary', action='append', required=True)
    parser.add_argument('--managed-port', type=int, default=8054)
    parser.add_argument('--parent-key', required=True)
    args = parser.parse_args()
    Handler.provisioner = ParentDelegationProvisioner(
        args.parent_zone, args.master, args.secondary, args.verify_timeout,
        args.managed_master, args.managed_secondary, args.managed_port, args.parent_key
    )
    ThreadingHTTPServer(('0.0.0.0', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
'''


class AgentDnsProvisioningServer(Server):
    """Parent-zone delegation provisioner for the B02a control node."""

    def __init__(self):
        super().__init__()
        self.__port = 8053
        self.__parent_zone = "com."
        self.__master: Optional[str] = None
        self.__secondaries: list[str] = []
        self.__verify_timeout = 30.0
        self.__managed_master: Optional[str] = None
        self.__managed_secondaries: list[str] = []
        self.__managed_port = 8054
        self.__parent_key = "/etc/bind/agent-parent-update.key"

    def setPort(self, port: int) -> AgentDnsProvisioningServer:
        assert 1 <= port <= 65535, "invalid provisioner API port"
        self.__port = port
        return self

    def setParentServers(
        self, master: str, secondaries: Iterable[str]
    ) -> AgentDnsProvisioningServer:
        self.__master = str(ip_address(master))
        assert not isinstance(secondaries, str), "secondaries must be an iterable of addresses"
        self.__secondaries = [str(ip_address(server)) for server in secondaries]
        assert self.__secondaries, "at least one parent DNS secondary is required"
        assert len(self.__secondaries) == len(set(self.__secondaries)), (
            "parent DNS secondary addresses must be unique"
        )
        assert self.__master not in self.__secondaries, (
            "parent DNS master and secondaries must be distinct"
        )
        return self

    def setVerifyTimeout(self, seconds: float) -> AgentDnsProvisioningServer:
        assert seconds > 0, "verification timeout must be positive"
        self.__verify_timeout = seconds
        return self

    def setManagedServers(
        self, master: str, secondaries: Iterable[str], port: int = 8054
    ) -> AgentDnsProvisioningServer:
        self.__managed_master = str(ip_address(master))
        self.__managed_secondaries = [str(ip_address(server)) for server in secondaries]
        assert self.__managed_secondaries, "at least one managed DNS secondary is required"
        assert self.__managed_master not in self.__managed_secondaries, "managed DNS servers must be distinct"
        assert 1 <= port <= 65535, "invalid managed DNS API port"
        self.__managed_port = port
        return self

    def install(self, node: Node):
        assert self.__master is not None, "parent DNS master is not configured"
        assert self.__secondaries, "parent DNS secondaries are not configured"
        assert self.__managed_master is not None, "managed DNS master is not configured"
        app_dir = "/opt/seedemu-agent-dns-provisioner"
        node.addSoftware("python3 curl bind9-dnsutils")
        node.setFile(self.__parent_key, 'key "agent-parent-update" { algorithm hmac-sha256; secret "YWdlbnQtcGFyZW50LXVwZGF0ZS1rZXk="; };\n')
        node.setFile(f"{app_dir}/provisioner_api.py", _PROVISIONER_API)
        node.appendStartCommand(
            "python3 {}/provisioner_api.py --port {} --parent-zone {} "
            "--master {} {} --verify-timeout {} --managed-master {} {} --managed-port {} --parent-key {}".format(
                app_dir,
                self.__port,
                self.__parent_zone,
                self.__master,
                " ".join(
                    "--secondary {}".format(server)
                    for server in self.__secondaries
                ),
                self.__verify_timeout,
                self.__managed_master,
                " ".join("--managed-secondary {}".format(server) for server in self.__managed_secondaries),
                self.__managed_port,
                self.__parent_key,
            ),
            fork=True,
        )

    def print(self, indent: int) -> str:
        return " " * indent + "AgentDnsProvisioningServer\n"


class AgentDnsProvisioningService(Service):
    """Service layer for idempotent parent-zone delegation updates."""

    def __init__(self):
        super().__init__()
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        return "AgentDnsProvisioningService"

    def _createServer(self) -> AgentDnsProvisioningServer:
        return AgentDnsProvisioningServer()

    def print(self, indent: int) -> str:
        return " " * indent + "AgentDnsProvisioningService\n"
