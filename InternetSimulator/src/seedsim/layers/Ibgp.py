from .Layer import Layer
from .Base import Base
from seedsim.core import Registry, ScopedRegistry, Node
from typing import List, Set

class Ibgp(Layer):
    """!
    @brief The Ibgp (iBGP) layer.

    This layer automatically setup full mesh peering between routers within AS.
    """

    __masked: Set[int] = set()
    __reg = Registry()

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        self.__masked = set()

    def getName(self) -> str:
        return 'Ibgp'

    def getDependencies(self) -> List[str]:
        return ['Ospf']

    def mask(self, asn: int):
        """!
        @brief Mask an AS.

        By default, Ibgp layer will add iBGP peering for all ASes. Use this
        method to mask an AS and disable iBGP.

        @param asn AS to mask.
        """
        self.__masked.add(asn)

    def onRender(self):
        base: Base = self.__reg.get('seedsim', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn)).getByType('rnode')

            for router in routers:
                self._log('!! TODO: setting up IBGP peering on as{}/{}'.format(asn, router.getName()))


    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'IbgpLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'Masked ASes:\n'

        indent += 4
        for asn in self.__masked:
            out += ' ' * indent
            out += '{}\n'.format(asn)

        return out

