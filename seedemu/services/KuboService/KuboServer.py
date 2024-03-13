from seedemu.core import Node, Server, Service, BaseSystem
from seedemu.core.enums import NetworkType
from KuboEnums import Architecture, Distribution
from KuboUtils import DottedDict
import json

DEFAULT_KUBO_VERSION = 'v0.27.0'

class KuboServer(Server):
    """!
    @brief The Kubo Server (IPFS)
    """

    _version:str
    _distro:Distribution
    _arch:Architecture
    _is_bootnode:bool
    config:DottedDict
    _profile:str

    def __init__(self, **kwargs):
        # Emulator-specific data:
        self._base_system = BaseSystem.DEFAULT
        
        super().__init__()
        
        # Kubo-specific data:
        self._distro = kwargs.get('distro', Distribution.LINUX)
        self._version = kwargs.get('version', DEFAULT_KUBO_VERSION).strip().lower()
        self._arch = kwargs.get('arch', Architecture.X64)
        self._is_bootnode = kwargs.get('is_bootnode', False)
        self.config = DottedDict(kwargs.get('config', {}))
        self._profile = kwargs.get('profile', 'default').strip().lower()  # Empty string or 'default' for default?

    def install(self, node:Node, service:Service):
        """!
        @brief Installs Kubo implementation of IPFS on node.

        @param node Node object.
        """ 
        node.appendClassName('KuboService')
        
        # 1. Download and install Kubo
        node.addBuildCommand('mkdir /tmp/kubo/')
        # assert self._version in service._version_list, f'Specified version, {self._version}, is not a valid version of Kubo'
        # kuboFilename = f'kubo_$(cat /tmp/kubo/version)_{str(self._distro.value)}-{self._arch.value}'
        kuboFilename = f'kubo_{self._version}_{str(self._distro.value)}-{self._arch.value}'
        # Export version as temporary file to make things easier:
        # if self._version != 'latest':
            # node.addBuildCommand(f'echo {self._version} > tmp/kubo/version')
        # else:
            # node.addBuildCommand('curl -s https://dist.ipfs.tech/kubo/versions | grep -so v[0-9]*\.[0-9]*\.[0-9]* | tail -n 1 > /tmp/kubo/version')
       
        # Install:
        # node.addBuildCommand(f'curl -so {kuboFilename}.tar.gz https://dist.ipfs.tech/kubo/$(cat /tmp/kubo/version)/{kuboFilename}.tar.gz')
        node.addBuildCommand(f'curl -so {kuboFilename}.tar.gz https://dist.ipfs.tech/kubo/{self._version}/{kuboFilename}.tar.gz')
        node.addBuildCommand(f'tar -xf {kuboFilename}.tar.gz && rm {kuboFilename}.tar.gz')
        node.addBuildCommand('cd kubo && bash install.sh')
        
        # Add configuration file to IPFS before initialization (read here) if additional configuration is given:
        if not self.config.empty():
            node.appendFile('/root/.ipfs/config', json.dumps(self.config, indent=2))
        
        # 3. Initialize IFPS
        if self._profile in ['', 'default', 'none']:
            node.appendStartCommand('ipfs init')
        else:
            node.appendStartCommand(f'ipfs init --profile={self._profile}')
        # 5. Bind RPC API to public IP
        node.appendStartCommand(f'ipfs config Addresses.API /ip4/{self._getIP(node)}/tcp/5001')
        # 6. Launch daemon/bootstrap script
        node.appendStartCommand('bash /tmp/kubo/bootstrap.sh', fork=True)
        node.appendStartCommand('ipfs daemon >/dev/null', fork=True)
        
    def isBootNode(self) -> bool:
        """
        @brief Returns true if node is a bootstrap node, and false if not.
        """
        return self._is_bootnode
    
    def setBootNode(self, isBoot:bool=True):
        """Sets whether or not this node is considered a bootstrap node for Kubo.

        Args:
            isBoot (bool): True if this is a bootstrap node, False otherwise.

        Returns:
            KuboServer: this KuboServer instance for chaining API calls.
        """
        self._is_bootnode = isBoot
        return self
    
    def importConfig(self, config:dict):
        """Import an entire config file in dictionary form to override the default.

        Args:
            config (dict): representation of the Kubo config JSON file (located at $IPFS_PATH/config).

        Returns:
            KuboServer: this KuboServer instance for chaining API calls.
        """
        self.config = DottedDict(config)
        return self
    
    def setConfig(self, key:str, value):
        """Add/modify a single line of the config file to override the default.

        Args:
            key (str): key in JSON dot-notation.
            value (str): desired config value.

        Returns:
            KuboServer: this KuboServer instance for chaining API calls.
        """
        self.config[key] = value
        return self
    
    def setProfile(self, profile:str):
        """Set the profile with which Kubo will run on the node.

        Args:
            profile (str): any valid profile name; use "" or "default" or None for defaults.

        Returns:
            KuboServer: this KuboServer instance for chaining API calls.
        """
        self._profile = profile
        return self
        
    def _getIP(self, node) -> str:
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                return iface.getAddress()
            
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Kubo peer object.\n'

        return out