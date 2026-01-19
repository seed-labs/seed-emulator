from ipaddress import IPv4Address
from seedemu import *
import psutil
import os
import socket

VPN_SCRIPT = '''\
#!/bin/bash

if [ $# -ge 3 ]; then
    REMOTE_IP=$1
    REMOTE_PORT=$2
    DEFAULT_ROUTER=$3

    if ! command -v openvpn &> /dev/null; then
        echo "OpenVPN not installed, trying to install..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y openvpn
        fi
    fi

    DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
    if [ -z "$DEFAULT_IFACE" ]; then
        echo "Unable to detect default interface" >&2
        exit 1
    fi
    echo "Detected interface: $DEFAULT_IFACE"

    echo "Connecting... wait a moment"
    sudo openvpn --config ovpn-client.ovpn --remote $REMOTE_IP $REMOTE_PORT --daemon --log /tmp/openvpn.log
    sleep 5

    if ip link show tap0 > /dev/null 2>&1; then
        echo "tap0 interface exists."
        sudo ip route add $REMOTE_IP via 192.168.102.1 dev $DEFAULT_IFACE
        sudo ip route del default
        sudo ip route add default via $DEFAULT_ROUTER dev tap0
    else
        echo "tap0 interface does not exist."
    fi
else
    echo "Usage: $0 <remote_ip> <remote_port>"
    echo "No remote IP and port provided. Skipping OpenVPN connection."
    exit 3
fi
'''

LOCAL_ENV_TEMPLATE = '''\
CLONE_TEMPLATE="{clone_template}"
VM_NAME="{vm_name}"
VMID={vmid}
VM_SSH_PORT={vm_ssh_port}
VM_USERNAME="seed"
VM_PASSWORD="dees"
REMOTE_IP="{remote_ip}"
REMOTE_PORT={remote_port}
DEFAULT_ROUTER="{default_router}"
ASN={asn}
NET_NAME="{net_name}"
'''

