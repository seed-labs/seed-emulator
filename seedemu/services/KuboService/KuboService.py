from seedemu.core import Node, Service
from seedemu.core.enums import NetworkType
from seedemu.services.KuboService.KuboEnum import Distribution, Architecture
from KuboServer import KuboServer
import http.client
import re

class KuboService(Service):
    """!
    @brief The Kubo Service (IPFS)
    """
    _bootstrap_ips:list[str]
    _bootstrap_script:str
    
    def __init__(self, **kwargs):
        """Create instance of the Kubo Service
        
        Args:
            bootstrap_ips (list): OPTIONAL; a list of strings representing IPv4 addresses.
        """
        super().__init__()
        
        self.addDependency('Base', False, False)  # Depends on base layer (need networking info)
        
        self._bootstrap_ips = kwargs.get('bootstrap_ips', [])
        self._bootstrap_script = None
        
    def getName(self) -> str:
        return 'KuboService'
    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'KuboServiceLayer\n'

        return out
    
    def _createServer(self) -> KuboServer:
        """Create and return an instance of KuboServer.

        Returns:
            KuboServer: a Node with Kubo installed and configured.
        """
        return KuboServer()
        
    def _doInstall(self, node:Node, server:KuboServer):
        """Called during the render stage to install a KuboServer on a node.
        In this case, also adds bootstrap script to node.

        Args:
            node (Node): representation of a physical node.
            server (KuboServer): representation of IPFS Kubo server for the given node.
        """
        
        # First node installed during render stage triggers generation of bootstrap IPs and script.
        # All nodes will have bootstrap script installed, and then will proceed with individual installation.
        if len(self._bootstrap_ips) == 0: self._getBootstrapIps()
        if self._bootstrap_script is None: self._bootstrap_script = self._generateBootstrapScript()
        node.appendFile('/tmp/kubo/bootstrap.sh', self._bootstrap_script)
        node.appendStartCommand('chmod +x /tmp/kubo/bootstrap.sh')
        server.install(node, self)
        
    # def addBootstrap(self, *args) -> None:
    #     """Add all valid IPs to bootstrap node list.
    #     """
    #     # Iterate through args, if valid, add to bootstrap node list.
    #     self._bootstrap_ips.extend(args)
        
    def getBootstrapList(self) -> list:
        """Get current bootstrap nodes for Kubo service.

        Returns:
            list: list of IPs as strings
        """
        return self._bootstrap_ips
    
    # def clearBootstrapList(self) -> None:
    #     """Clear current list of bootstrap nodes.
    #     """
    #     self._bootstrap_ips.clear()
        
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
        """Generate bootstrap script; prep for install.
        
        Returns:
            str: string representing bootstrap script.
        """
        script = f"""#!/bin/bash

timeout=60
bootips=({' '.join(self._bootstrap_ips)})
peerids=()
pidcount=0

# Function to get peer ID and append it to the
# array of bootstrap node IDs:
getid () {{
   # Wait for bootstrap node to initialize:
   up=1
   waited=0
   while [[ $up -ne 0 && $waited -lt $timeout ]]
   do
      nc -z -n ${{ip}} 5001
      up=$?
      sleep 1
      ((waited++))
   done

   # Some debug output:
   if [[ $up -eq 0 && $waited -lt $timeout ]]; then
      # Get info from node and add to bootstrap nodes:
      # curl -sX POST "http://${{ip}}:5001/api/v0/config?arg=Identity.PeerID"
      peerid=$(curl -sX POST "http://${{ip}}:5001/api/v0/config?arg=Identity.PeerID" | jq --raw-output '.Value')
      
      if [[ -n $peerid ]]; then
         peerids+=($peerid)
         ((pidcount++))
         # echo "${{ip}} is ${{peerid}}"
      else
         peerids+=("")
         echo "Could not get peer ID for ${{ip}}"
      fi
   else
      peerids+=("")
      echo "${{ip}} connection timed out."
   fi
}}


# Wait for network to come up:
# router=""
# while [[ -z $router ]]
# do
#    ip route
#    router=$(ip route | grep -Po '(?<=default via )([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}')
#    sleep 1
# done
# echo "Network is up! Router is at ${{router}}"

# Iterate through IPs to get peer IDs:
for ip in "${{bootips[@]}}"
do
   getid $ip
done

# Make changes to bootstrap list:
if [[ $pidcount -gt 0 ]]; then
   ipfs bootstrap rm --all &>/dev/null
   for i in "${{!peerids[@]}}";
   do
      ip=${{bootips[$i]}}
      id=${{peerids[$i]}}
      # echo "${{ip}} --> ${{id}}" >&2
      if [[ -n $id ]]; then
         ipfs bootstrap add /ip4/${{ip}}/tcp/4001/p2p/${{id}} &>/dev/null
      fi
   done
   echo "Kubo bootstrapping completed successfully!"
else
   echo "No peer IDs found, no changes made."
fi

# Start IPFS:
# ipfs daemon &
"""
        return script