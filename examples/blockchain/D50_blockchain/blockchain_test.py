#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from SEEDBlockchain import Wallet
from web3 import Web3
from seedemu import *

class MultipleChainsTestCase(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wallet1 = Wallet(chain_id=1337)
        cls.wallet2 = Wallet(chain_id=1338)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet1.createAccount(name)
            cls.wallet2.createAccount(name)

        url_1 = 'http://10.152.0.71:8540'
        url_2 = 'http://10.160.0.71:8545'
        cls.wallet1.connectToBlockchain(url_1)
        cls.wallet2.connectToBlockchain(url_2, isPOA=True)
        

    def test_pow_chain_connection(self):
        self.assertTrue(self.wallet1._web3.isConnected())
    
    def test_poa_chain_connection(self):
        self.assertTrue(self.wallet2._web3.isConnected())

    def test_pow_chain_id(self):
        self.assertEqual(self.wallet1._web3.eth.chain_id, 1337)
    
    def test_poa_chain_id(self):
        self.assertEqual(self.wallet2._web3.eth.chain_id, 1338)

    def test_pow_send_transaction(self):
        recipient = self.wallet1.getAccountAddressByName('Bob')
        txhash = self.wallet1.sendTransaction(recipient, 0.1, sender_name='David', wait=True, verbose=False)
        self.assertTrue(self.wallet1.getTransactionReceipt(txhash)["status"], 1)
    
    def test_poa_send_transaction(self):
        recipient = self.wallet2.getAccountAddressByName('Alice')
        txhash = self.wallet2.sendTransaction(recipient, 0.1, sender_name='Eve', wait=True, verbose=False)
        self.assertTrue(self.wallet2.getTransactionReceipt(txhash)["status"], 1)

    def test_pow_chain_consensus(self):
        config = dict(self.wallet1._web3.geth.admin.nodeInfo().protocols.eth.config)
        self.assertTrue("ethash" in config.keys())

    def test_poa_chain_consensus(self):
        config = dict(self.wallet2._web3.geth.admin.nodeInfo().protocols.eth.config)
        self.assertTrue("clique" in config.keys())

    def test_pow_peer_counts(self):
        peer_counts = len(self.wallet1._web3.geth.admin.peers())
        self.assertEqual(peer_counts, 3)

    def test_poa_peer_counts(self):
        peer_counts = len(self.wallet2._web3.geth.admin.peers())
        self.assertEqual(peer_counts, 2)

    def test_import_account(self):
        self.assertEqual(self.wallet1._web3.eth.getBalance(Web3.toChecksumAddress("9f189536def35811e1a759860672fe49a4f89e94")), 10)
    
    def test_pow_emulator_account(self):
        accounts = []
        for i in range(1,5):
            accounts.extend(EthAccount.createEmulatorAccountsFromMnemonic(i, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=32*EthUnit.ETHER.value, total=1, password="admin"))
        for account in accounts:
            self.assertTrue(self.wallet1._web3.eth.getBalance(account.address) >= 32*EthUnit.ETHER.value)

    def test_poa_emulator_account(self):
        accounts = []
        for i in range(5,9):
            accounts.extend(EthAccount.createEmulatorAccountsFromMnemonic(i, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=32*EthUnit.ETHER.value, total=1, password="admin"))
        for account in accounts:
            self.assertTrue(self.wallet2._web3.eth.getBalance(account.address) >= 32*EthUnit.ETHER.value)

    def test_pow_create_account(self):
        account = EthAccount.createEmulatorAccountFromMnemonic(3, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=20*EthUnit.ETHER.value, index=1, password="admin")
        self.assertTrue(self.wallet1._web3.eth.getBalance(account.address) >= 20*EthUnit.ETHER.value)

    def test_pow_create_accounts(self):
        accounts = []
        for index in range(1, 4):
            accounts.append(EthAccount.createEmulatorAccountFromMnemonic(7, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=30*EthUnit.ETHER.value, index=index, password="admin"))
        
        for account in accounts:
            self.assertTrue(self.wallet2._web3.eth.getBalance(account.address) >= 30*EthUnit.ETHER.value)


if __name__ == "__main__":    
    
    test_suite = ut.TestLoader().loadTestsFromTestCase(MultipleChainsTestCase)
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    print("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