OVPN_CONFIG = '''\
client
nobind
dev tap
remote-cert-tls server
float

<key>
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDz6CcOlfLadadF
6Ou/xIMhpuEAOs6H1NuG6N2uBIYtiVy11EqH4fHpwhnRnVEYcbieufgavT+TM3gH
9IXVXHOmAm5zgEuKMsZtPJOzPDIL8OhYXBkdIIV45NEdgjf+WOjqpNFWex7rTPk7
+0dBgcPdDvtSwsMAlT5tRMTsZaG0JAFWenZFflzlOS9f3G90hvyAjnWXyRB5iToc
ce8zdXMwdbtu97NCPo46274UrA3U//uLxydkkm3/KrJVzDEFuA6OM5rNGTgYvPxg
BDV0eTmJt1hlsZPvDnN2JNR1NRGEGGbtXm41iXY7FGSE5UUBu+W/0Xfufl3un2IM
bv4x5exRAgMBAAECggEABpk4PUfHOyvFq7mCbzy0w3tNSQFORxR2H+862BNdQewe
avjkT0rIjadnpWkZIY0qDnk/ghGun5/b1nNCD6ShqFMWg99rq8B158ykvkuZmwMY
dhN/xm7zzXJ7Sc4VD7d+DaMJ2soX6wu5Dmtc4SPOlbNrDzEfr2taNgCPR0n0lvf4
4A9DYCAkMrS9bolGzJV0toIO6dwatU6qATfRJSrh1LRN+CPIoO+NPin8Z3HjGIUI
tBHOFwwH16Z/swfjc0Fmntf3iYRkqeU5lHHZhueVidB6D77w6BiA9DtokzPEsBPx
SZsAom1oHTtm36pR4qZW/27qS8omv/Fd68sfrB/CAQKBgQD6GLVCYKPonzVlLVPZ
PybBzrvmsZ9X606QX8O2ONYSkp/i/w7SijD8Bj4Y7/uu+TFYFHJH98+rOLiJ2XDw
eMWGW/WRKwzFk4+7sbnigF2+b4atKEhRfXtQEcaq4fTHMCTkwVs4q7oHS8urvVch
BNJiQHwIcqWbmbY9u++o+ZL88QKBgQD5qgqXLULxxMvkSrA+usDtKdeNCKtMo2aD
DtzzrMsgkWX96fQHdJkGMK8trBU4P4+CPe+iOcY9+/bx1KMWg0t+MrwthAalTZp8
XFw7dCnbEBSs8L2h4PurArWLhsjAv5LcMOE+SK9yBN4l7VthgGrKtqWcJG1mobVT
gZU2bfllYQKBgQDtHyoUkj42G2Vr1YsvaoHbtaBQPU6/9DlcB4AvMDpAB8cSWRP7
qMyC14Re7oJpxpjzUwd7lsjOJYxKHuDHDyrwlhYBmpiUZ7Eam4qL53t6SJGfcZcH
tHqLUx9S+8Oya8I/JdjQpXlO251y6qVGiCTUxSEUfWbpXdb9N0gmpOKpcQKBgDid
9RTfcMT/CfXVci5nj4S47mbPRnl0vLSP1E92KgJStrxkJ7DhIiqjM7a5xX4h+9tf
TE6Pp4M69n9U5z8duyr9Omtf+1nVRWlaUJgy+aLx/J5TYc2qBah8Tss7X59GUnmY
pBvJw++pZu9W6lgsFQuva9MC98REe6haRIo5WktBAoGASWYm12Mj4specUmULl6T
BV2BtjGlMGjD6xN0W6/geaDCqas4Ig4wvquQcpOZ0QPBwE8EwN/fVqgVEAMWCJyZ
OHHi6F9XhONgVIboYAbFE5VNSzOoxQsFrUTihR1MMkXU29T+dqAGrj/rSrsGcFBX
OsRX84Pzj6TdYXekeMYuFQk=
-----END PRIVATE KEY-----
</key>
<cert>
-----BEGIN CERTIFICATE-----
MIIDTjCCAjagAwIBAgIQYxSITktu/JD+Ol/iG+3e1zANBgkqhkiG9w0BAQsFADAS
MRAwDgYDVQQDDAdTRUVETEFCMCAXDTIzMDMwMTE4MjcwOFoYDzIwNzMwMjE2MTgy
NzA4WjARMQ8wDQYDVQQDDAZjbGllbnQwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
ggEKAoIBAQDz6CcOlfLadadF6Ou/xIMhpuEAOs6H1NuG6N2uBIYtiVy11EqH4fHp
whnRnVEYcbieufgavT+TM3gH9IXVXHOmAm5zgEuKMsZtPJOzPDIL8OhYXBkdIIV4
5NEdgjf+WOjqpNFWex7rTPk7+0dBgcPdDvtSwsMAlT5tRMTsZaG0JAFWenZFflzl
OS9f3G90hvyAjnWXyRB5iTocce8zdXMwdbtu97NCPo46274UrA3U//uLxydkkm3/
KrJVzDEFuA6OM5rNGTgYvPxgBDV0eTmJt1hlsZPvDnN2JNR1NRGEGGbtXm41iXY7
FGSE5UUBu+W/0Xfufl3un2IMbv4x5exRAgMBAAGjgZ4wgZswCQYDVR0TBAIwADAd
BgNVHQ4EFgQU7vK4g5ypbdN7lEsa0ajDPfL06tswTQYDVR0jBEYwRIAU+fjN6LDe
+n1VMp0T39bv5Hhr3emhFqQUMBIxEDAOBgNVBAMMB1NFRURMQUKCFCItEE3pPp/L
MOxFkHlbhQQeOYyNMBMGA1UdJQQMMAoGCCsGAQUFBwMCMAsGA1UdDwQEAwIHgDAN
BgkqhkiG9w0BAQsFAAOCAQEAH3fLEZwp7kF8scsBsXHRU5LMVvVx2N9RbrA4oC/n
ibQldCBdluFbArlpJtfkQ3QhzHiPgI6vwzbe00qWLyXvndbmMC3ZOfS7/piW5WH9
hQu0PFkPTzf4NxwolF+KoC1D9bWMYSJNjKBkWRPrU6tgFe890psl9aJUd10ESBU2
cOC2vV6h738Td6i1pf6XFw04V00elNhdLS6Bu8hKsUdZqzPQBHkowse8CiQF86qv
CxnMsdD6Xw/U/LaoycMTiJsP3+Q7EmSd/xyKrVJ+6FfkmG0P/TiFK2Bu1Au1xOkJ
sPHpC3DSqUkC/yeJ8I8YgTj87ets/h9m57/1jzZNnOki/g==
-----END CERTIFICATE-----
</cert>
<ca>
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
</ca>
key-direction 1
<tls-auth>
#
# 2048 bit OpenVPN static key
#
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
'''

