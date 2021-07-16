from __future__ import annotations
from seedemu.core import Component, Emulator, AutonomousSystem, Router, Hook
from seedemu.layers import Base, Routing
from typing import Dict, List

BgpAttackerComponentTemplates: Dict[str, str] = {}

BgpAttackerComponentTemplates['hijack_static'] = '''
    ipv4 {{
        table t_hijack;
    }};
{routes}
'''

class BgpAttackerInjectorHook(Hook):
    """!
    @brief Hook to inject static protocol after the EBGP layer configured the
    router. (we need the t_bgp table.)
    """
    
    __component: BgpAttackerComponent

    def __init__(self, component: 'BgpAttackerComponent'):
        """!
        @brief create the hook.

        @param component the attacker component.
        """
        self.__component = component

    def getName(self) -> str:
        return 'BgpAttackerInjectorAs{}'.format(self.__component.getHijackerAsn())

    def getTargetLayer(self) -> str:
        return 'Ebgp'

    def postrender(self, emulator: Emulator):
        prefixes = self.__component.getHijackedPrefixes()
        self._log('hijacking prefixes: {}'.format(prefixes))
        
        router = self.__component.getHijackerRouter()
        router.addTable('t_hijack')
        router.addTablePipe('t_hijack', 't_bgp', exportFilter = 'filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }')

        if len(prefixes) > 0:
            routes = ''
            for prefix in prefixes:
                routes += '    route {} blackhole;\n'.format(prefix)

            router.addProtocol('static', 'hijacks', BgpAttackerComponentTemplates['hijack_static'].format(
                routes = routes
            ))

class BgpAttackerComponent(Component):
    """!
    @brief BGP hijacker component.
    """

    __data: Emulator
    __hijacker_as: AutonomousSystem
    __prefixes: List[str]
    __routing: Routing
    __hijacker: Router

    def __init__(self, attackerAsn: int):
        """!
        @brief Create a new BGP hijacker.

        @param attackerAsn ASN of the hijacker.
        """

        self.__data = Emulator()
        self.__prefixes = []

        base = Base()
        self.__routing = Routing()

        self.__hijacker_as = base.createAutonomousSystem(attackerAsn)
        self.__hijacker = self.__hijacker_as.createRouter('hijacker')

        self.__data.addLayer(base)
        self.__data.addLayer(self.__routing)
        self.__data.addHook(BgpAttackerInjectorHook(self))

    def getHijackerAsn(self) -> int: 
        """!
        @brief Get ASN of the hijacker.

        @returns ASN.
        """
        return self.__hijacker_as.getAsn()

    def getHijackerRouter(self) -> Router:
        """!
        @brief Get the router object of the hijacker.

        @returns router.
        """
        return self.__hijacker

    def get(self) -> Emulator:
        """!
        @brief Get the emulator with attacker.

        Merge the emulator to install the component.
        """
        return self.__data

    def addHijackedPrefix(self, prefix: str) -> BgpAttackerComponent:
        """!
        @brief Add a prefix to hijack.

        @param prefix prefix in CIDR notation.

        @returns self, for chaining API calls.
        """
        self.__prefixes.append(prefix)

        return self

    def getHijackedPrefixes(self) -> List[str]:
        """!
        @brief Get hijacked prefixes.

        @returns list of prefixes.
        """
        return self.__prefixes

    def joinInternetExchange(self, ix: str, addr: str) -> BgpAttackerComponent:
        """!
        @brief Join an internet exchange.

        @param ix internet exchange network name.
        @param addr address in the exchange.

        @returns self, for chaining API calls.
        """
        self.__hijacker.joinNetwork(ix, addr)

        return self