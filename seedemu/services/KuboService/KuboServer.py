from __future__ import annotations
from seedemu.core import Node, Server, Service, BaseSystem
from seedemu.services.KuboService.KuboEnums import Architecture, Distribution
from seedemu.services.KuboService.KuboUtils import DottedDict, getIP
from typing import Any, Collection
import json, re

DEFAULT_KUBO_VERSION = 'v0.27.0'
KUBO_LABEL_META = 'kubo.{key}'

class KuboServer(Server):
    """
    The Kubo Server (IPFS)
    
    Attributes
    ----------
    initConfig : a DottedDict representation of the Kubo config JSON file, by default None
    startConfig : a DottedDict representing all Kubo config changes to be made on startup, by default None
    """

    _version:str
    _is_bootnode:bool
    initConfig:DottedDict
    _profile:str

    def __init__(self):
        """Create a new Kubo server.
        """
        
        # Emulator-specific data:
        self._base_system = BaseSystem.DEFAULT
        
        super().__init__()
        
        self._version = DEFAULT_KUBO_VERSION
        self._is_bootnode = False
        self._config_cmds = []
        self.initConfig = DottedDict()
        self.startConfig = DottedDict()
        self._profile = None
    
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
        node.setLabel(KUBO_LABEL_META.format(key='boot_node'), self._is_bootnode)
        node.setLabel(KUBO_LABEL_META.format(key='version'), self._version)
        
        # Download and install Kubo
        node.addBuildCommand(f'mkdir {service._tmp_dir}/')
        kuboFilename = f'kubo_{self._version}_{str(service._distro.value)}-{service._arch.value}'
        node.addBuildCommand(f'curl -so {kuboFilename}.tar.gz https://dist.ipfs.tech/kubo/{self._version}/{kuboFilename}.tar.gz')
        node.addBuildCommand(f'tar -xf {kuboFilename}.tar.gz && rm {kuboFilename}.tar.gz')
        node.addBuildCommand('cd kubo && bash install.sh')
        
        # Add configuration file to IPFS before initialization (read here) if additional configuration is given:
        if not self.initConfig.empty():
            node.appendFile('/root/.ipfs/config', json.dumps(self.initConfig, indent=2))
        
        # Initialize IFPS
        if self._profile is None or self._profile in ['', 'default', 'none']:
            node.appendStartCommand('ipfs init')
        else:
            node.appendStartCommand(f'ipfs init --profile={self._profile}')
            
        # Add startup config commands if they exist:
        if not self.startConfig.empty():
            for key, val in self.startConfig.dottedItems():
                if isinstance(val, str):
                    node.appendStartCommand(f'ipfs config {key} {val}')
                else:
                    node.appendStartCommand(f"ipfs config --json {key} '{json.dumps(val)}'")
        
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
    
    def setVersion(self, version:str) -> Self:
        """Sets the version of Kubo to use on this node.

        Parameters
        ----------
        version : str
            String representation of Kubo version, like 'v0.27.0'
            
        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        assert re.match('v(\d{1,3}\.){2}\d{1,3}(-rc)?', str(version).strip().lower()) is not None, f'{version} is not a valid version of Kubo'
        self._version = version
        return self
        
    def getVersion(self) -> str:
        """Get the version of Kubo that will be installed on this node.

        Returns
        -------
        str
            String representation of Kubo version, like 'v0.27.0'
        """
        return self._version
    
    def replaceConfig(self, config:dict) -> Self:
        """Import an entire config file in dictionary representation. This overrides the default config file at initialization.

        Parameters
        ----------
        config : dict
            representation of the Kubo config JSON file (located at $IPFS_PATH/config).

        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self.initConfig = DottedDict(config)
        return self
    
    def importConfig(self, config:dict) -> Self:
        """Import an entire config file in dictionary representation. Its keys and values will be configured at startup.

        Parameters
        ----------
        config : dict
            representation of the Kubo config JSON file (located at $IPFS_PATH/config).

        Returns
        -------
        Self
            This KuboServer instance for chaining API calls.
        """
        self.startConfig = DottedDict(config)
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
        self.startConfig[key] = value
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