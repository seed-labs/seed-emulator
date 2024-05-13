from __future__ import annotations
from typing import Dict

from seedemu.core import Node, Server, Service

import json
from ipaddress import IPv4Network


_Templates: Dict[str, str] = {}

_Templates["sig"] = """\
[log]
    [log.console]
        level = "{log_level}"

[tunnel]
src_ipv4 = "{src_ip}"

[gateway]
traffic_policy_file = "/etc/scion/sig.json"
ctrl_addr = "{ctrl_addr}:{ctrl_port}"
data_addr = "{data_addr}:{data_port}"
"""

_CommandTemplates: Dict[str, str] = {}

_CommandTemplates["sig_setup"] = "ip address add {ip_addr} dev lo"

_CommandTemplates["sig_start"] = """\
until pgrep -xf "scion-ip-gateway --config /etc/scion/{name}.toml" > /dev/null 2>&1;
do
    sleep 5;
    nohup scion-ip-gateway --config /etc/scion/{name}.toml >> /var/log/{name}.log 2>&1 &
done
echo "scion-ip-gateway started"
"""

sig_default_software = []

sig_default_software = ["iperf3", "net-tools"]

class ScionSIGServer(Server):
    """!
    @brief SCION IP Gateway server.
    """

    __config : Dict[str, str]

    def __init__(self):
        """!
        @brief ScionSIGServer constructor.
        """
        super().__init__()
        self.__config = {}

    def setConfig(self, config: {}) -> ScionSIGServer:
        """!
        @brief Set the configuration.

        @param config Configuration dictionary.
        """
        self.__config = config

        return self

    def _append_sig_command(self, node: Node):
        """
        Append commands for starting the SCION SIG stack on the node.
        """
        # get config
        config = self.__config
        ip = IPv4Network(config["local_net"]).network_address + 1
        # add setup command
        node.appendStartCommand(_CommandTemplates["sig_setup"].format(ip_addr=ip))
        node.appendStartCommand(_CommandTemplates['sig_start'].format(name=node.getName()))

    def _provision_sig_config(self, node: Node):
        
        name = node.getName()

        config = self.__config

        # provision sig.json

        isd, as_num = config["other_ia"]
        remote_net = config["remote_net"]

        sig_json = {
            "ASes": {
                f"{isd}-{as_num}": {
                    "Nets": [
                        remote_net
                    ]
                }
            },
            "ConfigVersion": 9001
        }

        node.setFile("/etc/scion/sig.json", json.dumps(sig_json, indent=4))

        # provision sig.toml

        local_net = config["local_net"]

        local_net = IPv4Network(local_net)
        src_ip = local_net.network_address + 1

        src_ip = str(src_ip)

        ip = node.getInterfaces()[0].getAddress()
        ctrl_port = config["ctrl_port"]
        data_port = config["data_port"]
        debug_level = config["debug_level"]

        sig_toml = _Templates["sig"].format(
            log_level=debug_level,  
            src_ip=src_ip,
            ctrl_addr=ip,
            ctrl_port=ctrl_port,
            data_addr=ip,
            data_port=data_port 
       )
    
        node.setFile(f"/etc/scion/{name}.toml", sig_toml)

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        [node.addSoftware(software) for software in sig_default_software] # add default software

        node.addBuildCommand(
            "apt-get update && apt-get install -y scion-sig")

        self._append_sig_command(node)

        self._provision_sig_config(node)

        node.appendClassName("ScionSIGService")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'SCION IP Gateway server object.\n'
        return out


class ScionSIGService(Service):
    """!
    @brief SCION IP Gateway service.
    """

    def __init__(self):
        """!
        @brief ScionSIGService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, False)

    def _createServer(self) -> Server:
        return ScionSIGServer()

    def getName(self) -> str:
        return 'ScionSIGService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ScionSIGServiceLayer\n'
        return out
