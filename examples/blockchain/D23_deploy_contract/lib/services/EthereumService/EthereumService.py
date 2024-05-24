from __future__ import annotations

from seedemu.services.EthereumService import Blockchain
from .EthUtil import CustomGenesis

class CustomBlockchain(Blockchain):
    
    def addStorage(self, contract_address: str, owner_address: str, slot: int, value: int) -> Blockchain:
        """!
        @brief Adds storage data to a specified contract in the blockchain's genesis configuration.

        This function is responsible for configuring initial storage values for a contract specified by
        `contract_address`. It uses `owner_address` and `slot` to compute the storage slot in the blockchain
        where `value` will be set. This method is typically used in the setup phase of a blockchain to
        ensure certain data or states are pre-loaded at the launch of the network.

        @param contract_address str: The address of the contract in the blockchain where the storage will be added.
            This contract should already be part of the genesis allocation.
        @param owner_address str: The address used to calculate the hash for the storage slot. This is often the
            owner or creator of the contract, whose address influences the slot calculation.
        @param slot int: The slot index used to calculate the precise storage location within the contract's state.
            This is a numerical index that determines where in the contract's storage layout the value will be placed.
        @param value int: The integer value to be stored at the calculated slot position. This value is typically
            crucial initial state data necessary for the contract's operations.

        @returns Blockchain: for chaining calls.
        """

        self._genesis.__class__ = CustomGenesis
        self._genesis.addStorage(contract_address, owner_address, slot, value)
        return self