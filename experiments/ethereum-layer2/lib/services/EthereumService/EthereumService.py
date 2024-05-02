from __future__ import annotations

from seedemu.services.EthereumService import Blockchain
from .EthUtil import CustomGenesis

class CustomBlockchain(Blockchain):
    
    def addCode(self, address: str, code: str) -> Blockchain:
        """!
        @brief Add code to an account by setting code field of genesis file.

        @param address The account's address.
        @param code The code to set.

        @returns Self, for chaining calls.
        """
        self._genesis.__class__ = CustomGenesis
        self._genesis.addCode(address, code)
        return self