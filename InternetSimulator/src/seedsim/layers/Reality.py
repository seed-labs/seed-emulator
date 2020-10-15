from .Layer import Layer
from .Base import Base
from .Routing import Router
from seedsim.core import Node, Network, AutonomousSystem, ScopedRegistry
from typing import List, Dict
import requests

RIS_PREFIXLIST_URL = 'https://stat.ripe.net/data/announced-prefixes/data.json'

RealityFileTemplates: Dict[str, str] = {}

RealityFileTemplates['configure_script'] = '''\
#!/bin/bash
gw="`ip rou show default | cut -d' ' -f3`"
sed -i 's/!__default_gw__!/'"$gw"'/g' /etc/bird/bird.conf
'''

class RealWorldRouter(Router):
    """!
    @brief RealWorldRouter class.

    This class extends the router node to supporting routing prefix to real
    world.
    """

    __realworld_routes: List[str]
    __sealed: bool
    __hide_hops: bool

    def initRealWorld(self, hideHops: bool):
        """!
        @brief init RealWorldRouter.
        """
        if hasattr(self, '__sealed'): return
        self.__realworld_routes = []
        self.__sealed = False
        self.__hide_hops = hideHops
        self.addSoftware('iptables')
        self.setFile('/rw_configure_script', RealityFileTemplates['configure_script'])
        self.addStartCommand('chmod +x /rw_configure_script')
        self.addStartCommand('/rw_configure_script')

    def addRealWorldRoute(self, prefix: str):
        """!
        @brief Add real world route.

        @param prefix prefix.
        
        @throws AssertionError if sealed.
        """
        assert not self.__sealed, 'Node sealed.'
        self.__realworld_routes.append(prefix)

    def getRealWorldRoutes(self) -> List[str]:
        """!
        @brief Get list of real world prefixes.

        @returns list of prefixes.
        """
        return self.__realworld_routes

    def seal(self):
        """!
        @brief seal the realworld router.

        Use this method to "seal" the router (add static protocol.) No new real
        world routes can be added once the node is sealed.
        """
        if self.__sealed: return
        self.__sealed = True
        if len(self.__realworld_routes) == 0: return
        self.addTable('t_rw')
        statics = '\n    table t_rw;\n    route ' + ' via !__default_gw__!;\n    route '.join(self.__realworld_routes)
        statics += ' via !__default_gw__!;\n'
        for prefix in self.__realworld_routes:
            # nat matched only
            self.appendFile('/rw_configure_script', 'iptables -t nat -A POSTROUTING -d {} -j MASQUERADE\n'.format(prefix))
            
            if self.__hide_hops:
                # remove realworld hops
                self.appendFile('/rw_configure_script', 'iptables -t mangle -A POSTROUTING -d {} -j TTL --ttl-set 64\n'.format(prefix))

        self.addProtocol('static', 'real_world', statics)
        self.addTablePipe('t_rw', 't_bgp')
        # self.addTablePipe('t_rw', 't_ospf') # TODO


    def print(self, indent: int) -> str:
        out = super(RealWorldRouter, self).print(indent)
        indent += 4

        out += ' ' * indent
        out += 'Real-world prefixes:\n'

        indent += 4
        for prefix in self.__realworld_routes:
            out += ' ' * indent
            out += '{}\n'.format(prefix)
        

        return out

class Reality(Layer):
    """!
    @brief The Reality.

    Reality Layer provides different ways to connect from and to the real world. 
    """

    __rwnodes: List[RealWorldRouter]
    __reg = ScopedRegistry('seedsim')
    __hide_hops: bool

    def __init__(self, hideHops: bool = True):
        """!
        @brief Reality constructor.

        @param hideHops hide realworld hops from traceroute (by setting TTL = 64
        to all real world dsts on POSTROUTING)
        """
        self.__rwnodes = []
        self.__hide_hops = hideHops

    def getName(self):
        return 'Reality'
    
    def getDependencies(self) -> List[str]:
        return ['Ebgp']

    def getPrefixList(self, asn: int) -> List[str]:
        """!
        @brief Helper tool, get real-world prefix list for an ans by RIPE RIS.

        @param asn asn.
        
        @throw AssertionError if API failed.
        """
        self._log('loading real-world prefix list for as{}...'.format(asn))

        rslt = requests.get(RIS_PREFIXLIST_URL, {
            'resource': asn
        })

        assert rslt.status_code == 200, 'RIPEstat API returned non-200'
        
        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'
 
        return [p['prefix'] for p in json['data']['prefixes'] if ':' not in p['prefix']]

    def createRealWorldRouter(self, asobj: AutonomousSystem, nodename: str = 'rw', prefixes: List[str] = None) -> Node:
        """!
        @brief add a router node that routes prefixes to the real world.

        Connect the node to an IX, or to other nodes in IX via IBGP, to get the
        routes into simulation.

        @param as AutonomousSystem to add this node to.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        rwnode: RealWorldRouter = asobj.createRouter(nodename)
        rwnode.__class__ = RealWorldRouter
        rwnode.initRealWorld(self.__hide_hops)
        if prefixes == None: prefixes = self.getPrefixList(asobj.getAsn())
        for prefix in prefixes:
            rwnode.addRealWorldRoute(prefix)
        self.__rwnodes.append(rwnode)

        return rwnode

    def getRealWorldRouters(self) -> List[RealWorldRouter]:
        """!
        @brief Get list of real-world routers.

        @returns list of real world routers.
        """
        return self.__rwnodes

    def enableRealWorldAccess(self, net: Network):
        """!
        @brief Setup VPN server for real-world clients to join a simulated
        network.

        @param net network.
        """
        pass

    def onRender(self):
        for node in self.__rwnodes:
            node.seal()

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Real-world router nodes:\n'

        indent += 4
        for node in self.__rwnodes:
            out += node.print(indent)

        return out
