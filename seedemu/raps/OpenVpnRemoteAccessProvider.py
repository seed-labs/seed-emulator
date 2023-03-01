from seedemu.core import RemoteAccessProvider, Emulator, Network, Node
from seedemu.core.enums import NodeRole
from typing import Dict
from itertools import repeat

OpenVpnRapFileTemplates: Dict[str, str] = {}

OpenVpnRapFileTemplates['ovpn_key'] = '''\
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDnHrzd+hoeGoQn
r2kwNQA7Exsy9c0ZiJyU+Bbs7rG4MLH9JYbfJgwk4JKLbeBof2MowT3Z8Fufvrvw
caSbrqttb8SR/Fwu0llF7DgzPPgkZ220AJkhN6YkS+4dUhTdHZTMme+Juv061qAD
yOxxnE4VUwcVf/hGCBAvYO1yARGSxBjVpLnD9mh2qe5Vkk/G6HpCOznYPArn1XvW
KjdqSSx6RvUHIppiKjFXmr8OfEBKPh7geFI/hS/mV6teQneD+AqR0O1U3GWh91sm
QAeCr/fLs23RBuiMGtRLkAzJ1/rgTZXdwEyXfhRWa2GI5FD/3cjNg8TE2wRzk/jo
Onc/Hol1AgMBAAECggEBAMvIPW1XzVmHtcisEIpR4S81TIElW79MxgtPqB8m44pt
XTLAuOfey0xkurG3outgjtTrdhbIqHD0ow+BlEs0urBWoTK7GairDc3qVy9Obdjj
XUYeVOaGA7bzQDOYIQ9Jut6gSCXfutH7VcGgkmImGG8S8ycQ258cEvFDfHlN2enV
0kgHYc6764JFHMMKwCrCwlzb3AXI74PwkubevzB0sd+9iC/LJ8KsPTmVfMfOT0IG
7fnhdJgpj2yOKJsxg1j7iHxuFrQdw50XCGZ1qdACWcvTlWvjq0quIeqE9J6Zf9+9
eHwSaTe+cwaXO/pCQoWUI64YkyK6go+AW/0A0usTbw0CgYEA/vMGdYIM4EotFNUm
JMTOaKOu79ZJX3ZI338vMAjHot4XGd3GYU3R/Deb80HWDgi7LhuEg+Su0t6pg//c
IzvfiCtVP9cZG3Zf6f5I3Hyj5Hgk0kbarlt4cK0YqsaG2PecB+QojRvJOhr/8qj+
sfbO1JusScvdzV0K3ZAH2lUccesCgYEA6BKShvwfz1J7n09h2Dx5hGvTUt18yOaO
JzLPNreCooBmGZhbl2dpPf2Zsmv9iIYkv+sPJbK+1Pkf2+YCEjCBX/ttyLEeycUe
KaZ3MPPkNFSpteW9kGwt0ZQYhJ6NF+QkaCyJSVZqFI9lzeDdukFeMi1CfuDzzLkS
WSmCLO+4uh8CgYA9q7HbSOsuciL3kBva9xRq8XVGpNI42lcEYTKb7vPDrO9vnVr4
fKeX2CfMLxfFa01D+PoUIYQ8lAnzWTf5+ei3eqvzdmenYfoPkygy1Z+bi4h0qRkK
5it7LhPyc3V5FGRU8Fby007Y1GEnZMO/btFXUpTZgQwVOjV/pPCRWtc3owKBgAOp
V1p929qfiIfI7thEi/5E3T6vc+qPiKqhqJdKaes6b2Hz/23yGbz6pVQlVAi1ZRsK
EGEd4tjlXVVQ2bODxGbJRsAl20B/tawejj7dejpBI7RU/ZqrukVWOtTM05kO5mwm
V7wqet38LTUEWTs5EM1l3Wi3D+GpAdsaRo2C8r0tAoGBAPRwaJj2ejndXNSRhFs5
Em0vQpBTVnasuv2oysVJ1ZINFaCP6PgKU7a1kH9j+U1/tdm+QmUJefVM/jM8pIIC
PWXuDxX2aQsS31Gk3R/Hev3lvBkZTrWiSVwnyHWD1IGcUy1DJhjEQ0u/KKT/Ardg
PF9Izl/W0GZPOJu6oPEm7uHR
-----END PRIVATE KEY-----
'''

