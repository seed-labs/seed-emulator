from __future__ import annotations

"""Reusable composition of Loom, Namingo Registry/RDDS, and TLD publication."""

import base64
import hashlib
import ipaddress
import secrets
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

from seedemu.core import Binding, Emulator, Filter, Node
from seedemu.layers import Base
from seedemu.services.DomainNameService import DomainNameService
from .LoomRegistrarService import (
    LOOM_DATABASE_NAME,
    LOOM_DATABASE_PASSWORD,
    LOOM_DATABASE_USERNAME,
    LOOM_WEBAUTHN_SECRET,
    LoomRegistrarServer,
    LoomRegistrarService,
    LoomWebTlsCredentials,
)
from .NamingoRegistrarService import (
    NamingoRegistrarServer,
    NamingoRegistrarService,
)
from .NamingoRegistryService import (
    NamingoRegistryServer,
    NamingoRegistryService,
)
from .RegistrarIdentity import RegistrarIdentity


DEFAULT_RDDS_DATABASE_USERNAME = "loom_rdds"
DEFAULT_RDDS_DATABASE_PASSWORD = "seedemu-loom-rdds"


@dataclass(frozen=True)
class RegistrationNode:
    """A service vnode and its physical host."""

    vnode: str
    asn: int
    node_name: str
    address: str


@dataclass(frozen=True)
class RegistryDeployment:
    node: RegistrationNode
    service: NamingoRegistryService
    server: NamingoRegistryServer
    epp_hostname: str
    epp_port: int
    tlds: tuple[str, ...]
    whois_host: str
    rdap_url: str


@dataclass(frozen=True)
class LoomRegistrarDeployment:
    identity: RegistrarIdentity
    node: RegistrationNode
    service: LoomRegistrarService
    server: LoomRegistrarServer
    web_tls: LoomWebTlsCredentials
    registrar_url: str
    database: str


@dataclass(frozen=True)
class RegistrarRddsDeployment:
    registrar_id: str
    node: RegistrationNode
    service: NamingoRegistrarService
    server: NamingoRegistrarServer


@dataclass(frozen=True)
class DomainRegistrationDeployment:
    registries: dict[str, RegistryDeployment]
    registrars: dict[str, LoomRegistrarDeployment]
    registrar_rdds: dict[str, RegistrarRddsDeployment]


@dataclass(frozen=True)
class EppConnection:
    registrar_id: str
    registry_id: str
    clid: str
    password: str
    prefix: str
    tld: str
    prices: dict[str, dict[int, float]]
    probe_domain: str


