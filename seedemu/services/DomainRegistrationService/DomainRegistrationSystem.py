from __future__ import annotations

"""Reusable composition of Loom, Namingo Registry/RDDS, and TLD publication."""

import hashlib
import ipaddress
import secrets
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

from seedemu.core import Binding, Emulator, Filter, Node
from seedemu.layers import Base
from seedemu.services.DomainNameService import (
    DomainNameService,
    ZonePublicationCredentials,
)
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
    """Map one service vnode to the physical host that will run it.

    Attributes:
        vnode: Virtual-node name passed to ``Service.install``.
        asn: Autonomous-system number containing the physical host.
        node_name: Physical host name within ``asn``.
        address: Service address used by peers and generated configuration.
    """

    vnode: str
    asn: int
    node_name: str
    address: str


@dataclass(frozen=True)
class RegistryDeployment:
    """References and public endpoints for one configured Registry."""
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
    """References, identity, and HTTPS state for one Loom Registrar."""
    identity: RegistrarIdentity
    node: RegistrationNode
    service: LoomRegistrarService
    server: LoomRegistrarServer
    web_tls: LoomWebTlsCredentials
    registrar_url: str
    database: str


@dataclass(frozen=True)
class RegistrarRddsDeployment:
    """References for Registrar WHOIS/RDAP attached to a Loom instance."""
    registrar_id: str
    node: RegistrationNode
    service: NamingoRegistrarService
    server: NamingoRegistrarServer


@dataclass(frozen=True)
class DomainRegistrationDeployment:
    """Snapshot of all deployments produced when the system is installed."""
    registries: dict[str, RegistryDeployment]
    registrars: dict[str, LoomRegistrarDeployment]
    registrar_rdds: dict[str, RegistrarRddsDeployment]