START_SCRIPT = r'''\
import os
import sys
import json
import time
import requests
import subprocess
from dotenv import load_dotenv
from vm_allocate import VMAllocate
from user_allocate import UserAllocate
from base_client import ProxmoxAPIError
from ssh_executor import SSHExecutor

def run():
    global_env_path = os.path.join(os.path.dirname(__file__), "../global.env")
    vm_env_path = os.path.join(os.path.dirname(__file__), "./config.env")

    load_dotenv(global_env_path, override=False)
    load_dotenv(vm_env_path, override=True)
    
    PVE_HOST = os.getenv("PVE_HOST")
    API_TOKEN_ID = os.getenv("API_TOKEN_ID")
    API_TOKEN_SECRET = os.getenv("API_TOKEN_SECRET")
    NODE = os.getenv("NODE")
    CLONE_TEMPLATE = os.getenv("CLONE_TEMPLATE")
    VM_NAME = os.getenv("VM_NAME")
    NEW_VMID = os.getenv("VMID")
    VM_SSH_PORT = int(os.getenv("VM_SSH_PORT", "22"))
    VM_USERNAME = os.getenv("VM_USERNAME")
    VM_PASSWORD = os.getenv("VM_PASSWORD")
    REMOTE_IP = os.getenv("REMOTE_IP")
    REMOTE_PORT = int(os.getenv("REMOTE_PORT", "65000"))
    DEFAULT_ROUTER = os.getenv("DEFAULT_ROUTER")
    ASN = os.getenv("ASN")
    NET_NAME = os.getenv("NET_NAME")
    
    required_vars = {
        "PVE_HOST": PVE_HOST, 
        "API_TOKEN_ID": API_TOKEN_ID, 
        "API_TOKEN_SECRET": API_TOKEN_SECRET, 
        "NODE": NODE, 
        "CLONE_TEMPLATE": CLONE_TEMPLATE, 
        "VM_NAME": VM_NAME, 
        "VMID": NEW_VMID
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        error_msg = f"Configuration File (.env) is incomplete, missing the following required configuration items for VM Allocate: {', '.join(missing_vars)}"
        print(json.dumps({"success": False, "error": error_msg}))
        sys.exit(1)
    
    start_time = time.time()
    result = {"success": False}
    
    print("=== Start VM & User Allocation ===")

    try:
        vm_manager = VMAllocate(
            pve_host=PVE_HOST,
            node=NODE,
            api_token_id=API_TOKEN_ID,
            api_token_secret=API_TOKEN_SECRET
        )
        
        user_manager = UserAllocate(
            pve_host=PVE_HOST,
            node=NODE,
            api_token_id=API_TOKEN_ID,
            api_token_secret=API_TOKEN_SECRET
        )
        
        user_info = user_manager.create_user(random = False)
        
        vm_info = vm_manager.clone_vm(
            template_vmid=int(CLONE_TEMPLATE),
            new_vmid=int(NEW_VMID),
            new_vm_name=VM_NAME
        )
        
        vm_manager.start_vm(int(NEW_VMID))
        
        snapshot_info = vm_manager.create_snapshot(
            vmid=int(NEW_VMID),
            description="Snapshot when created"
        )
        
        user_manager.grant_vm_access(
            vmid=int(NEW_VMID),
            username=user_info["username"]
        )
        
        total_time = round(time.time() - start_time, 2)
        ip_info = vm_manager.get_vm_ip_and_prefix(vmid=int(NEW_VMID), wait_timeout=120)
        TARGET_HOST = ip_info[0]
        PREFIX = ip_info[1]
        
        result = {
            "success": True,
            "username": user_info["username"],
            "password": user_info["password"],
            "IP": TARGET_HOST,
            "prefix": PREFIX,
            "vmid": vm_info["vmid"],
            "vm_name": vm_info["name"],
            "snapshot": snapshot_info["snapshot_name"],
            "duration": f"{total_time}s"
        }

    except ProxmoxAPIError as e:
        print(e.to_json())
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": "Unknown Error",
            "detail": str(e)
        }, indent=4))
        sys.exit(1)
    
    print(json.dumps(result, indent=4))

    time.sleep(10)

    required_vars = {
        "TARGET_HOST": TARGET_HOST, 
        "VM_SSH_PORT": VM_SSH_PORT, 
        "VM_USERNAME": VM_USERNAME, 
        "VM_PASSWORD": VM_PASSWORD, 
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        error_msg = f"Configuration File (.env) is incomplete, missing the following required configuration items for Execution: {', '.join(missing_vars)}"
        print(json.dumps({"success": False, "error": error_msg}, indent=4))
        sys.exit(1)

    print("=== Start Execution in VM ===")

    executor = SSHExecutor(
        host=TARGET_HOST,
        port=VM_SSH_PORT,
        user=VM_USERNAME,
        password=VM_PASSWORD
    )
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    START_SH = os.path.join(CUR_DIR, 'start.sh')
    OVPN = os.path.join(CUR_DIR, 'ovpn-client.ovpn')
    executor.upload_file(START_SH, f"/home/{VM_USERNAME}/start.sh")
    executor.upload_file(OVPN, f"/home/{VM_USERNAME}/ovpn-client.ovpn")
    executor.run_command(f"chmod +x /home/{VM_USERNAME}/start.sh")

    print("- [x] Start VPN Linking ...")

    try:
        out, err = executor.run_command(f"source /home/{VM_USERNAME}/start.sh {REMOTE_IP} {REMOTE_PORT} {DEFAULT_ROUTER}")
        if err.strip():
            raise Exception(err)
        else:
            print(json.dumps({"success": True, "output": out.strip()}, indent=4))
    except Exception as e:
        print(json.dumps({"success": False, "error": "Fail to LinkVPN", "detail": str(e)}, indent=4))
        sys.exit(1)

    print("- [x] Start Attaching to Map ...")

    try:
        out, err = executor.run_command("ip -4 addr show dev tap0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'")
        if err.strip():
            raise Exception(err)
        else:
            VPN_IP = out.strip()
            print(json.dumps({"success": True, "output": out.strip()}, indent=4))
    except Exception as e:
        print(json.dumps({"success": False, "error": "Fail to get tap0's IP", "detail": str(e)}, indent=4))
        sys.exit(1)

    payload_dict = {
        "networkName": f"output_net_{ASN}_{NET_NAME}",
        "nodename": f"VM{NEW_VMID}",
        "ip": VPN_IP
    }

if __name__ == "__main__":
    run()
'''

