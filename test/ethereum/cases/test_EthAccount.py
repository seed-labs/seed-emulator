import unittest
import re
from seedemu.services.EthereumService import *

'''
Code from https://github.com/vgaicuks/ethereum-address
'''
from Crypto.Hash import keccak

def is_checksum_address(address):
    address = address.replace('0x', '')
    address_hash = keccak.new(digest_bits=256)
    address_hash = address_hash.update(address.lower().encode('utf-8')).hexdigest()

    for i in range(0, 40):
        # The nth letter should be uppercase if the nth digit of casemap is 1
        if ((int(address_hash[i], 16) > 7 and address[i].upper() != address[i]) or
                (int(address_hash[i], 16) <= 7 and address[i].lower() != address[i])):
            return False
    return True

def is_address(address):
    if not re.match(r'^(0x)?[0-9a-f]{40}$', address, flags=re.IGNORECASE):
        # Check if it has the basic requirements of an address
        return False
    elif re.match(r'^(0x)?[0-9a-f]{40}$', address) or re.match(r'^(0x)?[0-9A-F]{40}$', address):
        # If it's all small caps or all all caps, return true
        return True
    else:
        # Otherwise check each case
        return is_checksum_address(address)


def isArray(test:str):
    regex = re.compile(r'\[[a-z,\",\',0-9,\,,\ ]*\]')
    res = re.match(regex, test)
    return bool(res)

class TestEthAccount(unittest.TestCase):
    # @classmethod
    # def setUpClass(self):
    #     os.system("pip3 install eth_account > /dev/null")
    #     print("prepare testing: install eth_account")
    

    # def test_init_without_lib(self):
    #     os.system("pip3 uninstall eth_account")
    #     self.assertRaises(EthAccount(), )
    #     # self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    def test_create_account(self):
        account = EthAccount(alloc_balance="0", password="admin", keyfile = None)
        self.assertIsNotNone(account.keystore_content)
        self.assertIsNotNone(account.keystore_filename)
        self.assertIsNotNone(account.alloc_balance)
        self.assertTrue(is_address(account.address))

    def test_create_account_invalid_balance_negative_decimal(self):
        with self.assertRaises(AssertionError) as ctx:
            EthAccount(alloc_balance="-1", password="admin", keyfile = None)
        self.assertEqual("Invalid Balance: -1", str(ctx.exception))

    def test_create_account_valid_balance_decimal(self):
        account = EthAccount(alloc_balance="14124", password="admin", keyfile = None)
        self.assertEqual(account.alloc_balance, "14124")

    def test_create_account_invalid_balance_hexadecimal(self):
        with self.assertRaises(AssertionError) as ctx:
            EthAccount(alloc_balance="0xkfoangegdsamk", password="admin", keyfile = None)
        self.assertEqual("Invalid Balance: 0xkfoangegdsamk", str(ctx.exception))

    def test_create_account_invalid_balance_hexadecimal_no_prefix(self):
        with self.assertRaises(AssertionError) as ctx:
            EthAccount(alloc_balance="kfoangegdsamk", password="admin", keyfile = None)
        self.assertEqual("Invalid Balance: kfoangegdsamk", str(ctx.exception))

    def test_create_account_valid_balance_hexadecimal(self):
        account = EthAccount(alloc_balance="0xbbcadd00", password="admin", keyfile = None)
        self.assertEqual(account.alloc_balance, "0xbbcadd00")

    def test_create_account_valid_balance_hexadecimal_no_prefix(self):
        account = EthAccount(alloc_balance="bbcadd00", password="admin", keyfile = None)
        self.assertEqual(account.alloc_balance, "bbcadd00")

    def test_create_account_valid_balance_hexadecimal_mix_case(self):
        account = EthAccount(alloc_balance="bbcaDDFF00", password="admin", keyfile = None)
        self.assertEqual(account.alloc_balance, "bbcaDDFF00")

    def test_import_account(self):
        correct_keystore_file = '{"address": "675eb8226a35256f638712db74878f0a15d3d56e", "crypto": {"cipher": "aes-128-ctr", "cipherparams": {"iv": "cbc176365f3894af5e95cd2704ee61c4"}, "ciphertext": "371c37784906c9d37abc3900c958c752f41b60f6dfaeddc4bf2a6d2d774b028b", "kdf": "scrypt", "kdfparams": {"dklen": 32, "n": 262144, "r": 1, "p": 8, "salt": "93794d233d59b0ff5daa6e5eca345c4a"}, "mac": "b139214451b8559567a2d06d7a6d1109b107b23ed8b809c1e6ca6d1c9ec15526"}, "id": "464b1168-fcb5-45c0-8c48-5adc0f255ade", "version": 3}'
        correct_address = '0x675eb8226a35256f638712db74878f0a15d3d56e'
        account = EthAccount(alloc_balance="0", password="admin", keyfile=correct_keystore_file)
        self.assertIsNotNone(account.keystore_content)
        self.assertIsNotNone(account.keystore_filename)
        self.assertIsNotNone(account.alloc_balance)
        self.assertTrue(is_address(account.address))
        self.assertEqual(account.address.lower(), correct_address) #lower() removes the address's checksum
    
if __name__ == '__main__':
    unittest.main()