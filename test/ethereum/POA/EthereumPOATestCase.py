#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from .SEEDBlockchain import Wallet
from web3 import Web3
from seedemu import *
import time
from test import SeedEmuTestCase

class EthereumPOATestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.wallet1 = Wallet(chain_id=1337)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet1.createAccount(name)

        return

    def test_poa_chain_connection(self):
        url = 'http://10.150.0.71:8545'

        i = 1
        current_time = time.time()
        while True:
            self.printLog("\n----------Trial {}----------".format(i))
            if time.time() - current_time > 600:
                self.printLog("TimeExhausted: 600 sec")
            try:
                self.wallet1.connectToBlockchain(url, isPOA=True)
                self.printLog("Connection Succeed: ", url)
                break
            except Exception as e:
                self.printLog(e)
                time.sleep(20)
                i += 1
        self.assertTrue(self.wallet1._web3.isConnected())

    def test_poa_chain_id(self):
        self.assertEqual(self.wallet1._web3.eth.chain_id, 1337)
    
    def test_poa_send_transaction(self):
        time.sleep(10)
        recipient = self.wallet1.getAccountAddressByName('Alice')
        txhash = self.wallet1.sendTransaction(recipient, 0.1, sender_name='Eve', wait=True, verbose=False)
        self.assertTrue(self.wallet1.getTransactionReceipt(txhash)["status"], 1)

    def test_poa_chain_consensus(self):
        config = dict(self.wallet1._web3.geth.admin.nodeInfo().protocols.eth.config)
        self.assertTrue("clique" in config.keys())

    def test_poa_peer_counts(self):
        peer_counts = len(self.wallet1._web3.geth.admin.peers())
        self.assertEqual(peer_counts, 3)

    def test_import_account(self):
        self.assertEqual(self.wallet1._web3.eth.getBalance(Web3.toChecksumAddress("9f189536def35811e1a759860672fe49a4f89e94")), 10)
    
    def test_poa_emulator_account(self):
        accounts = []
        for i in range(1,6):
            accounts.extend(EthAccount.createEmulatorAccountsFromMnemonic(i, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=32*EthUnit.ETHER.value, total=1, password="admin"))
        for account in accounts:
            self.assertTrue(self.wallet1._web3.eth.getBalance(account.address) >= 32*EthUnit.ETHER.value)

    def test_poa_create_accounts(self):
        accounts = []
        for index in range(1, 4):
            accounts.append(EthAccount.createEmulatorAccountFromMnemonic(3, mnemonic="great awesome fun seed security lab protect system network prevent attack future", balance=30*EthUnit.ETHER.value, index=index, password="admin"))
        
        for account in accounts:
            self.assertTrue(self.wallet1._web3.eth.getBalance(account.address) >= 30*EthUnit.ETHER.value)

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_poa_chain_connection'))
        test_suite.addTest(cls('test_poa_chain_id'))
        test_suite.addTest(cls('test_poa_send_transaction'))
        test_suite.addTest(cls('test_poa_chain_consensus'))
        test_suite.addTest(cls('test_poa_peer_counts'))
        test_suite.addTest(cls('test_poa_emulator_account'))
        test_suite.addTest(cls('test_poa_create_accounts'))
        test_suite.addTest(cls('test_import_account'))
        return test_suite
    
if __name__ == "__main__":
    test_suite = EthereumPOATestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    EthereumPOATestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    EthereumPOATestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