DOWN_SCRIPT = '''\
import os
import sys
import json
import time
from dotenv import load_dotenv
from vm_allocate import VMAllocate
from user_allocate import UserAllocate
from base_client import ProxmoxAPIError

def run():
    global_env_path = os.path.join(os.path.dirname(__file__), "../global.env")
    vm_env_path = os.path.join(os.path.dirname(__file__), "./config.env")

    load_dotenv(global_env_path, override=False)
    load_dotenv(vm_env_path, override=True)
    
    PVE_HOST = os.getenv("PVE_HOST")
    API_TOKEN_ID = os.getenv("API_TOKEN_ID")
    API_TOKEN_SECRET = os.getenv("API_TOKEN_SECRET")
    NODE = os.getenv("NODE")
    NEW_VMID = os.getenv("VMID")
    
    required_vars = {
        "PVE_HOST": PVE_HOST, 
        "API_TOKEN_ID": API_TOKEN_ID, 
        "API_TOKEN_SECRET": API_TOKEN_SECRET, 
        "NODE": NODE, 
        "VMID": NEW_VMID
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        error_msg = f"Configuration File (.env) is incomplete, missing the following required configuration items for VM Allocate: {', '.join(missing_vars)}"
        print(json.dumps({"success": False, "error": error_msg}, indent=4))
        sys.exit(1)
    
    try:
        vm_manager = VMAllocate(
            pve_host=PVE_HOST,
            node=NODE,
            api_token_id=API_TOKEN_ID,
            api_token_secret=API_TOKEN_SECRET
        )
        
        user_manager = UserAllocate(
            pve_host=PVE_HOST,
            node=NODE,
            api_token_id=API_TOKEN_ID,
            api_token_secret=API_TOKEN_SECRET
        )
        
        # user_manager.delete_user(vmid=int(NEW_VMID))
        
        vm_manager.delete_vm(vmid=int(NEW_VMID))
    except ProxmoxAPIError as e:
        print(e.to_json())
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": "Unknown Error",
            "detail": str(e)
        }, indent=4))
        sys.exit(1)

if __name__ == "__main__":
    run()
'''

