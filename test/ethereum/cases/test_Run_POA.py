#!/usr/bin/env python3
# encoding: utf-8

import os
from time import sleep
import unittest
import subprocess
# from subprocess import CalledProcessError
from seedemu.services.EthereumService import *

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
        In this case, ethereum node 1-5 is minig, ehtereum node 6 is not.
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
        If a node runs on POA, it should have a module clique. So the method check whether all ehthereum nodes have module clique.
        '''
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'web3.clique'".format(eth)
            output = removeColoredText(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
            self.assertNotEqual(removeColoredText(output),"undefined")     

if __name__ == '__main__':
    unittest.main()