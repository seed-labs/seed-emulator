from __future__ import annotations
import json
import os.path
from typing import Dict

from seedemu.core import Emulator, Node, ScionAutonomousSystem, ScionRouter
from seedemu.layers import Routing, ScionBase, ScionIsd


_Templates: Dict[str, str] = {}

_Templates["general"] = """\
[general]
id = "{name}"
config_dir = "/etc/scion"

[log.console]
level = "debug"
"""

_Templates["trust"] = """\
[trust_db]
connection = "/cache/{name}.trust.db"
"""

_Templates["path"]  = """\
[path_db]
connection = "/cache/{name}.path.db"
"""

_Templates["beacon"] = """\
[beacon_db]
connection = "/cache/{name}.beacon.db"
"""

_Templates["dispatcher"] = """\
[dispatcher]
id = "dispatcher"
"""

_CommandTemplates: Dict[str, str] = {}

_CommandTemplates["br"] = "scion-border-router --config /etc/scion/{name}.toml >> /var/log/scion-border-router.log 2>&1"

_CommandTemplates["cs"] = """\
bash -c 'until [ -e /run/shm/dispatcher/default.sock ]; do sleep 1; done;\
scion-control-service --config /etc/scion/{name}.toml >> /var/log/scion-control-service.log 2>&1'\
"""

_CommandTemplates["disp"] = "scion-dispatcher --config /etc/scion/dispatcher.toml >> /var/log/scion-dispatcher.log 2>&1"

_CommandTemplates["sciond"] = "sciond --config /etc/scion/sciond.toml >> /var/log/sciond.log 2>&1"


class ScionRouting(Routing):
    """!
    @brief Extends the routing layer with SCION inter-AS routing.

    Installs the open-source SCION stack on all hosts and routers. Additionally
    installs standard SCION test applications (e.g., scion-bwtestclient - a
    replacement for iperf) on all hosts.

    During layer configuration Router nodes are replaced with ScionRouters which
    add methods for configuring SCION border router interfaces.
    """

    def configure(self, emulator: Emulator):
        """!
        @brief Install SCION on router, control service and host nodes.
        """
        super().configure(emulator)

        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rnode':
                rnode: ScionRouter = obj
                if not issubclass(rnode.__class__, ScionRouter):
                    rnode.__class__ = ScionRouter
                    rnode.initScionRouter()

                self.__install_scion(rnode)
                name = rnode.getName()
                rnode.appendStartCommand(_CommandTemplates['br'].format(name=name), fork=True)

            elif type == 'csnode':
                csnode: Node = obj
                self.__install_scion(csnode)
                self.__append_scion_command(csnode)
                name = csnode.getName()
                csnode.appendStartCommand(_CommandTemplates['cs'].format(name=name), fork=True)

            elif type == 'hnode':
                hnode: Node = obj
                self.__install_scion(hnode)
                self.__append_scion_command(hnode)

    def __install_scion(self, node: Node):
        """Install SCION packages on the node."""
        node.addBuildCommand(
            'echo "deb [trusted=yes] https://packages.netsec.inf.ethz.ch/debian all main"'
            ' > /etc/apt/sources.list.d/scionlab.list')
        node.addBuildCommand(
            "apt-get update && apt-get install -y"
            " scion-border-router scion-control-service scion-daemon scion-dispatcher scion-tools"
            " scion-apps-bwtester")
        node.addSoftware("apt-transport-https")
        node.addSoftware("ca-certificates")

    def __append_scion_command(self, node: Node):
        """Append commands for starting the SCION host stack on the node."""
        node.appendStartCommand(_CommandTemplates["disp"], fork=True)
        node.appendStartCommand(_CommandTemplates["sciond"], fork=True)

    def render(self, emulator: Emulator):
        """!
        @brief Configure SCION routing on router, control service and host
        nodes.
        """
        super().render(emulator)
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get('seedemu', 'layer', 'Base')
        assert issubclass(base_layer.__class__, ScionBase)
        isd_layer: ScionIsd = reg.get('seedemu', 'layer', 'ScionIsd')

        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type in ['rnode', 'csnode', 'hnode']:
                node: Node = obj
                asn = obj.getAsn()
                as_: ScionAutonomousSystem = base_layer.getAutonomousSystem(asn)
                isds = isd_layer.getAsIsds(asn)
                assert len(isds) == 1, f"AS {asn} must be a member of exactly one ISD"

                # Install AS topology file
                as_topology = as_.getTopology(isds[0][0])
                node.setFile("/etc/scion/topology.json", json.dumps(as_topology, indent=2))

                self.__provision_base_config(node)

            if type == 'rnode':
                rnode: ScionRouter = obj
                self.__provision_router_config(rnode)
            elif type == 'csnode':
                csnode: Node = obj
                self._provision_cs_config(csnode)

    @staticmethod
    def __provision_base_config(node: Node):
        """Set configuration for sciond and dispatcher."""

        node.addBuildCommand("mkdir -p /cache")

        node.setFile("/etc/scion/sciond.toml",
            _Templates["general"].format(name="sd1") +
            _Templates["trust"].format(name="sd1") +
            _Templates["path"].format(name="sd1"))

        node.setFile("/etc/scion/dispatcher.toml", _Templates["dispatcher"])

    @staticmethod
    def __provision_router_config(router: ScionRouter):
        """Set border router configuration on router nodes."""

        name = router.getName()
        router.setFile(os.path.join("/etc/scion/", name + ".toml"),
            _Templates["general"].format(name=name))

    @staticmethod
    def _provision_cs_config(node: Node):
        """Set control service configuration."""

        name = node.getName()
        node.setFile(os.path.join("/etc/scion/", name + ".toml"),
            _Templates["general"].format(name=name) +
            _Templates["trust"].format(name=name) +
            _Templates["beacon"].format(name=name) +
            _Templates["path"].format(name=name))