OpenVpnRapFileTemplates['ovpn_ca'] = '''\
-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgIUIi0QTek+n8sw7EWQeVuFBB45jI0wDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwHU0VFRExBQjAgFw0yMzAzMDExODI2MTNaGA8yMDczMDIx
NjE4MjYxM1owEjEQMA4GA1UEAwwHU0VFRExBQjCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAKHVnm+y+pUE6IweAd+FJ2cgLknpDKMXVtINjnet1owFJv/G
J3KI0aGWTOlE/Z05m/QnJsif0KoakDkpTW8YBT7D2jffByANELkAPWi4KeS9/u4y
tn8mnzwTRmWp0AxXeB80se2sSnfXJoA+/5U6H76Keead3+gkkLQfjslxrW7QYT5I
EQRSZxZ9B01qwS/9/5+NBe4VysHquzlZ4kY7/BrzumdzYG5hra+sCfM6qjX1KPZt
dUdNahjpO8IY8MbB0QnYtezDrTWUrdE7/Y9aBcDabqOKnkz39/MgHmk8oGXY079G
BO50KyZoUs9I5AZV/hsuts/8WdN3eu2DlVjzDFUCAwEAAaOBjDCBiTAdBgNVHQ4E
FgQU+fjN6LDe+n1VMp0T39bv5Hhr3ekwTQYDVR0jBEYwRIAU+fjN6LDe+n1VMp0T
39bv5Hhr3emhFqQUMBIxEDAOBgNVBAMMB1NFRURMQUKCFCItEE3pPp/LMOxFkHlb
hQQeOYyNMAwGA1UdEwQFMAMBAf8wCwYDVR0PBAQDAgEGMA0GCSqGSIb3DQEBCwUA
A4IBAQAddpMVHoz8Og3o4dvIXj7aSNPzj9XoAVhPyEnnE8EfRRqtWbt+3tSSKxGL
xAVXH/e/2/whcXTgBfbwn20/bVfOLQdzTgKszSducQPCD61k+OGAXR45xtNBcvNr
BHkeqOMAu5nmn9Dlm5VWCmbJFBxTu/PPUxDv5y0Z/CwaoweKunvLCpmdqfDl6ejk
lf9ipMCEV73D+WX/vdfD5VGoLIZbZzUgfjoRP54t+FbZav0LYpuU3DI83CvO/pzJ
2QOUJYOd6gNn+h2HA0dacDRCpJnLFUUsKn7RhK4pyhRTtXz8vndOHAEm0plonqeT
vgv5PvXzjCVY71b1ZrjHo0SUDGRC
-----END CERTIFICATE-----
'''

OpenVpnRapFileTemplates['ovpn_cert'] = '''\
-----BEGIN CERTIFICATE-----
MIIDYjCCAkqgAwIBAgIRAI0hz1w7O33tlaZ9XBm1WO8wDQYJKoZIhvcNAQELBQAw
EjEQMA4GA1UEAwwHU0VFRExBQjAgFw0yMzAzMDExODI2NTJaGA8yMDczMDIxNjE4
MjY1MlowETEPMA0GA1UEAwwGc2VydmVyMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A
MIIBCgKCAQEA5x683foaHhqEJ69pMDUAOxMbMvXNGYiclPgW7O6xuDCx/SWG3yYM
JOCSi23gaH9jKME92fBbn7678HGkm66rbW/EkfxcLtJZRew4Mzz4JGdttACZITem
JEvuHVIU3R2UzJnvibr9OtagA8jscZxOFVMHFX/4RggQL2DtcgERksQY1aS5w/Zo
dqnuVZJPxuh6Qjs52DwK59V71io3akksekb1ByKaYioxV5q/DnxASj4e4HhSP4Uv
5lerXkJ3g/gKkdDtVNxlofdbJkAHgq/3y7Nt0QbojBrUS5AMydf64E2V3cBMl34U
VmthiORQ/93IzYPExNsEc5P46Dp3Px6JdQIDAQABo4GxMIGuMAkGA1UdEwQCMAAw
HQYDVR0OBBYEFMCoQZ9XQTl5kZ5nz330ctV/F5OjME0GA1UdIwRGMESAFPn4zeiw
3vp9VTKdE9/W7+R4a93poRakFDASMRAwDgYDVQQDDAdTRUVETEFCghQiLRBN6T6f
yzDsRZB5W4UEHjmMjTATBgNVHSUEDDAKBggrBgEFBQcDATALBgNVHQ8EBAMCBaAw
EQYDVR0RBAowCIIGc2VydmVyMA0GCSqGSIb3DQEBCwUAA4IBAQA6HrnPfq7dgJYj
raMHI9bt2wXVaOg5n3wXPXBPxF+Elzq7JvssOADnEoJNkGkvyCa3xPuR/rFjhEtU
z/gH7/7EpquJnywhpMsDoZElR6hXeGT3iqk/iRlgczNgCC08aIxb8FiW5UqNw8up
CX0tSqVoPuKT0ETaORTVX8f3Wy4GI1dB5fFTpWgjIW2dXZdeaesfNFXAdQqXbPRn
NklfZ7UDTMHUnl+C3FBpnt3Pi05JlYn8yb2HMxRPqIhvTyjRyGwao3Y09KHGxJ2l
ZUmC9q7UPWVQqlBrfUMZoU+BD5a9ZzvZ1T7aFVtV23WgDrdRPwO0l3SGqPs6QrXP
MBV5ibZ7
-----END CERTIFICATE-----
'''

