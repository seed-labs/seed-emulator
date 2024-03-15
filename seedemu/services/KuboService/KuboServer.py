from seedemu.core import Node, Server, Service, BaseSystem
from seedemu.services.KuboService.KuboEnums import Architecture, Distribution
from seedemu.services.KuboService.KuboUtils import DottedDict, getIP
from typing import Any
from typing_extensions import Self
import json, re

DEFAULT_KUBO_VERSION = 'v0.27.0'

class KuboServer(Server):
    """
    The Kubo Server (IPFS)
    
    Attributes
    ----------
    config : a DottedDict representation of the Kubo config JSON file, by default None
    """

    _version:str
    _distro:Distribution
    _arch:Architecture
    _is_bootnode:bool
    config:DottedDict
    _profile:str

    def __init__(self, distro:Distribution=Distribution.LINUX, arch:Architecture=Architecture.X64,
                 version:str=DEFAULT_KUBO_VERSION, isBootNode:bool=False, config:dict=None, profile:str=None):
        """Create a new Kubo server.

        Parameters
        ----------
        distro : Distribution, optional
            OS distribution of Kubo to use, by default Distribution.LINUX
        arch : Architecture, optional
            CPU architecture of Kubo to use, by default Architecture.X64
        version : str, optional
            Version of Kubo to use, by default DEFAULT_KUBO_VERSION
        isBootNode : bool, optional
            Other nodes will bootstrap to this node, by default False
        config : dict, optional
            JSON configuration file for Kubo to use on initialization, by default None
        profile : str, optional
            Profile (presets) for Kubo to use on initialization, by default None
        """
        
        # Emulator-specific data:
        self._base_system = BaseSystem.DEFAULT
        
        super().__init__()
        
        # Kubo-specific data:
        assert isinstance(distro, Distribution), '"distro" must be an instance of KuboEnums.Distribution'
        self._distro = distro
        
        assert re.match('v(\d{1,3}\.){2}\d{1,3}(-rc)?', str(version).strip().lower()) is not None, f'{version} is not a valid version of Kubo'
        self._version = str(version).strip().lower()
        
        assert isinstance(arch, Architecture), '"arch" must be an instance of KuboEnums.Architecture'
        self._arch = arch
        
        self._is_bootnode = isBootNode
        self.config = DottedDict(config)
        self._profile = str(profile).strip().lower() if profile is not None else None

    def install(self, node:Node, service:Service):
        """Installs Kubo on a physical node.

        Parameters
        ----------
        node : Node
            Physical emulator node for Kubo to be installed on.
        service : Service
            Instance of the Kubo Service being installed.
        """
        
        node.appendClassName('KuboService')
        
        # Download and install Kubo
        node.addBuildCommand(f'mkdir {service._tmp_dir}/')
        kuboFilename = f'kubo_{self._version}_{str(self._distro.value)}-{self._arch.value}'
        node.addBuildCommand(f'curl -so {kuboFilename}.tar.gz https://dist.ipfs.tech/kubo/{self._version}/{kuboFilename}.tar.gz')
        node.addBuildCommand(f'tar -xf {kuboFilename}.tar.gz && rm {kuboFilename}.tar.gz')
        node.addBuildCommand('cd kubo && bash install.sh')
        
        # Add configuration file to IPFS before initialization (read here) if additional configuration is given:
        if not self.config.empty():
            node.appendFile('/root/.ipfs/config', json.dumps(self.config, indent=2))
        
        # Initialize IFPS
        if self._profile is None or self._profile in ['', 'default', 'none']:
            node.appendStartCommand('ipfs init')
        else:
            node.appendStartCommand(f'ipfs init --profile={self._profile}')
        
        # Remainder of configuration is done at the service level (see KuboService).
        
    def isBootNode(self) -> bool:
        """Indicates whether or not the current node is a bootstrap node.

        Returns
        -------
        bool
            True if this node is a bootstrap node, False otherwise.
        """
        return self._is_bootnode
    
    def setBootNode(self, isBoot:bool=True) -> Self:
        """Sets whether or not this node is considered a bootstrap node.

        Parameters
        ----------
        isBoot : bool, optional
            True if this is a bootstrap node, False otherwise, by default True
            
        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self._is_bootnode = isBoot
        return self
    
    def importConfig(self, config:dict) -> Self:
        """Import an entire config file in dictionary representation. This overrides the default config file.

        Parameters
        ----------
        config : dict
            representation of the Kubo config JSON file (located at $IPFS_PATH/config).

        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self.config = DottedDict(config)
        return self
    
    def setConfig(self, key:str, value:Any) -> Self:
        """Add/modify a single line of the config file. This config file overrides the default config file.

        Parameters
        ----------
        key : str
            key in JSON dot-notation.
        value : Any
            desired config value.

        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self.config[key] = value
        return self
         
    def setProfile(self, profile:str) -> Self:
        """Set the profile to be used upon initialization.

        Parameters
        ----------
        profile : str
            any valid profile name; use None to reset to default.

        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self._profile = profile
        return self
            
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Kubo peer object.\n'

        return out