@dataclass(frozen=True)
class EppConnection:
    """Configuration of one Registrar-to-Registry EPP relationship."""
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
        """Create an uninstalled domain-registration composition.

        Args:
            emulator: Emulator that will receive service layers and bindings.
            base: Base layer used to validate physical hosts.
            dns: Authoritative DNS layer used for TLD publication.
            registrar_identity: Optional default identity for Loom Registrars.
        """
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
        """Validate a short identifier used as an internal dictionary key."""
        assert 1 <= len(value) <= 32 and value.replace("-", "").replace("_", "").isalnum(), (
            "invalid {} id".format(kind)
        )

    def _bind(self, node: RegistrationNode) -> None:
        """Validate and queue a vnode-to-physical-host binding."""
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
        """Create one EPP Registry and its Registry-authority RDDS.

        Args:
            registry_id: Unique composition-local Registry identifier.
            node: Virtual and physical placement of the Registry.
            epp_hostname: DNS hostname exposed by the EPP server.
            tlds: TLDs for which this Registry accepts registrations.
            whois_host: Public Registry WHOIS hostname.
            rdap_url: Public Registry RDAP base URL.
            epp_port: TCP port used by EPP over TLS.

        Returns:
            The configured Registry deployment and its service/server handles.
        """
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
        """Create the customer-facing Loom Registrar and business database.

        Args:
            registrar_id: Unique composition-local Registrar identifier.
            node: Virtual and physical placement of Loom.
            identity: Public Registrar identity, or the constructor default.
            commit: Optional Loom commit override for controlled experiments.
            database: Loom database name.
            database_username: Local Loom database user.
            database_password: Password for the local database user.
            webauthn_secret: Secret used by Loom's WebAuthn configuration.

        Returns:
            The configured Loom deployment, including generated HTTPS material.
        """
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
        """Declare one edge in the Registrar-to-Registry EPP graph.

        Args:
            registrar_id: Existing Loom Registrar identifier.
            registry_id: Existing Registry identifier serving ``tld``.
            clid: Optional EPP client identifier; generated when omitted.
            password: Optional EPP password; generated when omitted.
            prefix: Optional Registry object prefix; generated when omitted.
            tld: TLD sold through this connection.
            prices: Loom prices keyed by operation, registration period, and value.
            probe_domain: Domain used for the read-only EPP health check.

        Returns:
            Nothing. The connection is materialized by :meth:`install`.
        """
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
        """Attach Registrar WHOIS/RDAP to Loom's business database.

        Args:
            rdds_id: Unique composition-local RDDS identifier.
            registrar_id: Loom Registrar whose data will be served.
            node: Virtual and physical placement of Namingo Registrar RDDS.
            database_username: Read-only Loom database user to create.
            database_password: Password for that read-only user.
            rdap_proxy_port: HTTP port exposing the RDAP reverse proxy.

        Returns:
            The configured Registrar RDDS deployment and service handles.
        """
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
        """Connect Registry Zone Writer output to authoritative TLD DNS.

        Args:
            registry_id: Registry whose database feeds the zone writer.
            zone: TLD zone to publish.
            nameservers: Zone-writer NS slots mapped to public hostnames.
            soa_contact: SOA responsible-party domain name.
            hidden_primary_ip: Destination address for full-zone publication.
            publisher_private_key: SSH key used by the Registry publisher.
            hidden_primary_host_key: Expected SSH host public key.
            public_secondary_ips: Servers whose SOA serials must converge.
            static_records: Records retained in every generated zone snapshot.
            interval_seconds: Zone-writer polling interval.

        Returns:
            Nothing. It updates the Registry server configuration in place.
        """
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
        """Return an in-zone hostname relative to ``zone``, else ``None``."""
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
        """Derive public A records for Registry and Registrar RDDS endpoints."""
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
        """Add initial service records before the first Zone Writer run.

        Args:
            zone: Existing authoritative DNS zone to update.
            records: ``(name, type, parameters)`` records relative to ``zone``.

        Returns:
            Nothing. The DNS layer's pending zone is modified in place.
        """
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
        hidden_primary_ip: str,
        publication: ZonePublicationCredentials,
        nameservers: dict[str, str],
        soa_contact: str,
        static_records: Iterable[tuple[str, str, list[str]]] = (),
        interval_seconds: int = 30,
    ) -> None:
        """Publish Registry-generated data to an existing TLD DNS topology.

        Args:
            registry_id: Registry that owns and publishes ``zone``.
            zone: TLD zone, with or without a trailing dot.
            hidden_primary_ip: Existing DNS primary receiving complete zones.
            publication: Opaque DNS-service result containing the publisher
                credentials and public-secondary convergence targets.
            nameservers: Zone-writer NS slots mapped to public DNS names.
            soa_contact: SOA responsible-party domain name.
            static_records: Scenario records retained during regeneration.
            interval_seconds: Zone-writer polling interval.

        Returns:
            Nothing. Registry publication and initial records are configured;
            DNS server roles and transfers must already exist.
        """
        assert registry_id in self._registries, "unknown Registry id"
        normalized_zone = zone.lower().strip(".") + "."
        secondary_ips = list(publication.secondary_addresses)
        assert secondary_ips, "at least one public TLD secondary is required"
        assert len(nameservers) == len(secondary_ips), (
            "each public TLD secondary requires one nameserver"
        )
        assert len(set(secondary_ips)) == len(secondary_ips), (
            "public TLD secondary addresses must be unique"
        )

        service_records = self._serviceRecords(registry_id, normalized_zone)
        self._publishInitialServiceRecords(normalized_zone, service_records)
        nameserver_records = [
            (relative_name, "A", [address])
            for hostname, address in zip(nameservers.values(), secondary_ips)
            if (relative_name := self._relativeName(hostname, normalized_zone)) is not None
        ]
        generated_records = nameserver_records + service_records + list(static_records)

        self.configureTldPublication(
            registry_id=registry_id,
            zone=normalized_zone,
            nameservers=nameservers,
            soa_contact=soa_contact,
            hidden_primary_ip=hidden_primary_ip,
            publisher_private_key=publication.publisher_private_key,
            hidden_primary_host_key=publication.primary_host_public_key,
            public_secondary_ips=secondary_ips,
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
        """Provision both halves of one source-to-Registrar identity.

        Args:
            source_node: Emulated client receiving its credential material.
            registrar_id: Loom Registrar that authenticates the source.
            source_id: Stable, non-secret source principal identifier.
            source_address: Expected source IP address at the Registrar.
            email: Email assigned to the bootstrapped Loom account.
            username: Login name assigned to the Loom account.
            credit_limit: Initial account credit available for purchases.

        Returns:
            Nothing. Both source node and Loom configuration are modified.
        """
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
        """Validate and add all queued bindings and service layers.

        Returns:
            A snapshot containing every installed Registry, Registrar, and
            Registrar RDDS deployment.

        Raises:
            AssertionError: If required components are missing or installation
                has already occurred.
        """
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
