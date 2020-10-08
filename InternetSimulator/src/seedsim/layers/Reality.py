from .Layer import Layer
from .Base import AutonomousSystem
from seedsim.core import Node, Network
from typing import List
import requests

RIS_PREFIXLIST_URL = 'https://stat.ripe.net/data/announced-prefixes/data.json'

class Reality(Layer):
    """!
    @brief The Reality.

    Reality Layer provides different ways to connect from and to the real world. 
    """

    def __init__(self):
        """!
        @brief Reality constructor.
        """
    def getName(self):
        return 'Reality'
    
    def getDependencies(self) -> List[str]:
        return ['Base']

    def getPrefixList(self, asn: int) -> List[str]:
        """!
        @brief Helper tool, get real-world prefix list for an ans by RIPE RIS.

        @param asn asn.
        
        @throw AssertionError if API failed.
        """
        self._log('loading real-world prefix list for as{}'.format(asn))

        rslt = requests.get(RIS_PREFIXLIST_URL, {
            'resource': asn
        })

        assert rslt.status_code == 200, 'RIPEstat API returned non-200'
        
        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'
 
        return [p['prefix'] for p in json['data']['prefixes'] if ':' not in p['prefix']]

    def createRealWorldRouter(self, asobj: AutonomousSystem, prefixes: List[str] = None) -> Node:
        """!
        @brief add a router node that routes prefixes to the real world.

        @param as AutonomousSystem to add this node to.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        pass

    def createRealWorldAutonomousSystem(self, asn: int, prefixes: List[str] = None) -> AutonomousSystem:
        """!
        @brief add an AutonomousSystem with a router node that routes prefixes
        to the real world.

        @param asn asn.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        pass

    def enableRealWorldAccess(self, net: Network):
        """!
        @brief Setup VPN server for real-world clients to join a simulated
        network.

        @param net network.
        """
        pass
