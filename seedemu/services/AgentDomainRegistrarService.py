from __future__ import annotations

import json
from typing import Optional

from seedemu.core import Node, Server, Service


_DEFAULT_POLICY = {
    "supported_tlds": ["com"],
    "reserved_names": [],
    "max_years": 10,
    "default_nameservers": [],
}


_REGISTRAR_API = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import sqlite3
from threading import Event, Thread
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    registrant_id TEXT NOT NULL,
    nameservers TEXT NOT NULL,
    zone_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    CHECK (status IN ('pending_dns', 'active', 'provisioning_failed',
                      'expired', 'redemption')),
    CHECK (zone_status IN ('pending', 'active', 'failed'))
);
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    request_fingerprint TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    registrant_id TEXT NOT NULL,
    years INTEGER NOT NULL,
    status TEXT NOT NULL,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(domain_name) REFERENCES domains(name),
    CHECK (status IN ('provisioning', 'active', 'provisioning_failed'))
);
CREATE TABLE IF NOT EXISTS managed_records (
    id TEXT PRIMARY KEY,
    domain_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    record_type TEXT NOT NULL,
    ttl INTEGER NOT NULL,
    value TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(domain_name) REFERENCES domains(name),
    UNIQUE(domain_name, owner_name, record_type),
    CHECK (status IN ('pending', 'active', 'deleting', 'failed'))
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT,
    CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    domain_name TEXT,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def now():
    return datetime.now(timezone.utc).isoformat()


def add_years(timestamp, years):
    value = datetime.fromisoformat(timestamp)
    try:
        return value.replace(year=value.year + years).isoformat()
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years).isoformat()


def normalize_domain(value):
    if not isinstance(value, str):
        raise ApiError(400, 'invalid_registration_request', 'domain must be a string')
    value = value.strip().rstrip('.').lower()
    try:
        labels = [label.encode('idna').decode('ascii') for label in value.split('.')]
    except UnicodeError as error:
        raise ApiError(400, 'invalid_registration_request', 'invalid IDNA domain') from error
    if len(labels) < 2 or any(
        not label or len(label) > 63 or not label.replace('-', '').isalnum()
        or label.startswith('-') or label.endswith('-') for label in labels
    ):
        raise ApiError(400, 'invalid_registration_request', 'invalid domain name')
    normalized = '.'.join(labels) + '.'
    if len(normalized.encode('ascii')) > 254:
        raise ApiError(400, 'invalid_registration_request', 'domain name is too long')
    return normalized


def normalize_owner(value, domain):
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, 'invalid_record', 'record name is required')
    value = value.strip().lower()
    if value == '@':
        return domain
    if not value.endswith('.'):
        value = value + '.' if value.endswith(domain.rstrip('.')) else value + '.' + domain
    normalized = normalize_domain(value)
    if normalized != domain and not normalized.endswith('.' + domain):
        raise ApiError(400, 'invalid_record', 'record name must be inside the managed zone')
    return normalized


def load_policy(path):
    with open(path, encoding='utf-8') as policy_file:
        policy = json.load(policy_file)
    tlds = policy.get('supported_tlds')
    if not isinstance(tlds, list) or not tlds:
        raise ValueError('policy must contain at least one supported TLD')
    normalized_tlds = []
    for value in tlds:
        if not isinstance(value, str) or not value.strip().strip('.'):
            raise ValueError('supported TLDs must be non-empty strings')
        normalized_tlds.append(value.strip().strip('.').lower())
    max_years = policy.get('max_years', 10)
    if not isinstance(max_years, int) or not 1 <= max_years <= 100:
        raise ValueError('max_years must be an integer from 1 to 100')
    reserved = policy.get('reserved_names', [])
    if not isinstance(reserved, list) or not all(isinstance(v, str) for v in reserved):
        raise ValueError('reserved_names must be a list of strings')
    nameservers = policy.get('default_nameservers', [])
    if not isinstance(nameservers, list) or not all(isinstance(v, dict) for v in nameservers):
        raise ValueError('default_nameservers must be a list of objects')
    return {
        'supported_tlds': sorted(set(normalized_tlds)),
        'reserved_names': {v.strip().rstrip('.').lower() for v in reserved},
        'max_years': max_years,
        'default_nameservers': nameservers,
    }


