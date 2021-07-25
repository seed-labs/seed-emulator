from seedemu.core import RemoteAccessProvider, Emulator, Network, Node
from seedemu.core.enums import NodeRole
from typing import Dict
from itertools import repeat

OpenVpnRapFileTemplates: Dict[str, str] = {}

OpenVpnRapFileTemplates['ovpn_key'] = '''\
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
'''

OpenVpnRapFileTemplates['ovpn_ca'] = '''\
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
'''

OpenVpnRapFileTemplates['ovpn_cert'] = '''\
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

        if you do not set ca/cert/key, bulitin ones will be used. to connect, 
        use the client configuration under misc/ folder. 

        @param startPort (optional) port number to start assigning from for
        port fowarding to the open server. 
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