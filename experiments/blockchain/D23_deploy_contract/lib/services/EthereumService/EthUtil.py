from __future__ import annotations

from seedemu.services.EthereumService.EthUtil import Genesis
from Crypto.Hash import keccak

class CustomGenesis(Genesis):
    """!
    @brief Genesis manage class
    """
    
    def calculateStorageSlot(self, slot: int, key: str = None, index: int = None, is_dynamic: bool = False) -> str:
        """!
        @brief Calculate the storage slot for a given address and slot number.

        @param slot int: The slot index for calculating the specific storage location in the contract.
        @param key str: The key for the storage slot, used for mappings. Default is None.
        @param index int: The index for the storage slot, used for arrays. Default is None.
        @param is_dynamic bool: Flag to indicate if the storage slot is for a dynamic array. Default is False.
        
        @returns The calculated storage slot.
        """
        if key is not None:
            # For mappings
            key_hex = key[2:].lower().zfill(64)
            slot_hex = hex(slot)[2:].zfill(64)
            data = key_hex + slot_hex
            hash_obj = keccak.new(digest_bits=256)
            hash_obj.update(bytearray.fromhex(data))
            return '0x' + hash_obj.hexdigest()
        elif index is not None:
            if is_dynamic:
                # For dynamic arrays
                slot_hex = hex(slot)[2:].zfill(64)
                hash_obj = keccak.new(digest_bits=256)
                hash_obj.update(bytearray.fromhex(slot_hex))
                base_location = int(hash_obj.hexdigest(), 16)
                return hex(base_location + index)[2:].zfill(64)
            else:
                # For fixed-size arrays
                return hex(slot + index)[2:].zfill(64)
        else:
            # For simple variables
            return hex(slot)[2:].zfill(64)

    def addStorage(self, contract_address: str, slot: int, value: int, key: str = None, index: int = None, is_dynamic: bool = False) -> Genesis:
        """!
        @brief Adds storage data for a contract in the genesis file.

        This method adds storage data to a specified contract address in the genesis allocation dictionary.
        It ensures that the contract address already has bytecode ('code') deployed; if so, it will add or update
        the storage slot with the provided value. The method calculates the storage slot based on the owner
        address and the slot index. It requires the contract to have been previously added with its code
        in the genesis block to ensure storage is associated with an existing contract.

        @param contract_address str: The contract address in the genesis allocation to which storage data will be added.
        @param slot int: The slot index for calculating the specific storage location in the contract.
        @param value int: The value to be stored in the calculated storage slot, specified as an integer.
        @param key str: The key for the storage slot, used for mappings. Default is None.
        @param index int: The index for the storage slot, used for arrays. Default is None.
        @param is_dynamic bool: Flag to indicate if the storage slot is for a dynamic array. Default is False.
        
        @returns Genesis: Returns itself to allow for chaining of multiple configuration calls.
        """

        storage_slot_hex = self.calculateStorageSlot(slot, key, index, is_dynamic)
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