class Registrar:
    def __init__(self, database, policy):
        self.database = database
        self.policy = policy
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA busy_timeout = 5000')
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute('PRAGMA journal_mode = WAL')
            connection.execute(
                "UPDATE outbox SET status = 'pending' WHERE status = 'processing'"
            )

    def validate_registration(self, domain, registrant_id, years):
        domain = normalize_domain(domain)
        if domain.rstrip('.').split('.')[-1] not in self.policy['supported_tlds']:
            raise ApiError(400, 'unsupported_tld', 'top-level domain is not supported')
        if domain.rstrip('.') in self.policy['reserved_names']:
            raise ApiError(400, 'invalid_registration_request', 'domain is reserved')
        if not isinstance(registrant_id, str) or not registrant_id.strip():
            raise ApiError(400, 'invalid_registration_request', 'registrant_id is required')
        if not isinstance(years, int) or isinstance(years, bool) or not 1 <= years <= self.policy['max_years']:
            raise ApiError(
                400,
                'invalid_registration_request',
                'years must be between 1 and {}'.format(self.policy['max_years']),
            )
        return domain, registrant_id.strip(), years

    def availability(self, name):
        domain = normalize_domain(name)
        if domain.rstrip('.').split('.')[-1] not in self.policy['supported_tlds']:
            raise ApiError(400, 'unsupported_tld', 'top-level domain is not supported')
        if domain.rstrip('.') in self.policy['reserved_names']:
            return {'domain': domain, 'available': False, 'status': 'reserved', 'checked_at': now()}
        with self.connect() as connection:
            row = connection.execute('SELECT status FROM domains WHERE name = ?', (domain,)).fetchone()
        return {
            'domain': domain,
            'available': row is None,
            'status': 'available' if row is None else row['status'],
            'checked_at': now(),
        }

    def list_domains(self):
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT name, status, registrant_id, nameservers, zone_status, '
                'created_at, expires_at, updated_at FROM domains ORDER BY name'
            ).fetchall()
        return [self._domain_result(row) for row in rows]

    def get_domain(self, name):
        domain = normalize_domain(name)
        with self.connect() as connection:
            row = connection.execute(
                'SELECT name, status, registrant_id, nameservers, zone_status, '
                'created_at, expires_at, updated_at FROM domains WHERE name = ?',
                (domain,),
            ).fetchone()
        return self._domain_result(row) if row else None

    @staticmethod
    def _domain_result(row):
        result = dict(row)
        result['nameservers'] = json.loads(result['nameservers'])
        return result

    def get_order(self, order_id, connection=None):
        owns_connection = connection is None
        connection = connection or self.connect()
        try:
            row = connection.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
            return dict(row) if row else None
        finally:
            if owns_connection:
                connection.close()

    def purchase(self, request, idempotency_key):
        if not isinstance(request, dict):
            raise ApiError(400, 'invalid_registration_request', 'request must be an object')
        connection = self.connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            domain, registrant, years = self.validate_registration(
                request.get('domain', ''),
                request.get('registrant_id', ''),
                request.get('years', 1),
            )
            canonical = json.dumps(
                {'domain': domain, 'registrant_id': registrant, 'years': years},
                sort_keys=True,
                separators=(',', ':'),
            )
            fingerprint = sha256(canonical.encode()).hexdigest()
            previous = connection.execute(
                'SELECT id, request_fingerprint FROM orders WHERE idempotency_key = ?',
                (idempotency_key,),
            ).fetchone()
            if previous:
                if previous['request_fingerprint'] != fingerprint:
                    raise ApiError(
                        409, 'idempotency_key_conflict',
                        'Idempotency-Key was already used for another request'
                    )
                result = self.get_order(previous['id'], connection)
                connection.commit()
                return result, False

            timestamp = now()
            expires_at = add_years(timestamp, years)
            nameservers = self.policy['default_nameservers']
            try:
                connection.execute(
                    'INSERT INTO domains '
                    '(name, status, registrant_id, nameservers, zone_status, '
                    'created_at, expires_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        domain, 'pending_dns', registrant,
                        json.dumps(nameservers, separators=(',', ':')),
                        'pending', timestamp, expires_at, timestamp,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ApiError(409, 'domain_not_available', 'domain is not available') from error

            order_id = 'ord-' + uuid4().hex
            connection.execute(
                'INSERT INTO orders '
                '(id, idempotency_key, request_fingerprint, domain_name, registrant_id, '
                'years, status, failure_reason, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)',
                (
                    order_id, idempotency_key, fingerprint, domain, registrant,
                    years, 'provisioning', timestamp, timestamp,
                ),
            )
            self._enqueue(
                connection, 'domain.provision_requested', domain,
                {
                    'order_id': order_id,
                    'domain': domain,
                    'registrant_id': registrant,
                    'nameservers': nameservers,
                },
                timestamp,
            )
            self._audit(
                connection, registrant, 'domain.purchase_requested', domain,
                {'order_id': order_id}, timestamp,
            )
            result = self.get_order(order_id, connection)
            connection.commit()
            return result, True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_records(self, domain_name, registrant_id):
        domain = self._authorize_domain(domain_name, registrant_id, require_active=True)
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT id, owner_name, record_type, ttl, value, status, updated_at '
                'FROM managed_records WHERE domain_name = ? ORDER BY owner_name, record_type',
                (domain,),
            ).fetchall()
        return [dict(row) for row in rows]

    def put_record(self, domain_name, record_id, request):
        registrant = request.get('registrant_id', '') if isinstance(request, dict) else ''
        domain = self._authorize_domain(domain_name, registrant, require_active=True)
        if not isinstance(record_id, str) or not record_id.strip() or len(record_id) > 128:
            raise ApiError(400, 'invalid_record', 'record_id is required')
        record_type = str(request.get('record_type', '')).upper()
        if record_type not in {'A', 'AAAA', 'CNAME'}:
            raise ApiError(400, 'invalid_record', 'record_type must be A, AAAA, or CNAME')
        owner = normalize_owner(request.get('name', request.get('host', '')), domain)
        ttl = request.get('ttl', 300)
        value = request.get('value')
        if not isinstance(ttl, int) or isinstance(ttl, bool) or not 0 <= ttl <= 2147483647:
            raise ApiError(400, 'invalid_record', 'ttl is out of range')
        if not isinstance(value, str) or not value.strip() or any(c in value for c in '\r\n'):
            raise ApiError(400, 'invalid_record', 'record value is required')
        value = value.strip()
        if record_type in {'A', 'AAAA'}:
            try:
                address = ipaddress.ip_address(value)
            except ValueError as error:
                raise ApiError(400, 'invalid_record', 'record value must be an IP address') from error
            if (record_type == 'A' and address.version != 4) or (
                record_type == 'AAAA' and address.version != 6
            ):
                raise ApiError(400, 'invalid_record', 'record value has the wrong IP version')
            value = str(address)
        elif record_type == 'CNAME':
            value = normalize_domain(value)
        timestamp = now()
        connection = self.connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            by_id = connection.execute(
                'SELECT * FROM managed_records WHERE id = ?', (record_id,)
            ).fetchone()
            if by_id and by_id['domain_name'] != domain:
                raise ApiError(409, 'record_conflict', 'record_id belongs to another domain')
            if by_id and by_id['status'] in {'pending', 'active'} and all(
                (
                    by_id['owner_name'] == owner,
                    by_id['record_type'] == record_type,
                    by_id['ttl'] == ttl,
                    by_id['value'] == value,
                )
            ):
                connection.commit()
                return {
                    key: by_id[key]
                    for key in (
                        'id', 'owner_name', 'record_type', 'ttl', 'value',
                        'status', 'updated_at'
                    )
                }
            existing = connection.execute(
                'SELECT id FROM managed_records '
                'WHERE domain_name = ? AND owner_name = ? AND record_type = ?',
                (domain, owner, record_type),
            ).fetchone()
            if existing and existing['id'] != record_id:
                raise ApiError(409, 'record_conflict', 'RRset already has another record_id')
            conflicting_type = connection.execute(
                'SELECT record_type FROM managed_records '
                'WHERE domain_name = ? AND owner_name = ? AND id != ? '
                "AND (record_type = 'CNAME' OR ? = 'CNAME') LIMIT 1",
                (domain, owner, record_id, record_type),
            ).fetchone()
            if conflicting_type:
                raise ApiError(409, 'record_conflict', 'CNAME conflicts with another RRset')
            connection.execute(
                'INSERT INTO managed_records '
                '(id, domain_name, owner_name, record_type, ttl, value, status, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(id) DO UPDATE SET owner_name = excluded.owner_name, '
                'record_type = excluded.record_type, ttl = excluded.ttl, '
                'value = excluded.value, status = excluded.status, updated_at = excluded.updated_at',
                (record_id, domain, owner, record_type, ttl, value, 'pending', timestamp),
            )
            self._enqueue(
                connection, 'dns.record_upsert_requested', record_id,
                {
                    'record_id': record_id, 'domain': domain, 'name': owner,
                    'record_type': record_type, 'ttl': ttl, 'value': value,
                },
                timestamp,
            )
            self._audit(
                connection, registrant.strip(), 'dns.record_upsert_requested', domain,
                {'record_id': record_id}, timestamp,
            )
            row = connection.execute(
                'SELECT id, owner_name, record_type, ttl, value, status, updated_at '
                'FROM managed_records WHERE id = ?', (record_id,)
            ).fetchone()
            connection.commit()
            return dict(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_record(self, domain_name, record_id, registrant_id):
        domain = self._authorize_domain(domain_name, registrant_id, require_active=True)
        timestamp = now()
        connection = self.connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute(
                'SELECT * FROM managed_records WHERE id = ? AND domain_name = ?',
                (record_id, domain),
            ).fetchone()
            if not row:
                raise ApiError(404, 'record_not_found', 'record does not exist')
            if row['status'] == 'deleting':
                connection.commit()
                return
            connection.execute(
                "UPDATE managed_records SET status = 'deleting', updated_at = ? WHERE id = ?",
                (timestamp, record_id),
            )
            self._enqueue(
                connection, 'dns.record_delete_requested', record_id,
                {
                    'record_id': record_id, 'domain': domain,
                    'name': row['owner_name'], 'record_type': row['record_type'],
                },
                timestamp,
            )
            self._audit(
                connection, registrant_id.strip(), 'dns.record_delete_requested', domain,
                {'record_id': record_id}, timestamp,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _authorize_domain(self, name, registrant_id, require_active):
        if not isinstance(registrant_id, str) or not registrant_id.strip():
            raise ApiError(400, 'invalid_registration_request', 'registrant_id is required')
        domain = self.get_domain(name)
        if not domain:
            raise ApiError(404, 'domain_not_found', 'domain does not exist')
        if domain['registrant_id'] != registrant_id.strip():
            raise ApiError(403, 'not_domain_owner', 'registrant does not own this domain')
        if require_active and domain['status'] != 'active':
            raise ApiError(409, 'domain_not_active', 'domain is not active')
        return domain['name']

    @staticmethod
    def _enqueue(connection, event_type, aggregate_id, payload, timestamp):
        connection.execute(
            'INSERT INTO outbox '
            '(event_type, aggregate_id, payload, created_at) VALUES (?, ?, ?, ?)',
            (event_type, aggregate_id, json.dumps(payload, separators=(',', ':')), timestamp),
        )

    @staticmethod
    def _audit(connection, actor_id, action, domain, details, timestamp):
        connection.execute(
            'INSERT INTO audit_events '
            '(actor_id, action, domain_name, details, created_at) VALUES (?, ?, ?, ?, ?)',
            (actor_id, action, domain, json.dumps(details, separators=(',', ':')), timestamp),
        )


def request_json(method, url, payload, timeout=75):
    body = json.dumps(payload, separators=(',', ':')).encode()
    request = Request(url, data=body, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            return json.loads(data) if data else {}
    except HTTPError as error:
        message = error.read().decode(errors='replace')
        raise RuntimeError('provisioner returned HTTP {}: {}'.format(error.code, message)) from error
    except URLError as error:
        raise RuntimeError('provisioner request failed: {}'.format(error.reason)) from error


class OutboxWorker:
    def __init__(self, registrar, provisioner_url, max_attempts=5):
        self.registrar = registrar
        self.provisioner_url = provisioner_url.rstrip('/') if provisioner_url else None
        self.max_attempts = max_attempts

    def process_once(self):
        connection = self.registrar.connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute(
                "SELECT * FROM outbox WHERE status = 'pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if not row:
                connection.commit()
                return False
            connection.execute(
                "UPDATE outbox SET status = 'processing', attempts = attempts + 1 WHERE id = ?",
                (row['id'],),
            )
            connection.commit()
        finally:
            connection.close()

        try:
            if not self.provisioner_url:
                raise RuntimeError('DNS provisioner is not configured')
            payload = json.loads(row['payload'])
            event_type = row['event_type']
            if event_type == 'domain.provision_requested':
                request_json('POST', self.provisioner_url + '/v1/zones', payload)
            elif event_type == 'dns.record_upsert_requested':
                request_json(
                    'PUT',
                    self.provisioner_url + '/v1/zones/{}/records/{}'.format(
                        quote(payload['domain'], safe=''), quote(payload['record_id'], safe='')
                    ),
                    payload,
                )
            elif event_type == 'dns.record_delete_requested':
                request_json(
                    'DELETE',
                    self.provisioner_url + '/v1/zones/{}/records/{}'.format(
                        quote(payload['domain'], safe=''), quote(payload['record_id'], safe='')
                    ),
                    payload,
                )
            else:
                raise RuntimeError('unsupported outbox event {}'.format(event_type))
            self._complete(row, payload)
        except Exception as error:
            self._fail(row, str(error))
        return True

    def _complete(self, row, payload):
        timestamp = now()
        with self.registrar.connect() as connection:
            connection.execute(
                "UPDATE outbox SET status = 'completed', last_error = NULL, processed_at = ? "
                'WHERE id = ?', (timestamp, row['id'])
            )
            if row['event_type'] == 'domain.provision_requested':
                connection.execute(
                    "UPDATE domains SET status = 'active', zone_status = 'active', "
                    'updated_at = ?, version = version + 1 WHERE name = ?',
                    (timestamp, payload['domain']),
                )
                connection.execute(
                    "UPDATE orders SET status = 'active', failure_reason = NULL, updated_at = ? "
                    'WHERE id = ?', (timestamp, payload['order_id'])
                )
            elif row['event_type'] == 'dns.record_upsert_requested':
                connection.execute(
                    "UPDATE managed_records SET status = 'active', updated_at = ? WHERE id = ?",
                    (timestamp, payload['record_id']),
                )
            elif row['event_type'] == 'dns.record_delete_requested':
                connection.execute('DELETE FROM managed_records WHERE id = ?', (payload['record_id'],))

    def _fail(self, row, message):
        attempts = row['attempts'] + 1
        terminal = attempts >= self.max_attempts
        timestamp = now()
        payload = json.loads(row['payload'])
        with self.registrar.connect() as connection:
            connection.execute(
                'UPDATE outbox SET status = ?, last_error = ?, processed_at = ? WHERE id = ?',
                ('failed' if terminal else 'pending', message[:2048],
                 timestamp if terminal else None, row['id']),
            )
            if terminal and row['event_type'] == 'domain.provision_requested':
                connection.execute(
                    "UPDATE domains SET status = 'provisioning_failed', zone_status = 'failed', "
                    'updated_at = ?, version = version + 1 WHERE name = ?',
                    (timestamp, payload['domain']),
                )
                connection.execute(
                    "UPDATE orders SET status = 'provisioning_failed', failure_reason = ?, "
                    'updated_at = ? WHERE id = ?',
                    (message[:2048], timestamp, payload['order_id']),
                )
            elif terminal and row['event_type'].startswith('dns.record_'):
                connection.execute(
                    "UPDATE managed_records SET status = 'failed', updated_at = ? WHERE id = ?",
                    (timestamp, payload['record_id']),
                )


class Handler(BaseHTTPRequestHandler):
    registrar = None
    server_version = 'SeedEmuAgentRegistrar/2.0'

    def reply(self, status, payload):
        body = json.dumps(payload, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error(self, error):
        self.reply(error.status, {'error': {'code': error.code, 'message': error.message}})

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError as error:
            raise ApiError(400, 'invalid_json', 'invalid Content-Length') from error
        if length <= 0 or length > 65536:
            raise ApiError(400, 'invalid_json', 'request body must be between 1 and 65536 bytes')
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ApiError(400, 'invalid_json', 'request body is not valid JSON') from error
        if not isinstance(value, dict):
            raise ApiError(400, 'invalid_json', 'request body must be an object')
        return value

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == '/health':
                self.reply(200, {'status': 'ok', 'database': 'ready',
                                 'service': 'seedemu-agent-domain-registrar'})
                return
            if path == '/v1/domains':
                self.reply(200, {'domains': self.registrar.list_domains()})
                return
            if path.startswith('/v1/orders/'):
                order = self.registrar.get_order(unquote(path[len('/v1/orders/'):]))
                if not order:
                    raise ApiError(404, 'order_not_found', 'order does not exist')
                self.reply(200, order)
                return
            if path.startswith('/v1/domains/'):
                suffix = unquote(path[len('/v1/domains/'):])
                if suffix.endswith('/availability'):
                    self.reply(200, self.registrar.availability(suffix[:-len('/availability')]))
                    return
                if suffix.endswith('/records'):
                    domain = suffix[:-len('/records')]
                    registrant = self.headers.get('X-Registrant-ID', '')
                    self.reply(200, {'records': self.registrar.list_records(domain, registrant)})
                    return
                domain = self.registrar.get_domain(suffix)
                if not domain:
                    raise ApiError(404, 'domain_not_found', 'domain does not exist')
                self.reply(200, domain)
                return
            raise ApiError(404, 'not_found', 'endpoint does not exist')
        except ApiError as error:
            self.error(error)
        except Exception as error:
            self.error(ApiError(500, 'internal_error', str(error)))

    def do_POST(self):
        try:
            if urlparse(self.path).path != '/v1/purchases':
                raise ApiError(404, 'not_found', 'endpoint does not exist')
            idempotency_key = self.headers.get('Idempotency-Key', '').strip()
            if not idempotency_key or len(idempotency_key) > 256:
                raise ApiError(400, 'missing_idempotency_key', 'valid Idempotency-Key is required')
            order, created = self.registrar.purchase(self.read_json(), idempotency_key)
            self.reply(201 if created else 200, order)
        except ApiError as error:
            self.error(error)
        except Exception as error:
            self.error(ApiError(500, 'internal_error', str(error)))

    def do_PUT(self):
        try:
            domain, record_id = self._record_path()
            self.reply(202, self.registrar.put_record(domain, record_id, self.read_json()))
        except ApiError as error:
            self.error(error)
        except Exception as error:
            self.error(ApiError(500, 'internal_error', str(error)))

    def do_DELETE(self):
        try:
            domain, record_id = self._record_path()
            registrant = self.headers.get('X-Registrant-ID', '').strip()
            self.registrar.delete_record(domain, record_id, registrant)
            self.reply(202, {'record_id': record_id, 'status': 'deleting'})
        except ApiError as error:
            self.error(error)
        except Exception as error:
            self.error(ApiError(500, 'internal_error', str(error)))

    def _record_path(self):
        path = urlparse(self.path).path
        prefix = '/v1/domains/'
        marker = '/records/'
        if not path.startswith(prefix) or marker not in path[len(prefix):]:
            raise ApiError(404, 'not_found', 'endpoint does not exist')
        domain, record_id = path[len(prefix):].split(marker, 1)
        if not domain or not record_id or '/' in record_id:
            raise ApiError(404, 'not_found', 'endpoint does not exist')
        return unquote(domain), unquote(record_id)

    def log_message(self, message, *args):
        print('%s - %s' % (self.address_string(), message % args), flush=True)


def worker_loop(worker, interval, stop):
    while not stop.is_set():
        worker.process_once()
        stop.wait(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--policy', required=True)
    parser.add_argument('--provisioner-url')
    parser.add_argument('--worker-interval', type=float, default=1.0)
    parser.add_argument('--max-provision-attempts', type=int, default=5)
    args = parser.parse_args()
    Handler.registrar = Registrar(args.database, load_policy(args.policy))
    stop = Event()
    thread = None
    if args.provisioner_url:
        worker = OutboxWorker(
            Handler.registrar, args.provisioner_url, args.max_provision_attempts
        )
        thread = Thread(
            target=worker_loop,
            args=(worker, args.worker_interval, stop),
            daemon=True,
        )
        thread.start()
    try:
        ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=2)


if __name__ == '__main__':
    main()
'''


class AgentDomainRegistrarServer(Server):
    """Offline registrar and managed-DNS control plane for agent emulations."""

    def __init__(self):
        super().__init__()
        self.__port = 8080
        self.__policy = json.dumps(_DEFAULT_POLICY, indent=2)
        self.__database_path = "/var/lib/seedemu-agent-registrar/registrar.db"
        self.__provisioner_url: Optional[str] = None
        self.__worker_interval = 1.0
        self.__max_provision_attempts = 5
        self.__dns_provisioner: Optional[Server] = None

    def setPort(self, port: int) -> AgentDomainRegistrarServer:
        assert 1 <= port <= 65535, "invalid registrar API port"
        self.__port = port
        return self

    def setPolicy(self, policy: str) -> AgentDomainRegistrarServer:
        parsed = json.loads(policy)
        assert isinstance(parsed.get("supported_tlds"), list), (
            "policy must contain supported_tlds"
        )
        self.__policy = json.dumps(parsed, indent=2)
        return self

    def setDatabasePath(self, path: str) -> AgentDomainRegistrarServer:
        assert path.startswith("/"), "database path must be absolute"
        self.__database_path = path
        return self

    def setProvisionerUrl(self, url: str) -> AgentDomainRegistrarServer:
        assert url.startswith("http://") or url.startswith("https://"), (
            "provisioner URL must use HTTP or HTTPS"
        )
        self.__provisioner_url = url.rstrip("/")
        return self

    def setWorkerInterval(self, seconds: float) -> AgentDomainRegistrarServer:
        assert seconds > 0, "worker interval must be positive"
        self.__worker_interval = seconds
        return self

    def setMaxProvisionAttempts(self, attempts: int) -> AgentDomainRegistrarServer:
        assert attempts >= 1, "max provision attempts must be positive"
        self.__max_provision_attempts = attempts
        return self

    def setDnsProvisioner(self, provisioner: Server) -> AgentDomainRegistrarServer:
        """Install a DNS provisioning sidecar on this same virtual node."""
        self.__dns_provisioner = provisioner
        return self

    def install(self, node: Node):
        app_dir = "/opt/seedemu-agent-registrar"
        policy_path = f"{app_dir}/policy.json"
        database_dir = self.__database_path.rsplit("/", 1)[0]

        node.addSoftware("python3")
        node.setFile(f"{app_dir}/registrar_api.py", _REGISTRAR_API)
        node.setFile(policy_path, self.__policy)
        node.appendStartCommand(f"mkdir -p {database_dir}")
        command = (
            "python3 {}/registrar_api.py --port {} --database {} --policy {} "
            "--worker-interval {} --max-provision-attempts {}"
        ).format(
            app_dir,
            self.__port,
            self.__database_path,
            policy_path,
            self.__worker_interval,
            self.__max_provision_attempts,
        )
        if self.__provisioner_url is not None:
            command += " --provisioner-url {}".format(self.__provisioner_url)
        node.appendStartCommand(command, fork=True)
        if self.__dns_provisioner is not None:
            self.__dns_provisioner.install(node)

    def print(self, indent: int) -> str:
        return " " * indent + "AgentDomainRegistrarServer\n"


class AgentDomainRegistrarService(Service):
    """Service layer for the agent-oriented registrar control plane."""

    def __init__(self):
        super().__init__()
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        return "AgentDomainRegistrarService"

    def _createServer(self) -> AgentDomainRegistrarServer:
        return AgentDomainRegistrarServer()

    def print(self, indent: int) -> str:
        return " " * indent + "AgentDomainRegistrarService\n"
