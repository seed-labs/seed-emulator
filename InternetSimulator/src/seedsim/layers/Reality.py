from .Layer import Layer
from .Base import Base
from .Routing import Router
from seedsim.core import Node, Network, AutonomousSystem, ScopedRegistry, Registry
from seedsim.core.enums import NodeRole
from typing import List, Dict, Tuple
from itertools import repeat
import requests

RIS_PREFIXLIST_URL = 'https://stat.ripe.net/data/announced-prefixes/data.json'

RealityFileTemplates: Dict[str, str] = {}

RealityFileTemplates['configure_script'] = '''\
#!/bin/bash
gw="`ip rou show default | cut -d' ' -f3`"
sed -i 's/!__default_gw__!/'"$gw"'/g' /etc/bird/bird.conf
'''

RealityFileTemplates['ovpn_server_config'] = '''\
mode server
tls-server
verb 3
<key>
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDGyzUXoj+wffTx
2S1KHxZ63YNlzJxUVoWpgAcjIibhHkc8mN7qdyUOkamateSr29JDVSgrBDFJbx01
rA9x/Yn7//JV5+Zll8izERJVyIfqdkfFQA7f7Jg3bXBSOG/LhKFgQqB5JI/hLGc1
2XP+x9ht+gY3jVF9caDT6GED495orSJQVP3hz1RoHxW0KY7p+LQ/HG2yQs9KBm84
sv4irXSVAdcls/HkbOka6oNiCpBLK7cHNqsui6TGA/EI+QidHAd2ABB/lIxCuZQs
+G5OpxpSGXew59ORjsDL2mSIodQxozseH7obWQ4H8SbNORYGf28aGv18XGzPjdmw
Zbh9pf2zAgMBAAECggEAPcqeRylcqKyOPbqm9Dozj59ZH4R5N1HpnCU6krYj5ae2
tuRBrhm4wA2Q7ZEKck0Sz3Eh2jUkaNIL/0nrRyBrCpSlLAS4Pe3vKZHt5BJABSYc
6vgdZ4cwTVJMLpJyVY11Z+lt3hn6SyC1OCzOfGx8HrsvwYbAxMBUIGpD9aSX1msm
IVRDRp9iZTx2xuJg9uwZf5nBLi88Ku4833KlCWOQaRrEpx/cH+goi1MU7VABxJpX
KFbsQSmw9qAlrS4CofGL1FWZD/TGr2RpQ/GfMwCw9iBQaoIGkg+t/4xJdOQRSWmF
MBZ9dqTex34re0wBVeD5s4rbEEH9mIYF9q4HO0MQ8QKBgQDuYRFgaNxEOV52Ho6F
SF2kHJiIADlQK68+DZ508omChqfLBnq7xYCyP/Dzne2NgOO4mbLmMYKRo/jztEMW
TVq+HAg6TwlcXpyhjwwgMVSGsorkn19boKP+z5W8Y7IvTRXXhqBVHpuToUelTEqT
GTiyRTW38OnH/jFysGN7iKJ1SQKBgQDVfQ0khIPorVcmO/OV9j4tB6TgIQw4Gdlf
+KfGpvpWzxZ6b3gbBFcXB6raHo7acVtJezL0+vM07xUz4S/yvUkmZFFe6Q1/YxZx
P7keUJjJzSigBvVyku0YLcczmMVkWxXoepxEKS9d0cH8ikZ7910WOdafpdmk0uyN
CzGA1vmnGwKBgHlACG2oiLlvENw2CLpEp9TM8sziiER+I+IFXV8Q6t7ojTqYrh8K
g76nBXF1GBrMv4frLfMmpcpcxEl5nFIgwJJIgerevt0sBrGqqDlLvjnRYRKO+hsK
J8B5aClt8Hlc1UpOYQlKy0mZVG8A0kHmJ0+OIpfQQ6mFYzN6AvAX/MJ5AoGBAJV+
j+l2cfhJCbHYYWYtnLRjmezot2nBkBpIQRQ2cS7ArPjnfa9Nhr61u8opg9crccUu
5CvwXsY+dRZzJeRQ8BxWOzS+9ZiyhlCfUr4LqjIF2+DTfqTQhf5ccBWNcQwpTFoT
IcIJJQYJkFGLcnf0a9bYgZYhyRpGKSdLI0sZPpDpAoGBAL3V17HDfe9pPE2MhfKf
1Djo8SLQoK5slFV1ayqC1iVFEavnRuDpE0IJdT1wOmZbUUGdJY9H1vvXrDT5wYJn
/HkA3KHQnuSI63NKURYwg93YpKPNvrQeDtu69iKP1u/CDmlYyN3ocO0wBx/lcqog
baY6j2daX4LF6wipbN8nmu+d
-----END PRIVATE KEY-----
</key>
<ca>
-----BEGIN CERTIFICATE-----
MIIDSzCCAjOgAwIBAgIUeBWmET3RvnXU1V9YVprLzlcT/BAwDQYJKoZIhvcNAQEL
BQAwFjEUMBIGA1UEAwwLRWFzeS1SU0EgQ0EwHhcNMTkxMDAyMjAyMjM1WhcNMjkw
OTI5MjAyMjM1WjAWMRQwEgYDVQQDDAtFYXN5LVJTQSBDQTCCASIwDQYJKoZIhvcN
AQEBBQADggEPADCCAQoCggEBAKj8Dq3JtARmANzvm4KbqU3yfxySTA+y9CFZX+5H
WmpS9AvENEWNtAkawkW5AH7LXAuEl1JckXtTuz2+Vgtd8bo3se34mZ3mDHoOYi28
8hBj1Y4NpguKcLy9xpkTxIxen5oAfth4KysL+d2UuYpKdR2MwEDsX7UgO6PuRW4a
Eem3NG0ubjI/MQDrVoA61a288sbs+zaeypcWASHpnllAOe0Lfpo78Hb+oUfakBxq
pcUH+u4Q8ZSzK11C1+Pp7kycUOx1+0pckc57tJmfvBVuODQ7QtrwfaF8gV0OvGW7
NerVzahNQx0MgNL5k3Q1FRd2/8I1J4chI+WO5r121iGfkeUCAwEAAaOBkDCBjTAd
BgNVHQ4EFgQU5e2+dqX3RoN3yQRmM+lHwmMjY2MwUQYDVR0jBEowSIAU5e2+dqX3
RoN3yQRmM+lHwmMjY2OhGqQYMBYxFDASBgNVBAMMC0Vhc3ktUlNBIENBghR4FaYR
PdG+ddTVX1hWmsvOVxP8EDAMBgNVHRMEBTADAQH/MAsGA1UdDwQEAwIBBjANBgkq
hkiG9w0BAQsFAAOCAQEAiafzuzWAhIPeeGF7pY4LFlN/pJz6tgM0h2zflMYKLIgD
s3pjo6xB4gg4XWWl7QVNhU9uFvqvKttZ4a5eM8aaBhSYSfRjlkreidi08L9AgLXv
1bClX9mzm52sYxGoWOYYZcvYVADTk06sah0CV9q1ZnWFzLrgfS4bcpJkNfCGh5eA
XQqfdCFTV3mcr0A/YrO73pJC80819uDoNRuwfeAKyNNcJB3nReIAVM4FLJ4kKX8s
6IjypBv+ZX2jhli+3xIOKUOKNEwEYpDRr78TMMN1m7NA1Z1rdxN7McvaE/6RXy5Z
P4qwZ5v373hLfW+/YlQ2gb8UMXAK2G025a5754E0Ag==
-----END CERTIFICATE-----
</ca>
<cert>
-----BEGIN CERTIFICATE-----
MIIDbzCCAlegAwIBAgIRAKZMH5L7JUN8QqloCQr9ZUgwDQYJKoZIhvcNAQELBQAw
FjEUMBIGA1UEAwwLRWFzeS1SU0EgQ0EwHhcNMTkxMDAyMjAyMzI2WhcNMjIwOTE2
MjAyMzI2WjAaMRgwFgYDVQQDDA8xMjguMjMwLjIxMC4xNTEwggEiMA0GCSqGSIb3
DQEBAQUAA4IBDwAwggEKAoIBAQDGyzUXoj+wffTx2S1KHxZ63YNlzJxUVoWpgAcj
IibhHkc8mN7qdyUOkamateSr29JDVSgrBDFJbx01rA9x/Yn7//JV5+Zll8izERJV
yIfqdkfFQA7f7Jg3bXBSOG/LhKFgQqB5JI/hLGc12XP+x9ht+gY3jVF9caDT6GED
495orSJQVP3hz1RoHxW0KY7p+LQ/HG2yQs9KBm84sv4irXSVAdcls/HkbOka6oNi
CpBLK7cHNqsui6TGA/EI+QidHAd2ABB/lIxCuZQs+G5OpxpSGXew59ORjsDL2mSI
odQxozseH7obWQ4H8SbNORYGf28aGv18XGzPjdmwZbh9pf2zAgMBAAGjgbMwgbAw
CQYDVR0TBAIwADAdBgNVHQ4EFgQU287Mv795myOlgDVBLSQ2uOR8FpYwUQYDVR0j
BEowSIAU5e2+dqX3RoN3yQRmM+lHwmMjY2OhGqQYMBYxFDASBgNVBAMMC0Vhc3kt
UlNBIENBghR4FaYRPdG+ddTVX1hWmsvOVxP8EDATBgNVHSUEDDAKBggrBgEFBQcD
ATALBgNVHQ8EBAMCBaAwDwYDVR0RBAgwBocEgObSlzANBgkqhkiG9w0BAQsFAAOC
AQEAZdpzYBUlLCGqT2U6TdWlLczVTmvZ/d21eV9X73N0/X4wgU2WtG6YASznwcIE
EfMYuGid2nQLA6BLjQ3EX/EppRP0D+LVTyOT/Z2kvrFP6v7nQztWFFk5W7eJRHNR
47FctlAWataSeQxiMeKKtzoJ9w6Y9bV0jB80oFfWDEMFcx4BwwqYSY9l7B/dOFxK
EjYDvjaEiQHXjeVr+M/FdtdggAleUGfOvohgA6QDM/NKgTzpbxiZMrlYjztCIs5i
jPICvnaaLqUJJLhdX8vmEyZ5lcReCfA+i823AHzimHNVJQGDZAZjFWeZS+X6S7lc
z/aTAQLl/Nl/8Z7o8TQzH5NTdg==
-----END CERTIFICATE-----
</cert>
<dh>
-----BEGIN DH PARAMETERS-----
MIIBCAKCAQEArera3K9jUe2CU/bSemBTUV802sd7EoFe7R0ci4WWcpZ4kLIht6wB
YAi6jpC/q3BEkGuSJwZYiY3ILLAahuJiVyzPwvfWxY/HCnOnbAM5hN6wo95lZlQT
XYkXbr27PVVmW8dn7OE3fuvE34PSfaP97cU+qUajys1Md8bWdg7KSo2eoeB+fVl5
MEW59Ge6iAVX4HT8j5hqzMUKiak+sVuc6qBSTpI7lSC6cQZ8+hW4o6nKdXDwVLaZ
0C1Ytj/HFA2U+oAwHtU66jVD6aUWp4FHCB9foZKWiOqMzLIkA6BK6BkzzTxKvK0U
xWctlE3wWUpV9XsDIZ5wgp2D3wK16IH9uwIBAg==
-----END DH PARAMETERS-----
</dh>
<tls-auth>
-----BEGIN OpenVPN Static key V1-----
2f7d9e47a8f9843c66821d9fcf9f9b5d
5d04e1d401f855593f0348e3b78cf746
4a2fb78a5c966b0bd601f4886d07ce2e
927c6e60359a3eff91df118da1260604
d8902cf6447e4568e3525962aa34d878
10c848b92a658be9f8fe948e1cc060b1
09fd6efe2598fc4be0faae0dfb62dadc
860c62c126a1c8af67d00b1e26342bbc
889700c790d0159de2e27eb005c08e49
0a8db7910241031a86b8feb23317e6c0
d47d528ee78b190baee442359b4ed243
9c1d99e724e7156de525ddd94145b588
e466272c2ab0b8d39b3da74d5794d6d4
00aff34bfa61f78ffb535d4b27c818ea
4e4b8a9efc6927b18a8e784d9236c3e2
c74e92120ac39909f3fe5da198f4e661
-----END OpenVPN Static key V1-----
</tls-auth>
key-direction 0
keepalive 10 60
persist-key
duplicate-cn
proto udp
port 1194
status /tmp/openvpn-status.log
user nobody
group nogroup
client-to-client
dev tap0
ifconfig-pool {addressStart} {addressEnd} {addressMask}
'''

