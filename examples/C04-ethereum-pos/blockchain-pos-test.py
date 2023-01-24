#!/usr/bin/env python3
# encoding: utf-8

import time
import unittest as ut
from SEEDBlockchain import Wallet
from web3 import Web3
from seedemu import *
import requests
import os, time

class BeaconClient:
    """!
    @brief The BeaconClient class.  
    """

    def __init__(self):
        """!
        @brief BeaconClient constructor.
        """

        self._beacon_node_url = 'http://10.151.0.71:8000'
        
    

    def getValidatorList(self):
        return self._request_api("eth/v1/beacon/states/head/validators")['data']


    def _request_api(self, api):
        return requests.get(self._beacon_node_url+"/"+api).json()
    

class POSTestCase(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.system("/bin/bash build.sh")
        os.system("/bin/bash run.sh 2> /dev/null &")
        
        cls.wallet = Wallet(chain_id=1337)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet.createAccount(name)

        cls.beacon_client = BeaconClient()
        cls.result = True
        return super().setUpClass()
        
    # @classmethod
    # def tearDownClass(cls) -> None:
    #     '''
    #     A classmethod to destruct the some thing after this test case is finished.
    #     For this test case, it will down the containers and remove the networks of this test case
    #     '''
        
        
    #     return super().tearDownClass()
    
    def test_pos_chain_merged(self):
        start_time = time.time()
        isMerged = False
        print("")
        while True:
            latestBlockNumber = self.wallet._web3.eth.getBlock('latest').number
            print("current blockNumber : ", latestBlockNumber)
            if latestBlockNumber > 11:
                isMerged = True
                break
            if time.time() - start_time > 600:
                break
            time.sleep(20)
        self.assertTrue(isMerged)

    def test_pos_chain_connection(self):
        #print(len(self.beacon_client.getValidatorList()))
        url_1 = 'http://10.151.0.72:8545'
        i = 1
        current_time = time.time()
        while True:
            print("\n==========Trial {}==========".format(i))
            if time.time() - current_time > 600:
                print("TimeExhausted: 600 sec")
            try:
                self.wallet.connectToBlockchain(url_1, isPOA=True)
                print("Connection Succeed")
                break
            except Exception as e:
                print(e)
                time.sleep(20)
                i += 1

        self.assertTrue(self.wallet._web3.isConnected())
   
    def test_pos_send_transaction(self):
        recipient = self.wallet.getAccountAddressByName('Bob')
        txhash = self.wallet.sendTransaction(recipient, 0.1, sender_name='David', wait=True, verbose=False)

        self.assertTrue(self.wallet.getTransactionReceipt(txhash)["status"], 1)
    
   

if __name__ == "__main__":    
    result = []
    os.system("rm -rf test_log")
    os.system("mkdir test_log")
    for i in range(40):
        os.system("mkdir ./test_log/test_%d"%i)
        test_suite = ut.TestSuite()
        test_suite.addTest(POSTestCase('test_pos_chain_connection'))
        test_suite.addTest(POSTestCase('test_pos_chain_merged'))
        test_suite.addTest(POSTestCase('test_pos_send_transaction'))
        res = ut.TextTestRunner(verbosity=2).run(test_suite)
        if not res.wasSuccessful():
            os.system("mv output /test_log/test_%d/"%(i))
        os.system("/bin/bash down.sh 2> /dev/null")
        succeed = "succeed" if res.wasSuccessful() else "failed"
        os.system("mv log ./test_log/test_%d/log_%s"%(i, succeed))
        print("Emulator Down")
        result.append(res)

    
    for count, res in enumerate(result):
        print("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        print("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        