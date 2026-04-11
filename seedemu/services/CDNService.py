from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Network
from typing import Dict, List, Optional, Set, Tuple

from seedemu.core import Emulator, Node, Server, Service
from seedemu.core.enums import NetworkType

from .DomainNameService import DomainNameService, DomainNameServer


CDNServiceFileTemplates: Dict[str, str] = {}

CDNServiceFileTemplates['origin_nginx_site'] = '''\
server {{
    listen {port};
    root {root};
    index index.html;
    server_name {server_name};
    add_header X-CDN-Origin {origin_name} always;
    add_header X-CDN-Origin-IP {origin_ip} always;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
'''

CDNServiceFileTemplates['edge_nginx_site'] = '''\
upstream cdn_origin_backend {{
{upstreams}
}}

server {{
    listen {port};
    server_name {server_names};
    add_header X-CDN-Edge {site_name} always;
    add_header X-CDN-Region {region} always;
    add_header X-CDN-Edge-IP {edge_ip} always;

    location / {{
        proxy_set_header Host $host;
        proxy_set_header X-CDN-Site {site_name};
        proxy_set_header X-CDN-Region {region};
        proxy_set_header X-CDN-Edge-IP {edge_ip};
        proxy_pass http://cdn_origin_backend;
    }}
}}
'''


def _choose_service_address(node: Node) -> str:
    for iface in node.getInterfaces():
        net = iface.getNet()
        if net.getType() == NetworkType.Local:
            return str(iface.getAddress())

    ifaces = node.getInterfaces()
    assert len(ifaces) > 0, 'node has no interfaces'
    return str(ifaces[0].getAddress())


def _normalize_zone_name(zone: str) -> str:
    return zone if zone.endswith('.') else '{}.'.format(zone)


def _infer_zone_name(domain: str) -> str:
    domain = domain[:-1] if domain.endswith('.') else domain
    labels = domain.split('.')
    assert len(labels) >= 2, 'cannot infer authoritative zone from "{}"'.format(domain)
    return _normalize_zone_name('.'.join(labels[1:]))


def _relative_record_name(domain: str, zone: str) -> str:
    domain = domain[:-1] if domain.endswith('.') else domain
    zone = zone[:-1] if zone.endswith('.') else zone
    if domain == zone:
        return '@'
    suffix = '.{}'.format(zone)
    assert domain.endswith(suffix), 'domain "{}" is not inside zone "{}"'.format(domain, zone)
    return domain[: -len(suffix)]


def _safe_name(value: str) -> str:
    return value.replace('.', '_').replace('-', '_').replace('/', '_')


@dataclass
class _DomainConfig:
    domain: str
    dns_vnode: str
    edges: List[str]
    mode: str = 'static'
    zone: Optional[str] = None
    include_path: Optional[str] = None
    region_map: Dict[str, List[str]] = field(default_factory=dict)
    asn_map: Dict[int, List[str]] = field(default_factory=dict)


class CDNOriginServer(Server):
    __node: Optional[Node]
    __service_ip: Optional[str]
    __port: int
    __server_name: str
    __index_content: str
    __root: str

    def __init__(self):
        super().__init__()
        self.__node = None
        self.__service_ip = None
        self.__port = 8080
        self.__server_name = '_'
        self.__index_content = ''
        self.__root = '/var/www/html'

    def setPort(self, port: int) -> CDNOriginServer:
        self.__port = port
        return self

    def getPort(self) -> int:
        return self.__port

    def setServerName(self, server_name: str) -> CDNOriginServer:
        self.__server_name = server_name
        return self

    def setIndexContent(self, content: str) -> CDNOriginServer:
        self.__index_content = content
        return self

    def setRoot(self, path: str) -> CDNOriginServer:
        self.__root = path
        return self

    def configure(self, node: Node):
        self.__node = node
        self.__service_ip = _choose_service_address(node)

    def getNode(self) -> Node:
        assert self.__node is not None, 'origin server not configured yet'
        return self.__node

    def getServiceAddress(self) -> str:
        assert self.__service_ip is not None, 'origin server not configured yet'
        return self.__service_ip

    def install(self, node: Node):
        origin_name = node.getName()
        origin_ip = self.getServiceAddress()
        node.addSoftware('nginx-light')
        index_content = self.__index_content or '<h1>{}</h1>'.format(node.getName())
        node.setFile('{}/index.html'.format(self.__root), index_content)
        node.setFile(
            '/etc/nginx/sites-available/default',
            CDNServiceFileTemplates['origin_nginx_site'].format(
                port=self.__port,
                root=self.__root,
                server_name=self.__server_name,
                origin_name=origin_name,
                origin_ip=origin_ip,
            )
        )
        node.appendStartCommand('service nginx start')
        node.appendClassName('CDNOrigin')


