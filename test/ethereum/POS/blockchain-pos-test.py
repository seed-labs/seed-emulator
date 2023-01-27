#!/usr/bin/env python3
# encoding: utf-8

import time
import unittest as ut
from SEEDBlockchain import Wallet
from web3 import Web3
from seedemu import *
import requests
import os, time
import docker
import getopt
import sys
from web3.middleware import geth_poa_middleware


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
        os.system("/bin/bash run.sh 2> /dev/null &")
        
        cls.wallet1 = Wallet(chain_id=1337)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet1.createAccount(name)
        
        cls.wallet2 = Wallet(chain_id=1337)
        cls.wallet3 = Wallet(chain_id=1337)

        cls.beacon_client = BeaconClient()
        cls.result = True
        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("/bin/bash down.sh 2> /dev/null")
        
        return super().tearDownClass()
    
    def test_pos_chain_merged(self):
        start_time = time.time()
        isMerged = False
        printLog("\n========================================")
        printLog("Terminal total difficulty is set to 40.")
        printLog("The blockNumber will not increase from 20, if the merge is failed.")
        printLog("So we will assume that the blockNumber is over 24, the merge is succeed.")
        printLog("========================================")
        while True:
            latestBlockNumber = self.wallet1._web3.eth.getBlock('latest').number
            printLog("current blockNumber : ", latestBlockNumber)
            if latestBlockNumber > 24:
                isMerged = True
                break
            if time.time() - start_time > 600:
                break
            time.sleep(20)
        self.assertTrue(isMerged)

    def test_pos_geth_connection(self):
        #printLog(len(self.beacon_client.getValidatorList()))
        url_1 = 'http://10.151.0.72:8545'
        url_2 = 'http://10.152.0.72:8545'
        url_3 = 'http://10.153.0.72:8545'

        i = 1
        current_time = time.time()
        while True:
            printLog("\n==========Trial {}==========".format(i))
            if time.time() - current_time > 600:
                printLog("TimeExhausted: 600 sec")
            try:
                self.wallet1.connectToBlockchain(url_1, isPOA=True)
                printLog("Connection Succeed: ", url_1)
                self.wallet2.connectToBlockchain(url_2, isPOA=True)
                printLog("Connection Succeed: ", url_2)
                self.wallet3.connectToBlockchain(url_3, isPOA=True)
                printLog("Connection Succeed: ", url_3)
                break
            except Exception as e:
                printLog(e)
                time.sleep(20)
                i += 1
        self.assertTrue(self.wallet1._web3.isConnected())

    def test_pos_contract_deployment(self):
        client = docker.from_env()
        all_containers = client.containers.list()
        beacon_setup_container:container
        contract_deployed = False
        for container in all_containers:
            labels = container.attrs['Config']['Labels']
            if 'BeaconSetup' in labels.get('org.seedsecuritylabs.seedemu.meta.displayname', ''):
                beacon_setup_container = container
        web3_list = [(self.wallet1._url, self.wallet1._web3),
                        (self.wallet2._url, self.wallet2._web3),
                        (self.wallet3._url, self.wallet3._web3) ]
    
        while True:
            latestBlockNumber = self.wallet1._web3.eth.getBlock('latest').number
            printLog("\n========================================")
            printLog("Waiting for contract deployment...")
            printLog("current blockNumber : ", latestBlockNumber)
            for ip, web3 in web3_list:
                printLog("Total in txpool: {} ({})".format(len(web3.geth.txpool.content().pending), ip))
            if latestBlockNumber == 20:
                break
            result = str(beacon_setup_container.exec_run("cat contract_address.txt").output, 'utf-8')
            if 'Deposit contract address:' in result:
                printLog("++++Deposit Succeed++++")
                printLog(result)
                contract_deployed = True
                break
            time.sleep(10)
        self.assertTrue(contract_deployed)

    def test_pos_send_transaction(self):
        recipient = self.wallet1.getAccountAddressByName('Bob')
        txhash = self.wallet1.sendTransaction(recipient, 0.1, sender_name='David', wait=True, verbose=False)
        self.assertTrue(self.wallet1.getTransactionReceipt(txhash)["status"], 1)

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

def connect_to_geth(url, consensus):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
       sys.exit("Connection failed!")
   
   if  consensus==  'POA':
       web3.middleware_onion.inject(geth_poa_middleware, layer=0)

   return web3

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
        test_suite.addTest(POSTestCase('test_pos_geth_connection'))
        test_suite.addTest(POSTestCase('test_pos_contract_deployment'))
        # test_suite.addTest(POSTestCase('test_pos_chain_merged'))
        # test_suite.addTest(POSTestCase('test_pos_send_transaction'))
        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        os.system("mv ./test_log/log ./test_log/test_%d/log_%s"%(i, succeed))

        printLog("Emulator Down")
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
