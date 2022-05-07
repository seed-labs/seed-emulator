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
    regex = re.compile(r'\[[a-z,\",\',0-9,\,,\ ]*\]')
    res = re.match(regex, test)
    return bool(res)


class TestRunPOW(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.system("cd ../resources/blockchain_pow; nohup /bin/bash build.sh; /bin/bash run.sh &")
        sleep(300) # sleep 5 min to build and run container
        return super().setUpClass()
    
    @classmethod
    def tearDownClass(cls) -> None:
        os.system("cd ../resources/blockchain_pow; /bin/bash down.sh")
        return super().tearDownClass()

    def setUp(self) -> None:
        cmd='docker ps -aqf "name=Ethereum-{}-"'
        self.eth_array = [subprocess.check_output(cmd.format(i), shell=True).decode("utf-8").strip() for i in range(1,7)]
        self.eth1, self.eth2, self.eth3, self.eth4, self.eth5, self.eth6 = self.eth_array
        return super().setUp()
    
    def test_running(self):
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'eth.accounts'".format(eth)
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            self.assertTrue(isArray(removeColoredText(output)))
    
    def test_prefund_account(self):
        # check creat prefunded accounts on e3
        cmd="docker exec -t {} geth attach --exec 'eth.getBalance(eth.accounts[1])'".format(self.eth3)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("8989898989", removeColoredText(output))
    
    def test_import_account(self):
        #test the import account exist
        cmd="docker exec -t {} geth attach --exec 'eth.getBalance(\"675eb8226a35256f638712db74878f0a15d3d56e\")'".format(self.eth4)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("989898989898", removeColoredText(output))
        
        #test the balance
        cmd="docker exec -t {} geth attach --exec 'eth.accounts'".format(self.eth4)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertTrue('0x675eb8226a35256f638712db74878f0a15d3d56e' in removeColoredText(output[1:-1]).replace("\"","").replace(" ","").split(","))
    
    def test_mining(self):
        # check mining, only eth6 is not mining
        for eth in self.eth_array[:-1]:
            cmd="docker exec -t {} geth attach --exec 'eth.mining'".format(eth)
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            self.assertEqual("true",removeColoredText(output))
        
        # eth6 is not mining
        cmd="docker exec -t {} geth attach --exec 'eth.mining'".format(self.eth6)
        output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.assertEqual("false",removeColoredText(output))
    
    def test_consensus_mechanism(self):
        # check mining, only eth6 is not mining
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'web3.ethash'".format(eth)
            output = removeColoredText(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
            self.assertNotEqual(removeColoredText(output),"undefined")     

if __name__ == '__main__':
    unittest.main()