RealityFileTemplates['ovpn_startup_script'] = '''\
#!/bin/bash
[ ! -d /dev/net ] && mkdir /dev/net
mknod /dev/net/tun c 10 200
openvpn --config /ovpn-server.conf &
while ! ip li sh tap0; do sleep 1; done
ip li set tap0 up
addr="`ip -br ad sh eth0 | awk '{ print $3 }'`"
gw="`ip rou sh default | cut -d' ' -f3`"
ip addr fl eth0
brctl addbr br0
brctl addif br0 eth0
brctl addif br0 tap0
ip addr add "$addr" dev br0
ip li set br0 up
ip rou add default via "$gw" dev br0
'''

class RealWorldRouter(Router):
    """!
    @brief RealWorldRouter class.

    This class extends the router node to supporting routing prefix to real
    world.

    @todo realworld access.
    """

    __realworld_routes: List[str]
    __sealed: bool
    __hide_hops: bool

    def initRealWorld(self, hideHops: bool):
        """!
        @brief init RealWorldRouter.
        """
        if hasattr(self, '__sealed'): return
        self.__realworld_routes = []
        self.__sealed = False
        self.__hide_hops = hideHops
        self.addSoftware('iptables')
        self.setFile('/rw_configure_script', RealityFileTemplates['configure_script'])
        self.addStartCommand('chmod +x /rw_configure_script')
        self.addStartCommand('/rw_configure_script')

    def addRealWorldRoute(self, prefix: str):
        """!
        @brief Add real world route.

        @param prefix prefix.
        
        @throws AssertionError if sealed.
        """
        assert not self.__sealed, 'Node sealed.'
        self.__realworld_routes.append(prefix)

    def getRealWorldRoutes(self) -> List[str]:
        """!
        @brief Get list of real world prefixes.

        @returns list of prefixes.
        """
        return self.__realworld_routes

    def seal(self):
        """!
        @brief seal the realworld router.

        Use this method to "seal" the router (add static protocol.) No new real
        world routes can be added once the node is sealed.
        """
        if self.__sealed: return
        self.__sealed = True
        if len(self.__realworld_routes) == 0: return
        self.addTable('t_rw')
        statics = '\n    ipv4 { table t_rw; import all; };\n    route ' + ' via !__default_gw__!;\n    route '.join(self.__realworld_routes)
        statics += ' via !__default_gw__!;\n'
        for prefix in self.__realworld_routes:
            # nat matched only
            self.appendFile('/rw_configure_script', 'iptables -t nat -A POSTROUTING -d {} -j MASQUERADE\n'.format(prefix))
            
            if self.__hide_hops:
                # remove realworld hops
                self.appendFile('/rw_configure_script', 'iptables -t mangle -A POSTROUTING -d {} -j TTL --ttl-set 64\n'.format(prefix))

        self.addProtocol('static', 'real_world', statics)
        self.addTablePipe('t_rw', 't_bgp')
        # self.addTablePipe('t_rw', 't_ospf') # TODO


    def print(self, indent: int) -> str:
        out = super(RealWorldRouter, self).print(indent)
        indent += 4

        out += ' ' * indent
        out += 'Real-world prefixes:\n'

        indent += 4
        for prefix in self.__realworld_routes:
            out += ' ' * indent
            out += '{}\n'.format(prefix)
        

        return out

