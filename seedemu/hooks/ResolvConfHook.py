from seedemu.core import Hook, Emulator, Node
from typing import List

class ResolvConfHook(Hook):
    """!
    @brief ResolvConfHook class. This class allows you to set resolv.conf on
    all host nodes.
    """

    __servers: List[str]

    def __init__(self, nameservers: List[str]):
        """!
        @brief ResolvConfHook constructor.

        
        """
        self.__servers = nameservers

    def getName(self) -> str:
        return 'ResolvConfHook'

    def getTargetLayer(self) -> str:
        return 'Base'

    def postrender(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for ((scope, type, name), object) in reg.getAll().items():
            if type != 'hnode': continue
            self._log('setting resolv.conf for as{}/{}'.format(scope, name))
            host: Node = object
            host.appendStartCommand(': > /etc/resolv.conf')
            for s in self.__servers:
                host.appendStartCommand('echo "nameserver {}" >> /etc/resolv.conf'.format(s))
