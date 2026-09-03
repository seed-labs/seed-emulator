from __future__ import annotations
from seedemu.core import Node, Printable, Emulator, Service, Server
from seedemu.core.enums import NetworkType
from typing import List, Dict, Tuple, Set, Optional
from ipaddress import ip_address
from re import fullmatch, sub
from random import randint
import requests

DomainNameServiceFileTemplates: Dict[str, str] = {}
ROOT_ZONE_URL = 'https://www.internic.net/domain/root.zone'

DomainNameServiceFileTemplates['named_options'] = '''\
options {
	directory "/var/cache/bind";
	recursion no;
	dnssec-validation no;
    empty-zones-enable no;
	allow-query { any; };
    allow-update { any; };
};
'''

class Zone(Printable):
    """!
    @brief Domain name zone.
    """
    __zonename: str
    __subzones: Dict[str, Zone]
    __records: List[str]
    __gules: List[str]
    __pending_records: Dict[str, List[str]]

    def __init__(self, name: str):
        """!
        @brief Zone constructor.
        
        @param name full zonename.
        """
        self.__zonename = name
        self.__subzones = {}
        self.__records = [
            '$TTL 300',
            '$ORIGIN {}'.format(name if name != '' else '.')
        ]
        self.__gules = []
        self.__pending_records = {}

    def getName(self) -> str:
        """!
        @brief Get zonename.

        @returns zonename.
        """
        return self.__zonename

    def getSubZone(self, name: str) -> Zone:
        """!
        @brief Get a subzone, if not exists, a new one will be created.

        @param name partial zonename. For example, if current zone is "com.", to
        get "example.com.", use getSubZone("example")

        @returns zone.
        @throws AssertionError if invalid zonename.
        """
        assert '.' not in name, 'invalid subzone name "{}"'.format(name)
        if name in self.__subzones: return self.__subzones[name]
        self.__subzones[name] = Zone('{}.{}'.format(name, self.__zonename if self.__zonename != '.' else ''))
        return self.__subzones[name]
    
    def getSubZones(self) -> Dict[str, Zone]:
        """!
        @brief Get all subzones.

        @return subzones dict.
        """
        return self.__subzones

    def addRecord(self, record: str) -> Zone:
        """!
        @brief Add a new record to zone.

        @todo NS?
        
        @returns self, for chaining API calls.
        """
        self.__records.append(record)

        return self
    
    def deleteRecord(self, record: str) -> Zone:
        """!
        @brief Delete the record from zone.

        @todo NS?
        
        @returns self, for chaining API calls.
        """
        self.__records.remove(record)

        return self

    def addGuleRecord(self, fqdn: str, addr: str) -> Zone:
        """!
        @brief Add a new gule record.

        Use this method to register a name server in the parent zone.

        @param fqdn full domain name of the name server.
        @param addr IP address of the name server.

        @returns self, for chaining API calls.
        """
        if fqdn[-1] != '.': fqdn += '.'
        zonename = self.__zonename if self.__zonename != '' else '.' 
        self.__gules.append('{} A {}'.format(fqdn, addr))
        self.__gules.append('{} NS {}'.format(zonename, fqdn))

        return self

    def resolveTo(self, name: str, node: Node) -> Zone:
        """!
        @brief Add a new A record, pointing to the given node.

        @param name name.
        @param node node.

        @throws AssertionError if node does not have valid interfaces.

        @returns self, for chaining API calls.
        """

        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node has no interfaces.'
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break

        assert address != None, 'Node has no valid interfaces.'
        self.__records.append('{} A {}'.format(name, address))

        return self

    def resolveToVnode(self, name: str, vnode: str) -> Zone:
        """!
        @brief Add a new A record, pointing to the given virtual node name.

        @param name name.
        @param vnode  virtual node name.

        @returns self, for chaining API calls.
        """
        self.__pending_records.setdefault(name, []).append(vnode)

        return self

    def resolvePendingRecords(self, emulator: Emulator):
        """!
        @brief resolve pending records in this zone.

        @param emulator emulator object.
        """
        for domain_name, vnode_names in self.__pending_records.items():
            for vnode_name in vnode_names:
                pnode = emulator.resolvVnode(vnode_name)

                ifaces = pnode.getInterfaces()
                assert len(ifaces) > 0, 'resolvePendingRecords(): node as{}/{} has no interfaces'.format(pnode.getAsn(), pnode.getName())
                addr = ifaces[0].getAddress()

                self.addRecord('{} A {}'.format(domain_name, addr))

    def getPendingRecords(self) -> Dict[str, List[str]]:
        """!
        @brief Get pending records.

        @returns dict, where key is domain name, and value is a list of vnode names.
        """
        return self.__pending_records

    def getRecords(self) -> List[str]:
        """!
        @brief Get all records.

        @return list of records.
        """
        return self.__records

    def getGuleRecords(self) -> List[str]:
        """!
        @brief Get all gule records.

        @return list of records.
        """
        return self.__gules

    def findRecords(self, keyword: str) -> List[str]:
        """!
        @brief Find a record.

        @param keyword keyword.

        @return list of records.
        """
        return [ r for r in self.__records if keyword in r ]

    def print(self, indent: int) -> str:
        out = ' ' * indent
        zonename = self.__zonename if self.__zonename != '' else '(root zone)'
        out += 'Zone "{}":\n'.format(zonename)

        indent += 4
        out += ' ' * indent
        out += 'Zonefile:\n'

        indent += 4
        for record in self.__records:
            out += ' ' * indent
            out += '{}\n'.format(record)

        indent -= 4
        out += ' ' * indent
        out += 'Subzones:\n'
        
        indent += 4
        for subzone in self.__subzones.values():
            out += subzone.print(indent)

        return out