class CDNEdgeServer(Server):
    __node: Optional[Node]
    __service_ip: Optional[str]
    __port: int
    __region: str
    __server_name: str
    __origin_vnodes: List[str]
    __resolved_origins: List[Tuple[str, int]]
    __enable_proxy_headers: bool
    __served_domains: Set[str]

    def __init__(self):
        super().__init__()
        self.__node = None
        self.__service_ip = None
        self.__port = 8080
        self.__region = 'default'
        self.__server_name = '_'
        self.__origin_vnodes = []
        self.__resolved_origins = []
        self.__enable_proxy_headers = True
        self.__served_domains = set()

    def setPort(self, port: int) -> CDNEdgeServer:
        self.__port = port
        return self

    def getPort(self) -> int:
        return self.__port

    def setRegion(self, region: str) -> CDNEdgeServer:
        self.__region = region
        return self

    def getRegion(self) -> str:
        return self.__region

    def addOrigin(self, vnode: str) -> CDNEdgeServer:
        if vnode not in self.__origin_vnodes:
            self.__origin_vnodes.append(vnode)
        return self

    def getOriginVnodes(self) -> List[str]:
        return self.__origin_vnodes

    def setServerName(self, server_name: str) -> CDNEdgeServer:
        self.__server_name = server_name
        return self

    def enableProxyHeaders(self, enabled: bool = True) -> CDNEdgeServer:
        self.__enable_proxy_headers = enabled
        return self

    def addServedDomain(self, domain: str):
        self.__served_domains.add(domain)

    def getServedDomains(self) -> List[str]:
        return sorted(self.__served_domains)

    def configure(self, node: Node):
        self.__node = node
        self.__service_ip = _choose_service_address(node)

    def setResolvedOrigins(self, origins: List[Tuple[str, int]]):
        self.__resolved_origins = origins

    def getNode(self) -> Node:
        assert self.__node is not None, 'edge server not configured yet'
        return self.__node

    def getServiceAddress(self) -> str:
        assert self.__service_ip is not None, 'edge server not configured yet'
        return self.__service_ip

    def install(self, node: Node):
        assert len(self.__resolved_origins) > 0, 'edge {} has no configured origin'.format(node.getName())
        upstreams = []
        for (addr, port) in self.__resolved_origins:
            upstreams.append('    server {}:{};'.format(addr, port))

        if self.__server_name != '_':
            server_names = self.__server_name
        elif len(self.__served_domains) > 0:
            server_names = ' '.join(sorted(self.__served_domains))
        else:
            server_names = '_'

        if self.__enable_proxy_headers:
            site_name = node.getName()
            region = self.__region
            edge_ip = self.getServiceAddress()
        else:
            site_name = ''
            region = ''
            edge_ip = ''

        node.addSoftware('nginx-light')
        node.setFile(
            '/etc/nginx/sites-available/default',
            CDNServiceFileTemplates['edge_nginx_site'].format(
                port=self.__port,
                server_names=server_names,
                upstreams='\n'.join(upstreams),
                site_name=site_name,
                region=region,
                edge_ip=edge_ip,
            )
        )
        node.appendStartCommand('service nginx start')
        node.appendClassName('CDNEdge')


