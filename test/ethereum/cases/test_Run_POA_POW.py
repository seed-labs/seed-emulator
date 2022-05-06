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

class TestIsArrayFunction(unittest.TestCase):
    def test_true_array(self):
        res = isArray('["0xb259ec1870f32a202c5a4779be7bd554f7dc6015", "0x906badd4a982fc0e107c1691f6e27abafa958425", "0xd72559d3200d6fb9bdd81f5aa704a6a1147ca15f"]')
        self.assertIsNotNone(res)
        self.assertTrue(res)

    def test_true_empty_array(self):
        res = isArray('[]')
        self.assertIsNotNone(res)
        self.assertTrue(res)

    def test_false_array(self):
        res = isArray('"0x906badd4a982fc0e107c1691f6e27abafa958425"')
        self.assertIsNotNone(res)
        self.assertFalse(res)

class TestRunPOAPOW(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.system("cd ../resources/blockchain_poa_pow; nohup /bin/bash build.sh; /bin/bash run.sh &")
        sleep(300) # sleep 5 min to build and run container
        return super().setUpClass()
    
    @classmethod
    def tearDownClass(cls) -> None:
        os.system("cd ../resources/blockchain_poa_pow; /bin/bash down.sh")
        return super().tearDownClass()

    def setUp(self) -> None:
        cmd='docker ps -aqf "name=Ethereum-{}-"'
        self.eth_array = [subprocess.check_output(cmd.format(i), shell=True).decode("utf-8").strip() for i in range(1,8)]
        self.eth1, self.eth2, self.eth3, self.eth4, self.eth5, self.eth6, self.eth7 = self.eth_array
        return super().setUp()
    
    def test_running(self):
        for eth in self.eth_array:
            cmd="docker exec -t {} geth attach --exec 'eth.accounts'".format(eth)
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            self.assertTrue(isArray(removeColoredText(output)))
    
    def test_mining(self):
        # check mining
        for index, result in enumerate(["true","true","false","true","true","true","true"]):
            if index + 1 % 3 == 0 and index + 1 <=6:
                # boot node is not mining
                cmd="docker exec -t {} geth attach --exec 'eth.mining'".format(self.eth_array[index])
                output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
                self.assertEqual(result,removeColoredText(output))
        
    
    def test_consensus_mechanism(self):
        for eth in self.eth_array[:5]:
            cmd="docker exec -t {} geth attach --exec 'web3.clique'".format(eth)
            output = removeColoredText(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
            self.assertNotEqual(removeColoredText(output),"undefined")
        for eth in self.eth_array[5:]:
            cmd="docker exec -t {} geth attach --exec 'web3.ethash'".format(eth)
            output = removeColoredText(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
            self.assertNotEqual(removeColoredText(output),"undefined")   

if __name__ == '__main__':
    unittest.main()