class DomainNameServer(Server):
    """!
    @brief The domain name server.
    """

    __zones: Set[Tuple[str, bool]]
    __node: Node
    __is_master: bool
    __is_real_root: bool
    __include_paths: Dict[str, str]
    __is_hidden_primary: bool
    __primary_ip: Optional[str]
    __transfer_key: Optional[Tuple[str, str]]
    __transfer_targets: List[str]
    __zone_file_receiver: Optional[Tuple[str, str, str, str, str, int]]

    def __init__(self):
        """!
        @brief DomainNameServer constructor.
        """
        super().__init__()
        
        self.__zones = set()
        self.__is_master = False
        self.__is_real_root = False
        self.__include_paths = {}
        self.__is_hidden_primary = False
        self.__primary_ip = None
        self.__transfer_key = None
        self.__transfer_targets = []
        self.__zone_file_receiver = None

    def addZone(self, zonename: str, createNsAndSoa: bool = True) -> DomainNameServer:
        """!
        @brief Add a zone to this node.

        @param zonename name of zone to host.
        @param createNsAndSoa add NS and SOA (if doesn't already exist) to zone. 

        You should use DomainNameService.hostZoneOn to host zone on node if you
        want the automated NS record to work.

        @returns self, for chaining API calls.
        """
        self.__zones.add((zonename, createNsAndSoa))

        return self

    def setMaster(self) -> DomainNameServer:
        """!
        @brief set the name server to be master name server.

        @returns self, for chaining API calls.
        """
        self.__is_master = True

        return self

    def setHiddenPrimary(self) -> DomainNameServer:
        """!
        @brief Make this server a hidden authoritative primary.

        A hidden primary is not published in parent-zone NS/glue records, does
        not answer ordinary queries for its hosted zones, and rejects dynamic
        updates. Zone data is expected to be delivered as a validated zone file
        by an external publisher such as Namingo Registry's Zone Writer.

        @returns self, for chaining API calls.
        """
        self.__is_master = True
        self.__is_hidden_primary = True

        return self

    def isHiddenPrimary(self) -> bool:
        """! @brief Return whether this server is a hidden primary. """
        return self.__is_hidden_primary

    def setSecondary(self, primary_ip: str) -> DomainNameServer:
        """!
        @brief Explicitly configure this server as a secondary.

        @param primary_ip hidden/public primary address used for AXFR/IXFR.

        @returns self, for chaining API calls.
        """
        ip_address(primary_ip)
        self.__is_master = False
        self.__primary_ip = primary_ip

        return self

    def setTransferKey(self, name: str, secret: str) -> DomainNameServer:
        """!
        @brief Configure the TSIG key used for NOTIFY and AXFR/IXFR.

        The same key must be configured on the primary and its secondaries.
        This key is deliberately separate from Registrar/Registry EPP
        credentials and from any dynamic-update key.

        @returns self, for chaining API calls.
        """
        assert fullmatch(r'[A-Za-z0-9_.-]{1,63}', name), 'invalid TSIG key name'
        assert fullmatch(r'[A-Za-z0-9+/]+={0,2}', secret), 'invalid TSIG secret'
        self.__transfer_key = (name, secret)

        return self

    def addTransferTarget(self, address: str) -> DomainNameServer:
        """!
        @brief Authorize and notify a secondary at the given address.

        @returns self, for chaining API calls.
        """
        ip_address(address)
        assert address not in self.__transfer_targets, 'duplicate transfer target'
        self.__transfer_targets.append(address)

        return self

    def enableZoneFileReceiver(
        self,
        zonename: str,
        publisher_ip: str,
        publisher_public_key: str,
        ssh_host_private_key: str,
        ssh_host_public_key: str,
        max_bytes: int = 8 * 1024 * 1024,
    ) -> DomainNameServer:
        """!
        @brief Accept one zone file through a restricted SSH forced command.

        The receiver validates the candidate with named-checkzone, rejects SOA
        serial rollback, atomically replaces the active file, and reloads BIND.
        It is intended for an external Registry Zone Writer and is deliberately
        independent of RFC 2136 updates and secondary-transfer TSIG keys.

        @returns self, for chaining API calls.
        """
        if zonename != '.' and not zonename.endswith('.'):
            zonename += '.'
        assert fullmatch(r'(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+', zonename), 'invalid receiver zone name'
        ip_address(publisher_ip)
        assert publisher_public_key.startswith('ssh-ed25519 '), 'publisher key must be an Ed25519 public key'
        assert 'BEGIN OPENSSH PRIVATE KEY' in ssh_host_private_key, 'invalid SSH host private key'
        assert ssh_host_public_key.startswith('ssh-ed25519 '), 'host key must be an Ed25519 public key'
        assert 1024 <= max_bytes <= 128 * 1024 * 1024, 'invalid maximum zone size'
        assert self.__zone_file_receiver is None, 'zone file receiver already configured'
        self.__zone_file_receiver = (
            zonename,
            publisher_ip,
            publisher_public_key.strip(),
            ssh_host_private_key.strip() + '\n',
            ssh_host_public_key.strip() + '\n',
            max_bytes,
        )
        return self

    def setRealRootNS(self) -> DomainNameServer:
        """!
        @brief set the name server to be a real root name server.

        @returns self, for chaining API calls.
        """
        self.__is_real_root = True

        return self

    def setInclude(self, zonename: str, file_path: str = '/etc/bind/include/custom.local') -> DomainNameServer:
        """!
        @brief Register an include file for a hosted zone.

        When any include is registered, DomainNameService treats this DNS node
        as include-backed and skips the default global zone stanzas. This is
        required for custom BIND view-based configurations.

        @param zonename zone name.
        @param file_path include file path inside container.

        @returns self, for chaining API calls.
        """
        if zonename != '.' and not zonename.endswith('.'):
            zonename += '.'

        self.__include_paths[zonename] = file_path

        return self

    def __usesIncludeConfig(self) -> bool:
        return len(self.__include_paths) > 0

    def getIncludePath(self, zonename: str) -> Optional[str]:
        """!
        @brief Get include file path for a hosted zone.

        @param zonename zone name.

        @returns include file path or None if not configured.
        """
        if zonename != '.' and not zonename.endswith('.'):
            zonename += '.'

        return self.__include_paths.get(zonename)

    def getNode(self) -> Node:
        """!
        @brief get node associated with the server. Note that this only works
        after the services is configured.
        """
        return self.__node

    def getZones(self) -> List[str]:
        """!
        @brief Get list of zones hosted on the node.

        @returns list of zones.
        """
        zones = []
        for (z, _) in self.__zones: zones.append(z)
        return zones

    def print(self, indent: int) -> str:
        out = ' ' * indent
        (scope, _, name) = self.__node.getRegistryInfo()
        out += 'Zones on as{}/{}:\n'.format(scope, name)
        indent += 4
        for (zone, _) in self.__zones:
            out += ' ' * indent
            if zone == '' or zone[-1] != '.': zone += '.'
            out += '{}\n'.format(zone)

        return out

        
    def __getRealRootRecords(self):
        """!
        @brief Helper tool, get real-world root zone records list by
        RIPE RIS.

        @throw AssertionError if API failed.
        """
        rules = []
        rslt = requests.get(ROOT_ZONE_URL)

        assert rslt.status_code == 200, 'RIPEstat API returned non-200'
        
        rules_byte = rslt.iter_lines()
        
        for rule_byte in rules_byte:
            line_str:str = rule_byte.decode('utf-8')
            if not line_str.startswith('.'):
                rules.append(line_str)
        
        return rules


    def configure(self, node: Node, dns: DomainNameService):
        """!
        @brief configure the node.
        """
        self.__node = node

        for (_zonename, auto_ns_soa) in self.__zones:
            zone = dns.getZone(_zonename)
            zonename = zone.getName()

            if auto_ns_soa:
                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'node has not interfaces'
                addr = ifaces[0].getAddress()

                if self.__is_master:
                    dns.addMasterIp(zonename, str(addr))

                if zonename[-1] != '.': zonename += '.'
                if zonename == '.': zonename = ''

                if len(zone.findRecords('SOA')) == 0:
                    zone.addRecord('@ SOA {} {} {} 900 900 1800 60'.format('ns1.{}'.format(zonename), 'admin.{}'.format(zonename), randint(1, 0xffffffff)))

                # A hidden primary is an unpublished distribution endpoint.
                # Public secondaries add the NS and glue records instead.
                if self.__is_hidden_primary:
                    continue

                existing_ns_addr = False
                for record in zone.getRecords():
                    if record.endswith(' A {}'.format(addr)) and record.startswith('ns'):
                        existing_ns_addr = True
                        break

                if existing_ns_addr:
                    continue

                #If there are multiple zone servers, increase the NS number for ns name.
                ns_number = 1
                while (True):
                    if len(zone.findRecords('ns{}.{} A '.format(str(ns_number), zonename))) > 0:
                        ns_number +=1
                    else:
                        break

                zone.addGuleRecord('ns{}.{}'.format(str(ns_number), zonename), addr)
                zone.addRecord('ns{}.{} A {}'.format(str(ns_number), zonename, addr))
                zone.addRecord('@ NS ns{}.{}'.format(str(ns_number), zonename))
                
            if zone.getName() == "." and self.__is_real_root:
                for record in self.__getRealRootRecords():
                    zone.addRecord(record)

    def install(self, node: Node, dns: DomainNameService):
        """!
        @brief Handle the installation.
        """
        assert node == self.__node, 'configured node differs from install node. Please check if there are conflict bindings'
        node.addSoftware('bind9')
        if self.__zone_file_receiver is not None:
            assert self.__is_hidden_primary, 'zone file receiver requires a hidden primary'
            node.addSoftware('openssh-server')
        if not self.__usesIncludeConfig():
            node.setFile(
                '/etc/bind/named.conf',
                '''// Generated by seedemu DomainNameService
include "/etc/bind/named.conf.options";
include "/etc/bind/named.conf.local";
include "/etc/bind/named.conf.default-zones";
'''
            )
        else:
            node.setFile(
                '/etc/bind/named.conf',
                '''// Generated by seedemu DomainNameService
include "/etc/bind/named.conf.options";
include "/etc/bind/named.conf.local";
'''
            )
        node.setFile(
            '/etc/bind/named.conf.options',
            DomainNameServiceFileTemplates['named_options']
        )

        transfer_key_name = None
        transfer_key_path = None
        if self.__transfer_key is not None:
            transfer_key_name, transfer_key_secret = self.__transfer_key
            transfer_key_path = '/etc/bind/keys/{}.key'.format(transfer_key_name)
            node.setFile(
                transfer_key_path,
                'key "{}" {{ algorithm hmac-sha256; secret "{}"; }};\n'.format(
                    transfer_key_name, transfer_key_secret
                )
            )

        named_conf_local_parts = []
        if transfer_key_path is not None:
            named_conf_local_parts.append('include "{}";\n'.format(transfer_key_path))
        if not self.__usesIncludeConfig():
            named_conf_local_parts.append('include "/etc/bind/named.conf.zones";\n')
        for include_path in dict.fromkeys(self.__include_paths.values()).keys():
            named_conf_local_parts.append('include "{}";\n'.format(include_path))
        node.setFile('/etc/bind/named.conf.local', ''.join(named_conf_local_parts))
        node.setFile('/etc/bind/named.conf.zones', '')

        if not self.__usesIncludeConfig():
            for (_zonename, auto_ns_soa) in self.__zones:
                zone = dns.getZone(_zonename)
                zonename = filename = zone.getName()

                if zonename == '' or zonename == '.':
                    filename = 'root'
                    zonename = '.'
                zonepath = '/etc/bind/zones/{}'.format(filename)
                node.setFile(zonepath, '\n'.join(zone.getRecords()))

                if self.__is_master:
                    if self.__is_hidden_primary:
                        assert transfer_key_name is not None, 'hidden primary requires a TSIG transfer key'
                        assert self.__transfer_targets, 'hidden primary requires at least one transfer target'
                        notify_targets = ' '.join(
                            '{} key "{}";'.format(addr, transfer_key_name)
                            for addr in self.__transfer_targets
                        )
                        node.appendFile(
                            '/etc/bind/named.conf.zones',
                            'zone "{}" {{ type master; notify yes; also-notify {{ {} }}; '
                            'allow-transfer {{ key "{}"; }}; allow-query {{ none; }}; '
                            'allow-update {{ none; }}; file "{}"; }};\n'.format(
                                zonename, notify_targets, transfer_key_name, zonepath
                            )
                        )
                    else:
                        node.appendFile('/etc/bind/named.conf.zones',
                                'zone "{}" {{ type master; notify yes; allow-transfer {{ any; }}; file "{}"; allow-update {{ any; }}; }};\n'.format(zonename, zonepath)
                            )
                elif self.__primary_ip is not None or zone.getName() in dns.getMasterIp().keys():
                    master_ips = [self.__primary_ip] if self.__primary_ip is not None else dns.getMasterIp()[zone.getName()]
                    if transfer_key_name is not None:
                        primary_entries = ' '.join(
                            '{} key "{}";'.format(addr, transfer_key_name)
                            for addr in master_ips
                        )
                    else:
                        primary_entries = ' '.join('{};'.format(addr) for addr in master_ips)
                    node.appendFile('/etc/bind/named.conf.zones',
                        'zone "{}" {{ type slave; masters {{ {} }}; file "{}";  }};\n'.format(zonename, primary_entries, zonepath)
                    )
                else:
                    node.appendFile('/etc/bind/named.conf.zones',
                        'zone "{}" {{ type master; file "{}"; allow-update {{ any; }}; }};\n'.format(zonename, zonepath)
                    )

        if self.__transfer_key is not None:
            node.appendStartCommand('chown -R root:bind /etc/bind/keys')
            node.appendStartCommand('chmod 0750 /etc/bind/keys')
            node.appendStartCommand('chmod 0640 /etc/bind/keys/*.key')

        if self.__zone_file_receiver is not None:
            (
                receiver_zone,
                publisher_ip,
                publisher_public_key,
                host_private_key,
                host_public_key,
                max_bytes,
            ) = self.__zone_file_receiver
            assert receiver_zone in self.getZones(), 'receiver zone is not hosted on this server'
            receiver_filename = receiver_zone.rstrip('.')
            receiver_zone_path = '/etc/bind/zones/{}'.format(receiver_zone)
            receiver_command = '/usr/local/sbin/seedemu-install-zone-{}'.format(receiver_filename)
            node.setFile(
                receiver_command,
                '''#!/bin/sh
set -eu

zone={zone}
zone_path={zone_path}
max_bytes={max_bytes}
candidate=$(mktemp "${{zone_path}}.incoming.XXXXXX")
backup="${{zone_path}}.previous"
trap 'rm -f "$candidate"' EXIT HUP INT TERM

cat > "$candidate"
size=$(wc -c < "$candidate")
test "$size" -ge 1
test "$size" -le "$max_bytes"
named-checkzone "$zone" "$candidate" >/dev/null

serial_of() {{
    named-checkzone -D -o - "$zone" "$1" 2>/dev/null |
        awk '$4 == "SOA" {{ print $7; exit }}'
}}

new_serial=$(serial_of "$candidate")
test -n "$new_serial"
case "$new_serial" in *[!0-9]*) exit 1 ;; esac

if test -s "$zone_path"; then
    if cmp -s "$candidate" "$zone_path"; then
        exit 0
    fi
    old_serial=$(serial_of "$zone_path")
    test -n "$old_serial"
    case "$old_serial" in *[!0-9]*) exit 1 ;; esac
    test "$new_serial" -gt "$old_serial"
    cp -p "$zone_path" "$backup"
fi

chown bind:bind "$candidate"
chmod 0640 "$candidate"
mv -f "$candidate" "$zone_path"

if ! rndc reload "$zone"; then
    if test -s "$backup"; then
        mv -f "$backup" "$zone_path"
        chown bind:bind "$zone_path"
        chmod 0640 "$zone_path"
        rndc reload "$zone" || true
    fi
    exit 1
fi

rm -f "$backup"
rndc notify "$zone"
logger -t seedemu-zone-publisher "installed $zone serial $new_serial"
'''.format(
                    zone=receiver_zone,
                    zone_path=receiver_zone_path,
                    max_bytes=max_bytes,
                ),
            )
            node.setFile('/etc/ssh/ssh_host_ed25519_key', host_private_key)
            node.setFile('/etc/ssh/ssh_host_ed25519_key.pub', host_public_key)
            node.setFile(
                '/root/.ssh/authorized_keys',
                'from="{}",restrict,command="{}" {}\n'.format(
                    publisher_ip, receiver_command, publisher_public_key
                ),
            )
            node.setFile(
                '/etc/ssh/sshd_config.d/seedemu-zone-publisher.conf',
                '''PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
Match User root Address {publisher_ip}
    ForceCommand {receiver_command}
'''.format(
                    publisher_ip=publisher_ip,
                    receiver_command=receiver_command,
                ),
            )
            node.appendStartCommand('chmod 0755 {}'.format(receiver_command))
            node.appendStartCommand('chmod 0600 /etc/ssh/ssh_host_ed25519_key')
            node.appendStartCommand('chmod 0644 /etc/ssh/ssh_host_ed25519_key.pub')
            node.appendStartCommand('mkdir -p /root/.ssh /run/sshd')
            node.appendStartCommand('chmod 0700 /root/.ssh')
            node.appendStartCommand('chmod 0600 /root/.ssh/authorized_keys')
            # This node's SSH endpoint is dedicated to zone publication.  Use
            # the receiver as the login shell as well as a forced command so
            # base images that discard SSH exec requests cannot feed the zone
            # text to an interactive shell.
            node.appendStartCommand(
                'usermod --shell {} root'.format(receiver_command)
            )
            node.appendStartCommand('service ssh start')

        node.appendStartCommand('chown -R bind:bind /etc/bind/zones')
        node.appendStartCommand('service named start')
    