class Reality(Layer):
    """!
    @brief The Reality.

    Reality Layer provides different ways to connect from and to the real world. 
    """

    __rwnodes: List[RealWorldRouter]
    __rwnets: List[Tuple[Network, int]]
    __reg = ScopedRegistry('seedsim')
    __hide_hops: bool

    def __init__(self, hideHops: bool = True):
        """!
        @brief Reality constructor.

        @param hideHops hide realworld hops from traceroute (by setting TTL = 64
        to all real world dsts on POSTROUTING)
        """
        self.__rwnodes = []
        self.__rwnets = []
        self.__hide_hops = hideHops

    def getName(self):
        return 'Reality'
    
    def getDependencies(self) -> List[str]:
        return ['Ebgp']

    def getPrefixList(self, asn: int) -> List[str]:
        """!
        @brief Helper tool, get real-world prefix list for an ans by RIPE RIS.

        @param asn asn.
        
        @throw AssertionError if API failed.
        """
        self._log('loading real-world prefix list for as{}...'.format(asn))

        rslt = requests.get(RIS_PREFIXLIST_URL, {
            'resource': asn
        })

        assert rslt.status_code == 200, 'RIPEstat API returned non-200'
        
        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'
 
        return [p['prefix'] for p in json['data']['prefixes'] if ':' not in p['prefix']]

    def createRealWorldRouter(self, asobj: AutonomousSystem, nodename: str = 'rw', prefixes: List[str] = None) -> Node:
        """!
        @brief add a router node that routes prefixes to the real world.

        Connect the node to an IX, or to other nodes in IX via IBGP, to get the
        routes into simulation.

        @param asobj AutonomousSystem to add this node to.
        @param nodename name to use for the realworld router.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        rwnode: RealWorldRouter = asobj.createRouter(nodename)
        rwnode.__class__ = RealWorldRouter
        rwnode.initRealWorld(self.__hide_hops)
        if prefixes == None: prefixes = self.getPrefixList(asobj.getAsn())
        for prefix in prefixes:
            rwnode.addRealWorldRoute(prefix)
        self.__rwnodes.append(rwnode)

        return rwnode

    def getRealWorldRouters(self) -> List[RealWorldRouter]:
        """!
        @brief Get list of real-world routers.

        @returns list of real world routers.
        """
        return self.__rwnodes

    def enableRealWorldAccess(self, net: Network, naddrs: int = 8):
        """!
        @brief Setup VPN server for real-world clients to join a simulated
        network.

        @param net network.
        @param naddrs number of IP addresses to assign to client pool.
        """
        self.__rwnets.append((net, naddrs))

    def enableRealWorldAccessByName(self, asn: int, netname: str, naddrs: int = 8):
        """!
        @brief Setup VPN server for real-world clients to join a simulated
        network.

        @param asn asn of the network owner.
        @param netname name of the network.
        @param naddrs number of IP addresses to assign to client pool.
        """
        self.enableRealWorldAccess(Registry().get(str(asn), 'net', netname))

    def onRender(self):
        # @todo ifconfig-pool
        for node in self.__rwnodes:
            self._log('Setting up real-world router as{}/{}...'.format(node.getAsn(), node.getName()))
            node.seal()

        cur_port = 65000
        for (net, poolsz) in self.__rwnets:
            (scope, _, name) = net.getRegistryInfo()
            self._log('Setting up real-world bridge for network as{}/{}...'.format(scope, name))
            snode_name = 'br-{}'.format(name)
            snode = Node(snode_name, NodeRole.Host, 0, 'seedsim')
            snode.joinNetwork(net)
            addrstart = addrend = net.assign(NodeRole.Host)
            for i in repeat(None, poolsz - 1): addrend = net.assign(NodeRole.Host)
            ScopedRegistry(scope).register('snode', snode_name, snode)
            #self.__reg.register('snode', snode_name, snode)
            snode.addSoftware('openvpn')
            snode.addSoftware('bridge-utils')
            snode.setFile('/ovpn-server.conf', RealityFileTemplates['ovpn_server_config'].format(
                addressStart = addrstart,
                addressEnd = addrend,
                addressMask = net.getPrefix().netmask
            ))
            snode.setFile('/ovpn_startup', RealityFileTemplates['ovpn_startup_script'])
            snode.addStartCommand('chmod +x /ovpn_startup')
            snode.addStartCommand('/ovpn_startup {}'.format(name))
            snode.addPort(cur_port, 1194, 'udp')
            cur_port += 1

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RealityLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'Real-world router nodes:\n'

        indent += 4
        for node in self.__rwnodes:
            out += node.print(indent)

        indent -= 4
        out += ' ' * indent
        out += 'Bridged networks:\n'
        indent += 4
        for (net, naddr) in self.__rwnets:
            (scope, _, name) = net.getRegistryInfo()
            out += ' ' * indent
            out += 'as{}/{}: {} Addresses'.format(scope, name, naddr)

        return out
