from .Layer import Layer
from .DomainNameService import DomainNameService
from typing import Set, Dict, List
from seedsim.core import ScopedRegistry, Node

DnssecFileTemplates: Dict[str, str] = {}

DnssecFileTemplates['enable_dnssec_script'] = """\
#!/bin/bash
rm -fr /etc/bind/keys 
mkdir /etc/bind/keys
cd /etc/bind/keys
rndc freeze
while read -r zonename; do {
    [ -z "$zonename" ] && continue
    zonefile="$zonename"
    [ "$zonename" = "." ] && zonefile="root"
    echo "setting up DNSSEC for "$zonename"..."
    sed -i 's|zone "'"$zonename"'" { type master; file "/etc/bind/zones/'"$zonefile"'"; allow-update { any; }; };|zone "'"$zonename"'" { type master; file "/etc/bind/zones/'"$zonefile"'"; allow-update { any; }; key-directory "/etc/bind/keys"; auto-dnssec maintain; inline-signing yes; };|' /etc/bind/named.conf.zones
    dnssec-keygen -a NSEC3RSASHA1 -b 2048 -n ZONE "$zonename"
    dnssec-keygen -f KSK -a NSEC3RSASHA1 -b 4096 -n ZONE "$zonename"
}; done < /dnssec_zones.txt

chown -R bind:bind /etc/bind/keys
rndc thaw
rndc reload

while read -r zonename; do {
    [ -z "$zonename" ] && continue
    [ "$zonename" = "." ] && continue
    pzonename="`tr '.' '\\n' <<< "$zonename" | sed '1d' | tr '\\n' '.' | sed -e 's/\\.\\.$/./'`"
    while true; do {
        pns="`dig +short NS "$pzonename"`" || pns=''
        [ -z "$pns" ] && echo "cannot get NS for parent zone ($pzonename), retrying in 1 second..." || break
        sleep 1
    }; done
    dig +short NS "$pzonename" | while read -r ns; do dig +short "$ns"; done | while read -r nsaddr; do {
        dss="`dig @127.0.0.1 dnskey "$zonename" | dnssec-dsfromkey -f- "$zonename" | sed 's/IN/300/; s/^/update add /;'`"
        echo "$dss"
        echo "submiting DS record to parent zone $nsaddr..."
        while true; do {
            cat << UPDATE | nsupdate && echo "parent accepted the update." && break
server $nsaddr
zone $pzonename
$dss
send
UPDATE
            echo "submission failed, retrying in 1 second..."
            sleep 1
        }; done
    };done
}; done < /dnssec_zones.txt
"""

class Dnssec(Layer):
    """!
    @brief The Dnssec (DNSSEC) layer.

    This layer helps setting up DNSSEC. It works by signing the zones and send
    the DS record to parent(s) with nsupdate. Note that to build a DNSSEC
    infrastructure, you will need to sign the entire chain. 
    """

    __zonenames: Set[str]
    __reg = ScopedRegistry('seedsim')

    def __init__(self):
        """!
        @brief Dnssec layer constructor.
        """
        self.__zonenames = set()

    def getName(self):
        return 'Dnssec'
    
    def getDependencies(self) -> List[str]:
        return ['DomainNameService']

    def enableOn(self, zonename: str):
        """!
        @brief Enable DNSSEC on the given zone.

        @param zonename zonename. 
        """
        if zonename[-1] != '.': zonename += '.'
        self.__zonenames.add(zonename)

    def onRender(self):
        dns: DomainNameService = self.__reg.get('layer', 'DomainNameService')
        nodes: Set[Node] = set()
        for zonename in self.__zonenames:
            self._log('Looking for server hosting "{}"...'.format(zonename))
            server = dns.getServerByZoneName(zonename)
            
            assert server != None, 'no server found for dnssec-enabled zone {}'.format(zonename)
            node = server.getNode()
            (scope, _, name) = node.getRegistryInfo()
            self._log('Setting up DNSSEC for "{}" on as{}/{}'.format(zonename, scope, name))
            nodes.add(node)
            node.appendFile('/dnssec_zones.txt', '{}\n'.format(zonename))

        for node in nodes:
            node.appendFile('/enable_dnssec', DnssecFileTemplates['enable_dnssec_script'])
            node.addStartCommand('chmod +x /enable_dnssec')
            node.addStartCommand('/enable_dnssec')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DnssecLayer:\n'

        indent += 4

        out += ' ' * indent
        out += 'DNSSEC-enabled zones:\n'

        for zonename in self.__zonenames:
            out += ' ' * indent
            out += '{}\n'.format(zonename)

        return out
            