class DomainNameService(Service):
    """!
    @brief The domain name service.
    """

    __rootZone: Zone
    __autoNs: bool
    __masters: Dict [str, List[str]]

    def __init__(self, autoNameServer: bool = True):
        """!
        @brief DomainNameService constructor.
        
        @param autoNameServer add gule records to parents automatically.
        """
        super().__init__()
        self.__autoNs = autoNameServer
        self.__rootZone = Zone('.')
        self.__masters = {}
        self.addDependency('Base', False, False)
    
    def __autoNameServer(self, zone: Zone):
        """!
        @brief Try to automatically add NS records of children to parent zones.

        @param zone root zone reference.
        """
        if (len(zone.getSubZones().values()) == 0): return
        self._log('Collecting subzones NSes of "{}"...'.format(zone.getName()))
        for subzone in zone.getSubZones().values():
            for gule in subzone.getGuleRecords(): zone.addRecord(gule)
            self.__autoNameServer(subzone)

    def __resolvePendingRecords(self, emulator: Emulator, zone: Zone):
        zone.resolvePendingRecords(emulator)
        self._log('resloving pending records for zone "{}"...'.format(zone.getName()))
        for subzone in zone.getSubZones().values():
            self.__resolvePendingRecords(emulator, subzone)

    def _createServer(self) -> Server:
        return DomainNameServer()

    def _doConfigure(self, node: Node, server: DomainNameServer):
        server.configure(node, self)

    def configure(self, emulator: Emulator):
        self.__resolvePendingRecords(emulator, self.__rootZone)
        return super().configure(emulator)

    def _doInstall(self, node: Node, server: DomainNameServer):
        server.install(node, self)

    def getName(self):
        return 'DomainNameService'

    def getConflicts(self) -> List[str]:
        return ['DomainNameCachingService']
    
    def getZone(self, domain: str) -> Zone:
        """!
        @brief Get a zone, create it if not exist.

        This method only create the zone. Host it with hostZoneOn.

        @param domain zone name.

        @returns zone handler.
        """
        if domain == '.' or domain == '': return self.__rootZone
        path: List[str] = sub(r'\.$', '', domain).split('.')
        path.reverse()
        zoneptr = self.__rootZone
        for z in path:
            zoneptr = zoneptr.getSubZone(z)

        return zoneptr

    def getRootZone(self) -> Zone:
        """!
        @brief Get the root zone.

        @return root zone.
        """
        return self.__rootZone

    def getZoneServerNames(self, domain: str, includeHidden: bool = False) -> List[str]:
        """!
        @brief Get the names of servers hosting the given zone. This only works
        if the server was installed by using the "installByName" call.

        @param domain domain.
        @param includeHidden include hidden primary servers in the result.

        @returns list of tuple of (node name, asn)
        """
        info = []
        targets = self.getPendingTargets()

        for (vnode, sobj) in targets.items():
            server: DomainNameServer = sobj

            if server.isHiddenPrimary() and not includeHidden:
                continue

            hit = False

            normalized_domain = domain if domain == '.' or domain.endswith('.') else domain + '.'
            for zone in server.getZones():
                normalized_zone = zone if zone == '.' or zone.endswith('.') else zone + '.'
                if normalized_zone == normalized_domain:
                    info.append(vnode)
                    hit = True
                    break
            
            if hit: continue
        
        return info

    def addMasterIp(self, zone: str, addr: str) -> DomainNameService:
        """!
        @brief add master name server IP address.

        @param addr the IP address of master zone server.
        @param zone the zone name, e.g : com.

        @returns self, for chaining API calls.
        """
        if zone in self.__masters.keys():
            self.__masters[zone].append(addr)
        else:
            self.__masters[zone] = [addr]

        return self

    def setAllMasterIp(self, masters: Dict[str: List[str]]):
        """!
        @brief override all master IPs, to be used for merger. Do not use unless
        you know what you are doing.

        @param masters master dict.
        """
        self.__masters = masters

    def getMasterIp(self) -> Dict [str, List[str]]:
        """!
        @brief get all master name server IP address.

        @return list of ip address
        """
        return self.__masters

    def render(self, emulator: Emulator):
        if self.__autoNs:
            self._log('Setting up NS records...')
            self.__autoNameServer(self.__rootZone)

        super().render(emulator)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameService:\n'

        indent += 4
        out += self.__rootZone.print(indent)

        return out