OpenVpnRapFileTemplates['ovpn_server_config'] = '''\
mode server
tls-server
verb 3
<key>
{key}
</key>
<ca>
{ca}
</ca>
<cert>
{cert}
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

OpenVpnRapFileTemplates['ovpn_startup_script'] = '''\
#!/bin/bash
[ ! -d /dev/net ] && mkdir /dev/net
mknod /dev/net/tun c 10 200 > /dev/null 2>&1
openvpn --config /ovpn-server.conf &
while ! ip li sh tap0 > /dev/null 2>&1; do sleep 1; done
ip li set tap0 up
addr="`ip -br ad sh "$1" | awk '{ print $3 }'`"
ip addr fl "$1"
brctl addbr br0
brctl addif br0 "$1"
brctl addif br0 tap0
ip addr add "$addr" dev br0
ip li set br0 up
'''

class OpenVpnRemoteAccessProvider(RemoteAccessProvider):

    __cur_port: int
    __naddrs: int

    __ovpn_ca: str
    __ovpn_cert: str
    __ovpn_key: str


    def __init__(self, startPort: int = 65000, naddrs: int = 8, ovpnCa: str = None, ovpnCert: str = None, ovpnKey: str = None):
        """!
        @brief OpenVPN remote access provider constructor.

        if you do not set ca/cert/key, builtin ones will be used. to connect, 
        use the client configuration under misc/ folder. 

        @param startPort (optional) port number to start assigning from for
        port forwarding to the open server. 
        @param naddrs number of IP addresses to assign to client pool.
        @param ovpnCa (optional) CA to use for openvpn.
        @param ovpnCert (optional) server certificate to use for openvpn.
        @param ovpnKey (optional) server key to use for openvpn.
        """
        super().__init__()

        self.__cur_port = startPort
        self.__naddrs = naddrs
        self.__ovpn_ca = ovpnCa
        self.__ovpn_cert = ovpnCert
        self.__ovpn_key = ovpnKey
    
    def getName(self) -> str:
        return 'OpenVpn'

    def configureRemoteAccess(self, emulator: Emulator, netObject: Network, brNode: Node, brNet: Network):
        self._log('setting up OpenVPN remote access for {} in AS{}...'.format(netObject.getName(), brNode.getAsn()))

        brNode.addSoftware('openvpn')
        brNode.addSoftware('bridge-utils')

        addrstart = addrend = netObject.assign(NodeRole.Host)
        for i in repeat(None, self.__naddrs - 1): addrend = netObject.assign(NodeRole.Host)

        brNode.setFile('/ovpn-server.conf', OpenVpnRapFileTemplates['ovpn_server_config'].format(
            addressStart = addrstart,
            addressEnd = addrend,
            addressMask = netObject.getPrefix().netmask,
            key = self.__ovpn_key if self.__ovpn_key != None else OpenVpnRapFileTemplates['ovpn_key'],
            ca = self.__ovpn_ca if self.__ovpn_ca != None else OpenVpnRapFileTemplates['ovpn_ca'],
            cert = self.__ovpn_cert if self.__ovpn_cert != None else OpenVpnRapFileTemplates['ovpn_cert']
        ))

        brNode.setFile('/ovpn_startup', OpenVpnRapFileTemplates['ovpn_startup_script'])

        # note: ovpn_startup will invoke interface_setup, and replace interface_setup script with a dummy. 
        brNode.appendStartCommand('chmod +x /ovpn_startup')
        brNode.appendStartCommand('/ovpn_startup {}'.format(netObject.getName()))

        brNode.appendStartCommand('ip route add default via {} dev {}'.format(brNet.getPrefix()[1], brNet.getName()))

        brNode.joinNetwork(brNet.getName())
        brNode.joinNetwork(netObject.getName())

        brNode.addPort(self.__cur_port, 1194, 'udp')

        self.__cur_port += 1