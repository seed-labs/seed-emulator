from __future__ import annotations

from seedemu.services.EthereumService.EthUtil import Genesis
from Crypto.Hash import keccak

class CustomGenesis(Genesis):
    """!
    @brief Genesis manage class
    """
    
    def calculateStorageSlot(self, address: str, slot: int) -> str:
        """!
        @brief Calculate the storage slot for a given address and slot number.

        @param address The address to calculate the storage slot for.
        @param slot The slot number to calculate the storage slot for.

        @returns The calculated storage slot.
        """
        address_hex = address[2:].lower().zfill(64)
        slot_hex = hex(slot)[2:].zfill(64)
        # Concatenate and hash
        data = address_hex + slot_hex
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(bytearray.fromhex(data))
        storage_slot_hex = '0x' + keccak_hash.hexdigest()
        return storage_slot_hex

    def addStorage(self, contract_address: str, owner_address: str, slot: int, value: int) -> Genesis:
        """!
        @brief Adds storage data for a contract in the genesis file.

        This method adds storage data to a specified contract address in the genesis allocation dictionary.
        It ensures that the contract address already has bytecode ('code') deployed; if so, it will add or update
        the storage slot with the provided value. The method calculates the storage slot based on the owner
        address and the slot index. It requires the contract to have been previously added with its code
        in the genesis block to ensure storage is associated with an existing contract.

        @param contract_address str: The contract address in the genesis allocation to which storage data will be added.
        @param owner_address str: The owner address used to calculate the storage slot.
        @param slot int: The slot index for calculating the specific storage location in the contract.
        @param value int: The value to be stored in the calculated storage slot, specified as an integer.

        @returns Genesis: Returns itself to allow for chaining of multiple configuration calls.
        """

        storage_slot_hex = self.calculateStorageSlot(owner_address, slot)
        value_hex = hex(value)[2:].zfill(64)
        print(f"Storage slot: {storage_slot_hex}, Value: {value_hex}")
        
        contract_address_key = contract_address[2:]
        if contract_address_key in self._genesis["alloc"]:
            if "code" in self._genesis["alloc"][contract_address_key]:
                # Create or update the storage dictionary for this address
                if "storage" in self._genesis["alloc"][contract_address_key]:
                    self._genesis["alloc"][contract_address_key]["storage"][storage_slot_hex] = value_hex
                else:
                    self._genesis["alloc"][contract_address_key]["storage"] = {storage_slot_hex: value_hex}
            else:
                print(f"No 'code' found for {contract_address_key}, unable to set 'storage'.")
        else:
            print(f"Address {contract_address_key} not found in genesis allocation. No 'code' entry to associate with 'storage'.")

        return self