class CDNService(Service):
    __dns_service_name: str
    __origins: Dict[str, CDNOriginServer]
    __edges: Dict[str, CDNEdgeServer]
    __domains: Dict[str, _DomainConfig]
    __region_members: Dict[str, Set[int]]
    __metrics_enabled: bool

    def __init__(self, dnsServiceName: str = 'DomainNameService'):
        super().__init__()
        self.__dns_service_name = dnsServiceName
        self.__origins = {}
        self.__edges = {}
        self.__domains = {}
        self.__region_members = {}
        self.__metrics_enabled = False
        self.addDependency('Base', False, False)
        self.addDependency('Routing', False, False)
        self.addDependency(dnsServiceName, True, False)

    def _createServer(self) -> Server:
        raise AssertionError('Use createOrigin() or createEdge() instead of install().')

    def createOrigin(self, vnode: str) -> CDNOriginServer:
        if vnode in self.__edges:
            raise AssertionError('vnode "{}" already used as edge'.format(vnode))
        if vnode not in self.__origins:
            server = CDNOriginServer()
            self.__origins[vnode] = server
            self._pending_targets[vnode] = server
        return self.__origins[vnode]

    def createEdge(self, vnode: str) -> CDNEdgeServer:
        if vnode in self.__origins:
            raise AssertionError('vnode "{}" already used as origin'.format(vnode))
        if vnode not in self.__edges:
            server = CDNEdgeServer()
            self.__edges[vnode] = server
            self._pending_targets[vnode] = server
        return self.__edges[vnode]

    def setDomain(
        self,
        domain: str,
        *,
        dnsVnode: str,
        edges: List[str],
        mode: str = 'static',
        zone: Optional[str] = None,
    ) -> CDNService:
        mode = mode.lower()
        assert mode in ['static', 'round_robin', 'region', 'map'], 'unsupported CDN mode "{}"'.format(mode)
        self.__domains[domain] = _DomainConfig(
            domain=domain[:-1] if domain.endswith('.') else domain,
            dns_vnode=dnsVnode,
            edges=list(edges),
            mode=mode,
            zone=_normalize_zone_name(zone) if zone is not None else None,
        )
        return self

    def mapRegion(self, domain: str, region: str, edges: List[str]) -> CDNService:
        assert domain in self.__domains, 'unknown domain "{}"'.format(domain)
        current_edges = self.__domains[domain].region_map.setdefault(region, [])
        for edge in edges:
            if edge not in current_edges:
                current_edges.append(edge)
        return self

    def setRegionMembers(self, region: str, asns: List[int]) -> CDNService:
        if region not in self.__region_members:
            self.__region_members[region] = set()
        self.__region_members[region].update(asns)
        return self

    def mapAsn(self, domain: str, asns: List[int], edges: List[str]) -> CDNService:
        assert domain in self.__domains, 'unknown domain "{}"'.format(domain)
        for asn in asns:
            current_edges = self.__domains[domain].asn_map.setdefault(int(asn), [])
            for edge in edges:
                if edge not in current_edges:
                    current_edges.append(edge)
        return self

    def setIncludeContent(
        self,
        domain: str,
        file_path: str = '/etc/bind/include/custom.local',
    ) -> CDNService:
        assert domain in self.__domains, 'unknown domain "{}"'.format(domain)
        self.__domains[domain].include_path = file_path
        return self

    def enableMetrics(self, enabled: bool = True) -> CDNService:
        self.__metrics_enabled = enabled
        return self

    def getName(self) -> str:
        return 'CDNService'

    def _doConfigure(self, node: Node, server: Server):
        if isinstance(server, CDNOriginServer) or isinstance(server, CDNEdgeServer):
            server.configure(node)

    def configure(self, emulator: Emulator):
        super().configure(emulator)

        dns_layer: DomainNameService = emulator.getRegistry().get('seedemu', 'layer', self.__dns_service_name)
        assert dns_layer is not None, 'CDNService requires DomainNameService'

        self.__prepareDnsZones(emulator, dns_layer)
        self.__resolveEdgeOrigins()
        self.__configureDns(emulator, dns_layer)

    def __prepareDnsZones(self, emulator: Emulator, dns_layer: DomainNameService):
        zones_per_dns: Dict[str, Set[str]] = {}

        for domain_cfg in self.__domains.values():
            zone_name = domain_cfg.zone if domain_cfg.zone is not None else _infer_zone_name(domain_cfg.domain)
            domain_cfg.zone = zone_name
            zones_per_dns.setdefault(domain_cfg.dns_vnode, set()).add(zone_name)

            for edge_vnode in domain_cfg.edges:
                assert edge_vnode in self.__edges, 'unknown edge vnode "{}" for domain "{}"'.format(edge_vnode, domain_cfg.domain)
                self.__edges[edge_vnode].addServedDomain(domain_cfg.domain)

        dns_targets = dns_layer.getPendingTargets()
        for (dns_vnode, zone_names) in zones_per_dns.items():
            assert dns_vnode in dns_targets, 'DNS vnode "{}" is not installed on DomainNameService'.format(dns_vnode)
            dns_server: DomainNameServer = dns_targets[dns_vnode]
            dns_node = emulator.getBindingFor(dns_vnode)
            existing = set(dns_server.getZones())
            changed = False
            for zone_name in zone_names:
                if zone_name not in existing:
                    dns_server.addZone(zone_name)
                    changed = True
            if changed:
                dns_server.configure(dns_node, dns_layer)

    def __resolveEdgeOrigins(self):
        for edge in self.__edges.values():
            resolved = []
            for origin_vnode in edge.getOriginVnodes():
                assert origin_vnode in self.__origins, 'unknown origin vnode "{}"'.format(origin_vnode)
                origin = self.__origins[origin_vnode]
                resolved.append((origin.getServiceAddress(), origin.getPort()))
            edge.setResolvedOrigins(resolved)

    def __configureDns(self, emulator: Emulator, dns_layer: DomainNameService):
        policy_domains: Dict[str, List[_DomainConfig]] = {}

        for domain_cfg in self.__domains.values():
            if domain_cfg.mode in ['static', 'round_robin']:
                self.__configureSimpleDomain(dns_layer, domain_cfg)
            else:
                assert domain_cfg.include_path is not None, (
                    'domain "{}" uses mode "{}" and requires setIncludeContent()'.format(
                        domain_cfg.domain, domain_cfg.mode
                    )
                )
                policy_domains.setdefault(domain_cfg.dns_vnode, []).append(domain_cfg)

        for (dns_vnode, domain_cfgs) in policy_domains.items():
            self.__configureIncludeBackedDomains(emulator, dns_layer, dns_vnode, domain_cfgs)

    def __configureSimpleDomain(self, dns_layer: DomainNameService, domain_cfg: _DomainConfig):
        zone = dns_layer.getZone(domain_cfg.zone)
        record_name = _relative_record_name(domain_cfg.domain, domain_cfg.zone)
        selected_edges = domain_cfg.edges[:1] if domain_cfg.mode == 'static' else domain_cfg.edges
        for edge_vnode in selected_edges:
            edge = self.__edges[edge_vnode]
            zone.addRecord('{} A {}'.format(record_name, edge.getServiceAddress()))

    def __configureIncludeBackedDomains(
        self,
        emulator: Emulator,
        dns_layer: DomainNameService,
        dns_vnode: str,
        domains: List[_DomainConfig],
    ):
        dns_targets = dns_layer.getPendingTargets()
        dns_server: DomainNameServer = dns_targets[dns_vnode]
        dns_node = emulator.getBindingFor(dns_vnode)
        dns_addr = _choose_service_address(dns_node)
        include_groups: Dict[str, List[_DomainConfig]] = {}
        for domain_cfg in domains:
            include_path = domain_cfg.include_path
            assert include_path is not None, 'domain "{}" is missing include path'.format(domain_cfg.domain)
            assert dns_server.getIncludePath(domain_cfg.zone) == include_path, (
                'DNS include path mismatch for zone "{}": expected "{}", got "{}"'.format(
                    domain_cfg.zone,
                    include_path,
                    dns_server.getIncludePath(domain_cfg.zone),
                )
            )
            include_groups.setdefault(include_path, []).append(domain_cfg)

        for (include_path, include_domains) in include_groups.items():
            zone_names = sorted(set(domain_cfg.zone for domain_cfg in include_domains))
            view_rules: List[Tuple[str, List[str], Dict[str, List[str]]]] = []
            acl_definitions: List[str] = []
            view_index = 0

            for domain_cfg in include_domains:
                edge_map = self.__buildDomainEdgeMap(emulator, domain_cfg)
                for (_rule_name, (cidrs, edges)) in edge_map.items():
                    acl_name = 'cdn_acl_{}_{}'.format(_safe_name(domain_cfg.domain), view_index)
                    view_name = 'cdn_view_{}_{}'.format(_safe_name(domain_cfg.domain), view_index)
                    acl_definitions.append(
                        'acl "{}" {{ {} }};\n'.format(acl_name, ' '.join(['{};'.format(c) for c in cidrs]))
                    )
                    view_rules.append((view_name, [acl_name], {domain_cfg.domain: edges}))
                    view_index += 1

            default_domain_edges = {
                domain_cfg.domain: domain_cfg.edges[:1]
                for domain_cfg in include_domains
            }
            view_rules.append(('cdn_view_default', [], default_domain_edges))

            include_content = ''.join(acl_definitions)
            for (view_name, acl_names, domain_edges) in view_rules:
                match_clients = 'any;' if len(acl_names) == 0 else ' '.join(['{};'.format(name) for name in acl_names])
                view_lines = [
                    'view "{}" {{'.format(view_name),
                    '    match-clients {{ {} }};'.format(match_clients),
                    '    recursion no;',
                ]

                for zone_name in zone_names:
                    zone_path = '/etc/bind/zones/{}_{}.zone'.format(_safe_name(zone_name), _safe_name(view_name))
                    zone_content = self.__buildZoneFileForView(dns_layer, zone_name, domain_edges, dns_addr)
                    dns_server.setZoneFile(zone_path, zone_content)
                    view_lines.append(
                        '    zone "{}" {{ type master; file "{}"; allow-update {{ any; }}; }};'.format(
                            zone_name if zone_name != '' else '.', zone_path
                        )
                    )

                view_lines.append('};\n')
                include_content += '\n'.join(view_lines)

            dns_server.setIncludeFile(include_path, include_content)

    def __buildDomainEdgeMap(self, emulator: Emulator, domain_cfg: _DomainConfig) -> Dict[str, Tuple[List[str], List[str]]]:
        mapping: Dict[str, Tuple[List[str], List[str]]] = {}

        if domain_cfg.mode == 'map':
            grouped: Dict[Tuple[str, ...], List[int]] = {}
            for (asn, edges) in domain_cfg.asn_map.items():
                grouped.setdefault(tuple(edges), []).append(asn)

            for (idx, (edges, asns)) in enumerate(grouped.items()):
                cidrs = self.__collectCidrsForAsns(emulator, asns)
                if len(cidrs) > 0:
                    mapping['map_{}'.format(idx)] = (cidrs, list(edges))
            return mapping

        if domain_cfg.mode == 'region':
            for (idx, (region, edges)) in enumerate(domain_cfg.region_map.items()):
                asns = sorted(self.__region_members.get(region, set()))
                cidrs = self.__collectCidrsForAsns(emulator, asns)
                if len(cidrs) > 0:
                    mapping['region_{}'.format(idx)] = (cidrs, list(edges))
            return mapping

        return mapping

    def __collectCidrsForAsns(self, emulator: Emulator, asns: List[int]) -> List[str]:
        cidrs: Set[str] = set()
        reg = emulator.getRegistry()
        target_asns = set(asns)
        for ((scope, obj_type, _name), obj) in reg.getAll().items():
            if obj_type not in ['hnode', 'rnode']:
                continue
            try:
                asn = int(scope)
            except ValueError:
                continue
            if asn not in target_asns:
                continue
            node: Node = obj
            for iface in node.getInterfaces():
                net = iface.getNet()
                if net.getType() == NetworkType.Local:
                    cidrs.add(str(net.getPrefix()))

        return sorted(cidrs)

    def __buildZoneFileForView(
        self,
        dns_layer: DomainNameService,
        zone_name: str,
        domain_edges: Dict[str, List[str]],
        dns_addr: str,
    ) -> str:
        zone = dns_layer.getZone(zone_name)
        records = list(zone.getRecords())
        filtered_records = records[:2]

        if not any(' SOA ' in record for record in records):
            zonename = zone_name if zone_name.endswith('.') else '{}.'.format(zone_name)
            filtered_records.append('@ SOA ns1.{} admin.{} 1 900 900 1800 60'.format(zonename, zonename))

        if not any(record.startswith('@ NS ') for record in records):
            zonename = zone_name if zone_name.endswith('.') else '{}.'.format(zone_name)
            filtered_records.append('@ NS ns1.{}'.format(zonename))

        if not any(record.endswith(' A {}'.format(dns_addr)) and record.startswith('ns1') for record in records):
            filtered_records.append('ns1 A {}'.format(dns_addr))

        managed_domains = set()
        for domain in domain_edges.keys():
            if self.__domains[domain].zone == zone_name:
                managed_domains.add(_relative_record_name(domain, zone_name))

        for record in records[2:]:
            skip = False
            for record_name in managed_domains:
                if record.startswith('{} A '.format(record_name)):
                    skip = True
                    break
            if not skip:
                filtered_records.append(record)

        for (domain, edges) in domain_edges.items():
            if self.__domains[domain].zone != zone_name:
                continue
            record_name = _relative_record_name(domain, zone_name)
            for edge_vnode in edges:
                edge = self.__edges[edge_vnode]
                filtered_records.append('{} A {}'.format(record_name, edge.getServiceAddress()))

        return '\n'.join(filtered_records)
