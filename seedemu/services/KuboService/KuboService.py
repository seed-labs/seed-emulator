from seedemu.core import Node, Service
from seedemu.core.enums import NetworkType
from seedemu.services.KuboService.KuboEnums import Distribution, Architecture
from seedemu.services.KuboService.KuboServer import KuboServer
from typing import List

TEMPORARY_DIR = '/tmp/kubo'

class KuboService(Service):
    """
    The Kubo Service (IPFS)
    """
    _distro:Distribution
    _arch:Architecture
    _bootstrap_ips:List[str]
    _bootstrap_script:str
    _tmp_dir:str
    _first_installed:bool
    _rpc_api_port:int
    _http_gateway_port:int
    
    def __init__(self, apiPort:int=5001, gatewayPort:int=8080,
                 distro:Distribution=Distribution.LINUX, arch:Architecture=Architecture.X64):
        """Create an instance of the IPFS Kubo Service.

        Parameters
        ----------
        apiPort : int, optional
            Set the port that the IPFS RPC API is bound to on all nodes, by default 5001
        gatewayPort : int, optional
            Set the port that the IPFS HTTP Gateway is bound to on all nodes, by default 8080
        distro : Distribution, optional
            OS distribution of Kubo to use, by default Distribution.LINUX
        arch : Architecture, optional
            CPU architecture of Kubo to use, by default Architecture.X64
        """
        super().__init__()
        
        self.addDependency('Base', False, False)  # Depends on base layer (need networking info)
        
        self._tmp_dir = TEMPORARY_DIR.rstrip('/')  # Directory without trailing slash.
        
        assert isinstance(distro, Distribution), '"distro" must be an instance of KuboEnums.Distribution'
        self._distro = distro
        assert isinstance(arch, Architecture), '"arch" must be an instance of KuboEnums.Architecture'
        self._arch = arch
        self._bootstrap_ips = []
        self._rpc_api_port = apiPort
        self._http_gateway_port = gatewayPort
        self._bootstrap_script = None
        self._first_installed = False
        
    def getName(self) -> str:
        return 'KuboService'
    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'KuboServiceLayer\n'

        return out
    
    def _createServer(self) -> KuboServer:
        """Create and return an instance of KuboServer.

        Returns
        -------
        KuboServer
            A virtual node with Kubo installed and configured.
        """
        return KuboServer()

    def _doInstall(self, node:Node, server:KuboServer):
        """Called during the render stage to install KuboServer on a physical node.
           Also makes service-level changes to nodes, including installing the bootstrap script.

        Parameters
        ----------
        node : Node
            Representation of a physical node.
        server : KuboServer
            Representation of IPFS Kubo server for the given node.
        """
        # First node installed during render stage triggers generation of bootstrap IPs and script.
        # All nodes will have bootstrap script installed, and then will proceed with individual installation.
        if len(self._bootstrap_ips) == 0: self._getBootstrapIps()
        if self._bootstrap_script is None: self._bootstrap_script = self._generateBootstrapScript()
        
        # Launch the per-node install process:
        server.install(node, self)
        
        # Modify port bindings on all nodes:
        node.appendStartCommand(f'ipfs config Addresses.API /ip4/0.0.0.0/tcp/{self._rpc_api_port}')
        node.appendStartCommand(f'ipfs config Addresses.Gateway /ip4/0.0.0.0/tcp/{self._http_gateway_port}')
        
        # Add bootstrap script to node and run the script:
        node.appendFile(f'{self._tmp_dir}/bootstrap.sh', self._bootstrap_script)
        node.appendStartCommand(f'chmod +x {self._tmp_dir}/bootstrap.sh')
        node.appendStartCommand(f'bash {self._tmp_dir}/bootstrap.sh', fork=True)
        
        # Forward port for Web UI to host for the first node created:
        # if not self._first_installed:
        #     node.addPortForwarding(self._rpc_api_port, self._rpc_api_port)  # For WebUI access
        #     node.addPortForwarding(self._http_gateway_port, self._http_gateway_port)  # For HTTP Gateway
        #     self._first_installed = True
        # else:
        #     node.addPortForwarding(0, self._rpc_api_port) 

    def getBootstrapList(self) -> list:
        """Get current bootstrap node IP addresses.

        Returns
        -------
        list
            A list of bootstrap node IPv4 addresses as strings.
        """
        return self._bootstrap_ips

    def _getBootstrapIps(self) -> None:
        """Called during the render stage; adds IPs for each bootstrap node to the bootstrap IP list.
        """
        # Must be called during render stage only!
        for server, node in self.getTargets():
            if server.isBootNode():
                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
                for iface in ifaces:
                    net = iface.getNet()
                    if net.getType() == NetworkType.Local and server.isBootNode():
                        self._bootstrap_ips.append(str(iface.getAddress()))
                        break

    def _generateBootstrapScript(self) -> str:
        """Generate bootstrap script that all nodes will use.

        Returns
        -------
        str
            String representing the bootstrap bash script.
        """        
        script = f"""#!/bin/bash

# logfile=/var/log/kubo_bootstrap_$(date +%s).log
logfile=/var/log/kubo_bootstrap.log
timeout=60
bootips=({' '.join(self._bootstrap_ips)})
peerids=()
pidcount=0

# Logger function:
# Positional Arguments:
#    string  : message to log
#    integer : log level (0=INFO, 1=DEBUG, 2=WARNING, 3=ERROR)
log () {{
    msg=$(date -Iseconds)'\\t'
    
    case $2 in
        0)
            msg=$msg'[INFO]\\t\\t'
            ;;
        1)
            msg=$msg'[DEBUG]\\t\\t'
            ;;
        2)
            msg=$msg'[WARNING]\\t\\t'
            ;;
        3)
            msg=$msg'[ERROR]\\t\\t'
            ;;
        *)
            msg=$msg'[INFO]\\t\\t'
            ;;
    esac
    
    msg=$msg$1
    echo -e $msg >>$logfile
}}

log "Kubo Bootstrap Process Started!"
# Write stderr to logfile automatically:
exec 2>>$logfile

# Function to get peer ID and append it to the
# array of bootstrap node IDs:
getid () {{
   # Wait for bootstrap node to initialize:
   up=1
   waited=0
   while [[ $up -ne 0 && $waited -lt $timeout ]]
   do
      nc -z -n ${{ip}} {self._rpc_api_port}
      up=$?
      sleep 1
      ((waited++))
   done

   # Some debug output:
   if [[ $up -eq 0 && $waited -lt $timeout ]]; then
      # Get info from node and add to bootstrap nodes:
      attempts=3
      peerid=""
      while [[ -z $peerid && $attempts -gt 0 ]]
      do
         peerid=$(curl -sX POST "http://${{ip}}:{self._rpc_api_port}/api/v0/config?arg=Identity.PeerID" | jq --raw-output '.Value')
         ((attempts--))
         sleep 5
      done
      
      if [[ -n $peerid ]]; then
         peerids+=($peerid)
         ((pidcount++))
        #  echo "${{ip}} has peer ID ${{peerid}}" >>$logfile
         log "${{ip}} has peer ID ${{peerid}}" 1
      else
         peerids+=("")
        #  echo "Could not get peer ID for ${{ip}}" >>$logfile
         log "Could not get peer ID for ${{ip}}" 3
      fi
   else
      peerids+=("")
    #   echo "Could not get peer ID for ${{ip}}; connection timed out." >>$logfile
      log "Could not get peer ID for ${{ip}}; connection timed out." 3
   fi
}}

# Start IPFS daemon (must be running to serve API requests):
ipfs daemon &
log "Started daemon to serve API requests from other nodes." 1

# Iterate through IPs to get peer IDs:
for ip in "${{bootips[@]}}"
do
   getid $ip
done

# Make changes to bootstrap list:
ipfs bootstrap rm --all &>/dev/null
if [[ $pidcount -gt 0 ]]; then
   for i in "${{!peerids[@]}}";
   do
      ip=${{bootips[$i]}}
      id=${{peerids[$i]}}
      # echo "${{ip}} --> ${{id}}" >&2
      if [[ -n $id ]]; then
         ipfs bootstrap add /ip4/${{ip}}/tcp/4001/p2p/${{id}} &>/dev/null
      fi
   done
#    echo "Kubo bootstrapping completed successfully!" >&2
   log "Kubo bootstrapping completed successfully!" 0
else
#    echo "No peer IDs found, no new nodes added." >&2
   log "No peer IDs found, no new nodes added." 3
fi

# Restart IPFS:
ipfs shutdown
log "Restarting Kubo daemon..." 1
exec ipfs daemon
"""
        return script