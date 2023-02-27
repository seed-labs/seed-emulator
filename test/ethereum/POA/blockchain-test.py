#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from SEEDBlockchain import Wallet
from web3 import Web3
from seedemu import *
import os
import getopt
import sys
import time

class MultipleChainsTestCase(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.system("/bin/bash ./emulator-code/run.sh 2> /dev/null &")

        cls.wallet1 = Wallet(chain_id=1337)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet1.createAccount(name)

        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("/bin/bash ./emulator-code/down.sh 2> /dev/null")
        
        return super().tearDownClass()

    def test_poa_chain_connection(self):
        url = 'http://10.150.0.71:8545'

        i = 1
        current_time = time.time()
        while True:
            printLog("\n==========Trial {}==========".format(i))
            if time.time() - current_time > 600:
                printLog("TimeExhausted: 600 sec")
            try:
                self.wallet1.connectToBlockchain(url, isPOA=True)
                printLog("Connection Succeed: ", url)
                break
            except Exception as e:
                printLog(e)
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

def get_arguments(argv, mapping):
    # Remove 1st argument from the list of command line arguments
    argumentList = argv[1:]

    # Options and long options
    options = "ht:"
    long_options = ["help", "times="]

    try:
        # Parsing argument
        arguments, values = getopt.getopt(argumentList, options, long_options)

        # checking each argument
        for arg, value in arguments:
            if arg in ("-h", "--help"):
                print ("Usage: test_script.py -t <times>")
                exit()

            elif arg in ("-t", "--times"):
                mapping['times'] = int(value)

    except getopt.error as err:
        print (str(err))

def printLog(*args, **kwargs):
    print(*args, **kwargs)
    with open('./test_log/log.txt','a') as file:
        print(*args, **kwargs, file=file)

if __name__ == "__main__":
    options = {}
    options['times'] = 1  # default sleeping time
    get_arguments(sys.argv, options)    
    result = []

    os.system("rm -rf test_log")
    os.system("mkdir test_log")
    
    for i in range(options['times']):
        os.system("mkdir ./test_log/test_%d"%i)
        test_suite = ut.TestSuite()
        test_suite.addTest(MultipleChainsTestCase('test_poa_chain_connection'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_chain_id'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_send_transaction'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_chain_consensus'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_peer_counts'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_emulator_account'))
        test_suite.addTest(MultipleChainsTestCase('test_poa_create_accounts'))
        test_suite.addTest(MultipleChainsTestCase('test_import_account'))

        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        os.system("mv ./test_log/log ./test_log/test_%d/log_%s"%(i, succeed))

        printLog("Emulator Down")
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        