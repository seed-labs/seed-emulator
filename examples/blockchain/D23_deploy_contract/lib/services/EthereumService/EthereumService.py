from __future__ import annotations

from seedemu.services.EthereumService import Blockchain
from .EthUtil import CustomGenesis

class CustomBlockchain(Blockchain):
    
    def addStorage(self, contract_address: str, slot: int, value: int, key: str = None, index: int = None, is_dynamic: bool = False) -> Blockchain:
        """!
        @brief Adds storage data to a specified contract in the blockchain's genesis configuration.

        This function is responsible for configuring initial storage values for a contract specified by
        `contract_address`. It uses `owner_address` and `slot` to compute the storage slot in the blockchain
        where `value` will be set. This method is typically used in the setup phase of a blockchain to
        ensure certain data or states are pre-loaded at the launch of the network.

        @param contract_address str: The contract address in the genesis allocation to which storage data will be added.
        @param slot int: The slot index for calculating the specific storage location in the contract.
        @param value int: The value to be stored in the calculated storage slot, specified as an integer.
        @param key str: The key for the storage slot, used for mappings. Default is None.
        @param index int: The index for the storage slot, used for arrays. Default is None.
        @param is_dynamic bool: Flag to indicate if the storage slot is for a dynamic array. Default is False.

        @returns Blockchain: for chaining calls.
        """

        self._genesis.__class__ = CustomGenesis
        self._genesis.addStorage(contract_address, slot, value, key, index, is_dynamic)
        return self