class DomainRegistrationSystem:
    """Builder/facade for relationships among domain-registration services.

    This is intentionally not a ``Service``: existing service layers continue
    to own installation, while this object owns shared credentials, bilateral
    configuration, bindings, and cross-service validation.
    """

    def __init__(
        self,
        emulator: Emulator,
        base: Base,
        dns: DomainNameService,
        registrar_identity: RegistrarIdentity | None = None,
    ):
        self._emulator = emulator
        self._base = base
        self._dns = dns
        self._default_registrar_identity = registrar_identity
        self._registries: dict[str, RegistryDeployment] = {}
        self._registrars: dict[str, LoomRegistrarDeployment] = {}
        self._registrar_rdds: dict[str, RegistrarRddsDeployment] = {}
        self._epp_connections: list[EppConnection] = []
        self._bindings: dict[str, RegistrationNode] = {}
        self._layers: list[object] = []
        self._installed = False

    @staticmethod
    def _validate_id(value: str, kind: str) -> None:
        assert 1 <= len(value) <= 32 and value.replace("-", "").replace("_", "").isalnum(), (
            "invalid {} id".format(kind)
        )

    def _bind(self, node: RegistrationNode) -> None:
        assert node.vnode not in self._bindings, "registration vnode is already configured"
        ipaddress.ip_address(node.address)
        self._base.getAutonomousSystem(node.asn).getHost(node.node_name)
        self._bindings[node.vnode] = node

    def addRegistry(
        self,
        registry_id: str,
        node: RegistrationNode,
        *,
        epp_hostname: str,
        tlds: Iterable[str],
        whois_host: str,
        rdap_url: str,
        epp_port: int = 700,
    ) -> RegistryDeployment:
        """Create one EPP Registry and its Registry-authority RDDS."""
        self._validate_id(registry_id, "Registry")
        assert registry_id not in self._registries, "Registry id is already configured"
        assert all(
            (item.node.asn, item.node.node_name) != (node.asn, node.node_name)
            for item in self._registries.values()
        ), "each Namingo Registry requires a separate physical node"
        normalized_tlds = tuple(dict.fromkeys(tld.lower().strip(".") for tld in tlds))
        assert normalized_tlds, "at least one Registry TLD is required"
        self._bind(node)
        service = NamingoRegistryService()
        server = service.install(node.vnode)
        server.setEppEndpoint(epp_hostname, epp_port).setTlds(list(normalized_tlds)) \
            .setRddsEndpoints(whois_host, rdap_url).enableWhois().enableRdap() \
            .exposeRddsToAgent()
        result = RegistryDeployment(
            node, service, server, epp_hostname, epp_port, normalized_tlds,
            whois_host, rdap_url,
        )
        self._registries[registry_id] = result
        self._layers.append(service)
        return result

    def addLoomRegistrar(
        self,
        registrar_id: str,
        node: RegistrationNode,
        *,
        identity: RegistrarIdentity | None = None,
        commit: str | None = None,
        database: str = LOOM_DATABASE_NAME,
        database_username: str = LOOM_DATABASE_USERNAME,
        database_password: str = LOOM_DATABASE_PASSWORD,
        webauthn_secret: str = LOOM_WEBAUTHN_SECRET,
    ) -> LoomRegistrarDeployment:
        """Create the customer-facing Registrar and business database."""
        self._validate_id(registrar_id, "Registrar")
        assert registrar_id not in self._registrars, "Registrar id is already configured"
        assert all(
            (item.node.asn, item.node.node_name) != (node.asn, node.node_name)
            for item in self._registrars.values()
        ), "each Loom Registrar requires a separate physical node"
        selected_identity = identity or self._default_registrar_identity
        assert selected_identity is not None, "Registrar identity is required"
        self._bind(node)
        web_tls = LoomRegistrarService.generateWebTlsCredentials(node.address)
        service = LoomRegistrarService()
        server = service.install(node.vnode)
        if commit is not None:
            server.setCommit(commit)
        server.configureDatabase(
            database, database_username, database_password
        ).configureEnvironment(
            identity=selected_identity, webauthn_secret=webauthn_secret
        ).setWebTls(web_tls.certificate, web_tls.private_key).initializeDatabase() \
            .createAdminUser()
        result = LoomRegistrarDeployment(
            identity=selected_identity,
            node=node,
            service=service,
            server=server,
            web_tls=web_tls,
            registrar_url="https://{}:443".format(node.address),
            database=database,
        )
        self._registrars[registrar_id] = result
        self._layers.append(service)
        return result

    def connectEpp(
        self,
        *,
        registrar_id: str,
        registry_id: str,
        clid: str | None = None,
        password: str | None = None,
        prefix: str | None = None,
        tld: str,
        prices: dict[str, dict[int, float]],
        probe_domain: str | None = None,
    ) -> None:
        """Declare one edge in the Registrar-to-Registry EPP graph."""
        assert registry_id in self._registries, "unknown Registry id"
        assert registrar_id in self._registrars, "unknown Registrar id"
        registry = self._registries[registry_id]
        normalized_tld = tld.lower().strip(".")
        assert normalized_tld in registry.tlds, (
            "Registrar EPP TLD is not served by this Registry"
        )
        existing_account = next((
            edge for edge in self._epp_connections
            if edge.registry_id == registry_id and edge.registrar_id == registrar_id
        ), None)
        if existing_account is not None:
            clid = clid or existing_account.clid
            password = password or existing_account.password
            prefix = prefix or existing_account.prefix
        else:
            clid = clid or registrar_id.lower()[:16]
            password = password or secrets.token_hex(8)
            prefix = prefix or hashlib.sha256(registrar_id.encode()).hexdigest()[:5].upper()
        probe_domain = probe_domain or "seedemu-epp-probe.{}".format(normalized_tld)
        for edge in self._epp_connections:
            if edge.registry_id == registry_id and edge.registrar_id == registrar_id:
                assert (edge.clid, edge.password, edge.prefix) == (clid, password, prefix), (
                    "one Registrar must reuse its Registry EPP account across TLDs"
                )
            assert not (
                edge.registry_id == registry_id
                and edge.registrar_id != registrar_id
                and edge.clid == clid
            ), "Registry EPP clid is already used by another Registrar"
        assert all(
            not (edge.registrar_id == registrar_id and edge.tld == normalized_tld)
            for edge in self._epp_connections
        ), "Registrar already has an EPP provider for this TLD"
        self._epp_connections.append(EppConnection(
            registrar_id, registry_id, clid, password, prefix,
            normalized_tld, prices, probe_domain,
        ))

    def addRegistrarRdds(
        self,
        rdds_id: str,
        registrar_id: str,
        node: RegistrationNode,
        *,
        database_username: str = DEFAULT_RDDS_DATABASE_USERNAME,
        database_password: str = DEFAULT_RDDS_DATABASE_PASSWORD,
        rdap_proxy_port: int = 80,
    ) -> RegistrarRddsDeployment:
        """Attach Registrar WHOIS/RDAP to Loom's business database."""
        self._validate_id(rdds_id, "Registrar RDDS")
        assert registrar_id in self._registrars, "unknown Registrar id"
        assert rdds_id not in self._registrar_rdds, "Registrar RDDS id is already configured"
        registrar = self._registrars[registrar_id]
        self._bind(node)
        colocated = (
            node.asn == registrar.node.asn
            and node.node_name == registrar.node.node_name
        )
        if colocated:
            assert rdap_proxy_port != 443, "RDAP proxy conflicts with Loom HTTPS"
            database_host = database_source = "127.0.0.1"
        else:
            database_host = registrar.node.address
            database_source = node.address
        registrar.server.addReadOnlyDatabaseUser(
            database_username,
            database_password,
            database_source,
            database=registrar.database,
        )
        service = NamingoRegistrarService()
        server = service.install(node.vnode)
        server.setBackend("loom").setExternalDatabase(
            host=database_host,
            port=3306,
            name=registrar.database,
            username=database_username,
            password=database_password,
        ).setIdentity(registrar.identity).enableWhois().enableRdap().setRdapProxyPort(
            rdap_proxy_port
        ).exposeRddsToAgent()
        result = RegistrarRddsDeployment(registrar_id, node, service, server)
        self._registrar_rdds[rdds_id] = result
        self._layers.append(service)
        return result

    def configureTldPublication(
        self,
        *,
        registry_id: str,
        zone: str,
        nameservers: dict[str, str],
        soa_contact: str,
        hidden_primary_ip: str,
        publisher_private_key: str,
        hidden_primary_host_key: str,
        public_secondary_ips: Iterable[str],
        static_records: Iterable[tuple[str, str, list[str]]] = (),
        interval_seconds: int = 30,
    ) -> None:
        """Connect Registry Zone Writer output to authoritative TLD DNS."""
        assert registry_id in self._registries, "unknown Registry id"
        registry = self._registries[registry_id]
        normalized_zone = zone.lower().strip(".")
        assert normalized_zone in registry.tlds, (
            "published zone is not served by this Registry"
        )
        registry.server.configureZoneWriter(
            nameservers, soa_contact, interval_seconds
        ).setZonePublisher(
            zone,
            hidden_primary_ip,
            publisher_private_key,
            hidden_primary_host_key,
            secondary_ips=list(public_secondary_ips),
        )
        for name, record_type, parameters in static_records:
            registry.server.addZoneWriterRecord(
                normalized_zone, name, record_type, parameters
            )

    @staticmethod
    def _relativeName(hostname: str, zone: str) -> str | None:
        """Return an in-zone hostname relative to its authoritative zone."""
        normalized_host = hostname.lower().rstrip(".")
        normalized_zone = zone.lower().rstrip(".")
        suffix = ".{}".format(normalized_zone)
        if not normalized_host.endswith(suffix):
            return None
        relative = normalized_host[:-len(suffix)]
        assert relative, "service hostname cannot equal the TLD apex"
        return relative

    def _serviceRecords(
        self, registry_id: str, zone: str
    ) -> list[tuple[str, str, list[str]]]:
        """Derive public service records from composed Registry/RDDS nodes."""
        registry = self._registries[registry_id]
        registry_rdap_host = urlsplit(registry.rdap_url).hostname
        assert registry_rdap_host is not None
        endpoints = [
            (registry.epp_hostname, registry.node.address),
            (registry.whois_host, registry.node.address),
            (registry_rdap_host, registry.node.address),
        ]
        for rdds in self._registrar_rdds.values():
            registrar = self._registrars[rdds.registrar_id]
            endpoints.extend([
                (registrar.identity.whois_host, rdds.node.address),
                (registrar.identity.rdap_host, rdds.node.address),
            ])
        records = [
            (relative_name, "A", [address])
            for hostname, address in endpoints
            if (relative_name := self._relativeName(hostname, zone)) is not None
        ]
        unique_records = dict.fromkeys(
            (name, record_type, tuple(parameters))
            for name, record_type, parameters in records
        )
        return [
            (name, record_type, list(parameters))
            for name, record_type, parameters in unique_records
        ]

    def _publishInitialServiceRecords(
        self,
        zone: str,
        records: Iterable[tuple[str, str, Iterable[str]]],
    ) -> None:
        """Make service endpoints resolvable before the first Zone Writer run."""
        dns_zone = self._dns.getZone(zone)
        if not dns_zone.findRecords("SOA"):
            dns_zone.addRecord("@ SOA ns1.{} hostmaster.{} 1 900 900 1800 60".format(
                zone, zone
            ))
        for name, record_type, parameters in records:
            dns_zone.addRecord("{} {} {}".format(
                name, record_type, " ".join(parameters)
            ))

    def connectTldDns(
        self,
        *,
        registry_id: str,
        zone: str,
        hidden_primary_vnode: str,
        hidden_primary_ip: str,
        public_secondaries: Iterable[tuple[str, str]],
        nameservers: dict[str, str],
        soa_contact: str,
        static_records: Iterable[tuple[str, str, list[str]]] = (),
        interval_seconds: int = 30,
        transfer_key_name: str | None = None,
    ) -> None:
        """Configure the complete Registry-to-public-TLD publication path."""
        assert registry_id in self._registries, "unknown Registry id"
        registry = self._registries[registry_id]
        normalized_zone = zone.lower().strip(".") + "."
        transfer_key_name = transfer_key_name or "{}-transfer".format(
            normalized_zone.rstrip(".")
        )
        secondary_items = list(public_secondaries)
        assert secondary_items, "at least one public TLD secondary is required"
        assert len(nameservers) == len(secondary_items), (
            "each public TLD secondary requires one nameserver"
        )
        assert len({address for _, address in secondary_items}) == len(secondary_items), (
            "public TLD secondary addresses must be unique"
        )

        publisher_private, publisher_public = self._dns.generateSshKeyPair(
            "{}-zone-publisher".format(normalized_zone.rstrip("."))
        )
        primary_host_private, primary_host_public = self._dns.generateSshKeyPair(
            "{}-hidden-primary".format(normalized_zone.rstrip("."))
        )
        transfer_secret = base64.b64encode(secrets.token_bytes(32)).decode()

        targets = self._dns.getPendingTargets()
        assert hidden_primary_vnode in targets, "hidden-primary vnode is not installed"
        hidden_primary = targets[hidden_primary_vnode]
        hidden_primary.setHiddenPrimary().setTransferKey(
            transfer_key_name, transfer_secret
        ).enableZoneFileReceiver(
            normalized_zone,
            registry.node.address,
            publisher_public,
            primary_host_private,
            primary_host_public,
        )
        for _, address in secondary_items:
            hidden_primary.addTransferTarget(address)

        for vnode, _ in secondary_items:
            targets = self._dns.getPendingTargets()
            secondary = targets.get(vnode)
            if secondary is None:
                secondary = self._dns.install(vnode).addZone(normalized_zone)
            secondary.setSecondary(hidden_primary_ip).setTransferKey(
                transfer_key_name, transfer_secret
            )

        service_records = self._serviceRecords(registry_id, normalized_zone)
        self._publishInitialServiceRecords(normalized_zone, service_records)
        nameserver_records = [
            (relative_name, "A", [address])
            for hostname, (_, address) in zip(nameservers.values(), secondary_items)
            if (relative_name := self._relativeName(hostname, normalized_zone)) is not None
        ]
        generated_records = nameserver_records + service_records + list(static_records)

        self.configureTldPublication(
            registry_id=registry_id,
            zone=normalized_zone,
            nameservers=nameservers,
            soa_contact=soa_contact,
            hidden_primary_ip=hidden_primary_ip,
            publisher_private_key=publisher_private,
            hidden_primary_host_key=primary_host_public,
            public_secondary_ips=[address for _, address in secondary_items],
            static_records=generated_records,
            interval_seconds=interval_seconds,
        )

    def enrollSource(
        self,
        source_node: Node,
        *,
        registrar_id: str,
        source_id: str,
        source_address: str,
        email: str,
        username: str,
        credit_limit: float = 0.0,
    ) -> None:
        """Provision both halves of one source-to-Registrar identity."""
        assert registrar_id in self._registrars, "unknown Registrar id"
        registrar = self._registrars[registrar_id]
        registrar.server.provisionSourceAccount(
            source_node=source_node,
            registrar_url=registrar.registrar_url,
            ca_certificate=registrar.web_tls.certificate,
            source_id=source_id,
            address=source_address,
            email=email,
            username=username,
            credit_limit=credit_limit,
        )

    def _configure_epp_connections(self) -> None:
        """Materialize all EPP graph edges with one CA per Registry."""
        for registry_id, registry in self._registries.items():
            edges = [
                edge for edge in self._epp_connections
                if edge.registry_id == registry_id
            ]
            if not edges:
                continue
            registrar_ids = list(dict.fromkeys(edge.registrar_id for edge in edges))
            credentials = NamingoRegistryService.generateEppTlsCredentialSet(
                registry.epp_hostname, registrar_ids
            )
            registry.server.setTlsCertificate(
                credentials.server_certificate,
                credentials.server_private_key,
                client_ca_pem=credentials.ca_certificate,
            )
            configured_accounts = set()
            configured_credentials = set()
            for edge in edges:
                registrar = self._registrars[edge.registrar_id]
                client_certificate, client_private_key, fingerprint = (
                    credentials.clients[edge.registrar_id]
                )
                account_key = (edge.registrar_id, edge.registry_id)
                if account_key not in configured_accounts:
                    registry.server.addRegistrar(
                        identity=registrar.identity,
                        clid=edge.clid,
                        password=edge.password,
                        prefix=edge.prefix,
                        whitelist=[registrar.node.address],
                        ssl_fingerprint=fingerprint,
                    )
                    configured_accounts.add(account_key)
                credential_key = (edge.registrar_id, edge.registry_id)
                if credential_key not in configured_credentials:
                    registrar.server.setEppClientCredentials(
                        credentials.ca_certificate,
                        client_certificate,
                        client_private_key,
                        credential_name=registry_id,
                    )
                    configured_credentials.add(credential_key)
                registrar.server.addEppProvider(
                    name="{} Registry".format(edge.tld.upper()),
                    hostname=registry.epp_hostname,
                    port=registry.epp_port,
                    tld=edge.tld,
                    clid=edge.clid,
                    password=edge.password,
                    prices=edge.prices,
                    credential_name=registry_id,
                ).enableEppProbe(
                    tld=edge.tld, probe_domain=edge.probe_domain
                )

    def install(self) -> DomainRegistrationDeployment:
        """Add bindings and layers after validating a complete system."""
        assert not self._installed, "DomainRegistrationSystem is already installed"
        assert self._registries, "at least one Registry is required"
        assert self._registrars, "at least one Loom Registrar is required"
        assert self._epp_connections, "at least one EPP connection is required"
        self._configure_epp_connections()
        locations = [(node.asn, node.node_name) for node in self._bindings.values()]
        for node in self._bindings.values():
            colocated = locations.count((node.asn, node.node_name)) > 1
            self._emulator.addBinding(Binding(
                node.vnode,
                filter=Filter(
                    asn=node.asn,
                    nodeName=node.node_name,
                    allowBound=colocated,
                ),
            ))
        for layer in self._layers:
            self._emulator.addLayer(layer)
        self._installed = True
        return DomainRegistrationDeployment(
            dict(self._registries),
            dict(self._registrars),
            dict(self._registrar_rdds),
        )


__all__ = [
    "DomainRegistrationDeployment",
    "DomainRegistrationSystem",
    "EppConnection",
    "LoomRegistrarDeployment",
    "RegistrarRddsDeployment",
    "RegistrationNode",
    "RegistryDeployment",
]
