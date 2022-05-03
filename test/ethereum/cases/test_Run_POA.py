#!/usr/bin/env python3
# encoding: utf-8

import os
from time import sleep
import unittest
import subprocess
# from subprocess import CalledProcessError
from seedemu.services.EthereumService import *
import time

def removeColoredText(color_text:str):
    return re.sub(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]', '', color_text)

def isArray(test:str):
    '''
    check a string is string array format or not
    for example: ["1,","2"], ['1','2']
    '''
    regex = re.compile(r'\[[a-z,\",\',0-9,\,,\ ]*\]')
    res = re.match(regex, test)
    return bool(res)


class TestRunPOA(unittest.TestCase):
    '''
    This is a test case to test ethereum service on Proof-Of-Authority consensus.
    '''
    @classmethod
    def setUpClass(cls) -> None:
        '''
        A classmethod to setup the some thing before running this test case.
        For this test case, it will render the network, build the containers and run the container for testing
        '''
        os.system("cd ../resources/blockchain_poa; nohup /bin/bash build.sh; /bin/bash run.sh &")
        sleep(300) # sleep 5 min to build and run container
        return super().setUpClass()
    
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("cd ../resources/blockchain_poa; /bin/bash down.sh")
        return super().tearDownClass()

    def setUp(self) -> None:
        '''
        setup some variables for test method
        Here will get all the ethereum containers id for test method 
        '''
        cmd='docker ps -aqf "name=Ethereum-{}-"'
        self.eth_array = [subprocess.check_output(cmd.format(i), shell=True).decode("utf-8").strip() for i in range(1,7)]
        self.eth1, self.eth2, self.eth3, self.eth4, self.eth5, self.eth6 = self.eth_array
        return super().setUp()
    
    def test_running(self):
        '''
        Test the ethereum node is running or not. 
        If the node is not running, geth can not attach to this node and execute command.
        This test method will try to list the account on each ethereum node, and assert the node's output.
        If the output is not the list of account address, it means the node runns incorrectly.
        '''
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'eth.accounts'".format(eth)
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            self.assertTrue(isArray(removeColoredText(output)))
    
    def test_prefund_account(self):
        '''
        Test create prefund account api is executed correctly.
        Checking whether a prefunded account is created on e3 and its balance
        '''
        cmd="docker exec -t {} geth attach --exec 'eth.getBalance(eth.accounts[1])'".format(self.eth3)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("8989898989", removeColoredText(output))
    
    def test_import_account(self):
        '''
        Test import prefund account api is executed correctly.
        Checking whether a specific prefund account is imported on e4 by checking the address and checkd its balance
        '''
        #test the import account exist
        cmd="docker exec -t {} geth attach --exec 'eth.getBalance(\"675eb8226a35256f638712db74878f0a15d3d56e\")'".format(self.eth4)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("989898989898", removeColoredText(output))
        
        #test the balance
        cmd="docker exec -t {} geth attach --exec 'eth.accounts'".format(self.eth4)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertTrue('0x675eb8226a35256f638712db74878f0a15d3d56e' in removeColoredText(output[1:-1]).replace("\"","").replace(" ","").split(","))
    
    def test_mining(self):
        '''
        Test the node is mining or not
        In this case, ethereum node 1-5 is mining, ethereum node 6 is not.
        '''
        for eth in self.eth_array[:-1]:
            cmd="docker exec -t {} geth attach --exec 'eth.mining'".format(eth)
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            self.assertEqual("true",removeColoredText(output))
        
        # eth6 is not mining
        cmd="docker exec -t {} geth attach --exec 'eth.mining'".format(self.eth6)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("false",removeColoredText(output))
    
    def test_consensus_mechanism(self):
        '''
        Test all nodes is on POA consensus.
        If a node runs on POA, it should have a module clique. So the method check whether all ethhereum nodes have module clique.
        '''
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'web3.clique'".format(eth)
            output = removeColoredText(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
            self.assertNotEqual(removeColoredText(output),"undefined")

    # def test_transation(self):
    #     '''
    #     Test transation
    #     '''
    #     # get destination account
    #     getReceiverAddrCmd = "docker exec -t {} geth attach --exec 'eth.accounts[2]'".format(self.eth6)
    #     receiverAddr = removeColoredText(subprocess.check_output(getReceiverAddrCmd, shell=True).decode("utf-8").strip())
    #     regex = re.compile(r"\"0x[0-9,a-f,A-F]{40}\"")
    #     res = re.match(regex, receiverAddr)
    #     # output is an address
    #     self.assertTrue(bool(res))
        
    #     # unlock sender account
    #     unlockAccountCmd = "docker exec -t {} geth attach --exec 'personal.unlockAccount(\"0x675eb8226a35256f638712db74878f0a15d3d56e\",\"admin\")'".format(self.eth4)
    #     UnlockAccountOutput = removeColoredText(subprocess.check_output(unlockAccountCmd, shell=True).decode("utf-8").strip())
    #     self.assertEqual(removeColoredText(UnlockAccountOutput),"true", "unlock account fail")
        
    #     # send transation
    #     sendTransationCmd="docker exec -t {} geth attach --exec 'eth.sendTransaction({from: \"0x675eb8226a35256f638712db74878f0a15d3d56e\", to:\"{}\", value:\"100000000\"})'".format(self.eth4, receiverAddr.replace('"',''))
    #     sendTransationOutput = removeColoredText(subprocess.check_output(sendTransationCmd, shell=True).decode("utf-8").strip())
    #     # output is the transation hash
    #     regex = re.compile(r"\"0x[0-9,a-f,A-F]{64}\"")
    #     res = re.match(regex, sendTransationOutput)
    #     self.assertTrue(bool(res))

    #     #wait for the transation
    #     startTime = time.time()
    #     pendingTransations = ""
    #     while True:
    #         sleep(300)
    #         # check transation
    #         getPendingTransationCmd="docker exec -t {} geth attach --exec 'eth.pendingTransactions'".format(self.eth4)
    #         pendingTransations = removeColoredText(subprocess.check_output(getPendingTransationCmd, shell=True).decode("utf-8").strip())
    #         if pendingTransations == "[]":
    #             # the transation is finish
    #             break
    #         # if the transation can not finish in 35 minutes, regard it as time out
    #         if time.time() - startTime > 2100:
    #             self.fail("transation time out: transation can not be finished within half an hour")
        
    #     # assert receiver's balance
    #     receiverBalanceCmd="docker exec -t {} geth attach --exec 'eth.getBalance('{}')'".format(self.eth6, receiverAddr.replace('"',''))
    #     receiverBalance = removeColoredText(subprocess.check_output(receiverBalanceCmd, shell=True).decode("utf-8").strip())
    #     self.assertEqual(receiverBalance, "100000000")
        
    #     # assert sender's balance
    #     senderBalanceCmd="docker exec -t {} geth attach --exec 'eth.getBalance('0x675eb8226a35256f638712db74878f0a15d3d56e')'".format(self.eth4)
    #     senderBalance = removeColoredText(subprocess.check_output(senderBalanceCmd, shell=True).decode("utf-8").strip())
    #     self.assertEqual(senderBalance, "989798989898")

if __name__ == '__main__':
    unittest.main()