class VMNode:

    vpn_server_ip: str
    vpn_server_port: int
    vpn_default_router: str
    vm_base: str
    vmid: int
    name: str
    asn: int
    net_name: str

    def __init__(self, asn: int, vmid: int, vm_base: str, name: str = "VMTest"):
        self.vmid = vmid
        self.name = name
        self.asn = asn
        self.vm_base = vm_base

    def getIPv4(self):
        result = []
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith("127.") and not ip.startswith("169."):
                        result.append(ip)
        return result

    def joinNetwork(self, network: str, base: Base):
        __as = base.getAutonomousSystem(self.asn)
        assert __as is not None, f"AS {self.asn} does not exist"
        __net = __as.getNetwork(network)
        assert __net is not None, f"Network {network} does not exist"
        assert __net.getRemoteAccessProvider() is not None, f"Network {net_name} does not support remote access"

        self.net_name = network

        for __node in __net.getAssociations():
            if __node.getRole() == NodeRole.OpenVpnRouter:
                self.vpn_default_router = __net.getDefaultRouter().__format__('s')
                self.vpn_server_ip = self.getIPv4()[0]
                self.vpn_server_port = __node.getPorts()[0][0]
    
    def generateVMConfig(self, output_dir: str, vm_ssh_port: int = 22):
        vm_dir = os.path.join(output_dir, f"vm_{self.vmid:03}")
        os.makedirs(vm_dir, exist_ok=True)                                  
        
        with open(os.path.join(vm_dir, "config.env"), "w") as f:
            f.write(LOCAL_ENV_TEMPLATE.format(clone_template=self.vm_base,
                                        vm_name=self.name,
                                        vmid=self.vmid,
                                        vm_ssh_port=vm_ssh_port,
                                        remote_ip=self.vpn_server_ip,
                                        remote_port=self.vpn_server_port,
                                        default_router=self.vpn_default_router,
                                        asn=self.asn,
                                        net_name=self.net_name
                                        ))

        with open(os.path.join(vm_dir, "start.sh"), "w") as f:
            f.write(VPN_SCRIPT)
        
        with open(os.path.join(vm_dir, "ovpn-client.ovpn"), "w") as f:
            f.write(OVPN_CONFIG)

        with open(os.path.join(vm_dir, "start.py"), "w") as f:
            f.write(START_SCRIPT)
        
        with open(os.path.join(vm_dir, "down.py"), "w") as f:
            f.write(DOWN_SCRIPT)