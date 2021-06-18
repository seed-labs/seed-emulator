from seedemu.core import Component, Emulator, AutonomousSystem
from seedemu.layers import Base, Router, Routing

class BgpAttackerComponent(Component):
    """!
    @brief BGP hijacker component.
    """

    __data: Emulator
    __hijacker_as: AutonomousSystem
    __routing: Routing
    __hijacker: Router
    __counter: int

    def __init__(self, attackerAsn: int):
        """!
        @brief Create a new BGP hijacker.

        @param attackerAsn ASN of the hijacker.
        """

        self.__data = Emulator()
        self.__counter = 0

        base = Base()
        self.__routing = Routing()

        self.__hijacker_as = base.createAutonomousSystem(attackerAsn)
        self.__hijacker = self.__hijacker_as.createRouter('hijacker')

        self.__data.addLayer(base)
        self.__data.addLayer(self.__routing)

    def get(self) -> Emulator:
        return self.__data

    def addHijackedPrefix(self, prefix: str):
        """!
        @brief Add a prefix to hijack.

        @param prefix prefix in CIDR notation.
        """
        netname = 'h{}'.format(self.__counter)
        self.__hijacker_as.createNetwork(netname, prefix)
        self.__hijacker.joinNetwork(netname)
        self.__routing.addDirect(self.__hijacker_as.getAsn(), netname)
        self.__counter += 1

    def joinInternetExchange(self, ix: str, addr: str):
        """!
        @brief Join an internet exchange.

        @param ix internet exchange network name.
        @param addr address in the exchange.
        """
        self.__hijacker.joinNetwork(ix, addr)