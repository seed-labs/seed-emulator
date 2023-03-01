#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu import *
import shutil
import os
import getopt
import sys


class CompileTest(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.test_list = {
            "A00-simple-peering": (["simple-peering.py"] , ["output"]),
            "A01-transit-as" : (["transit-as.py"], ["output", "base-component.bin"]),
            "A02-transit-as-mpls" : (["transit-as-mpls.py"], ["output"]), 
            "A03-real-world" : (["real-world.py"], ["output"]),
            "A04-visualization" : (["visualization.py"], ["output"]), 
            "A05-components" : (["components.py"], ["output"]),
            "A06-merge-emulation" : (["merge-emulation.py"], ["output"]),
            "A07-compilers" : (["compilers.py"], ["output"]),
            "A20-nano-internet" : (["nano-internet.py"], ["output", "base-component.bin"]),
            "A21-shadow-internet" : (["shadow-internet.py"], ["output"]),
            "B00-mini-internet" : (["mini-internet.py"], ["output", "base-component.bin"]),
            "B01-dns-component" : (["dns-component.py"], ["dns-component.bin"]),
            "B02-mini-internet-with-dns" : (["mini-internet-with-dns.py"], ["output", "base_with_dns.bin"]),
            "B03-ip-anycast" : (["ip-anycast.py"], ["output"]),
            "B04-bgp-prefix-hijacking" : (["bgp-prefix-hijacking.py"], ["output"]),
            "B05-botnet" : (["botnet-basic.py"], ["output"]),
            "B06-blockchain" : (["blockchain.py"], ["output", "eth-states"]),
            "B07-darknet-tor" : (["darknet-tor.py"], ["output"]),
            "B08-Remix-Connection" : (["component-blockchain.py", "blockchain.py"], ["output", "eth-states", "component-blockchain.bin"]),
            "B10-dhcp" : (["dhcp.py"], ["output"]),
            "C00-hybrid-internet" : (["hybrid-internet.py"], ["output", "base-component.bin"]),
            "C01-hybrid-dns-component" : (["hybrid-dns-component.py"], ["hybrid-dns-component.bin"]),
            "C02-hybrid-internet-with-dns" : (["hybrid-internet-with-dns.py"], ["output", "hybrid_base_with_dns.bin"]),
            "C03-bring-your-own-internet" : (["bring-your-own-internet.py"], ["output"]),
            "C04-ethereum-pos" : (["blockchain-pos.py"], ["output"])
        }
        # This is my path
        cls.init_cwd = os.getcwd()

        cls.path = "../../examples"
        for dir, (scripts, outputs) in cls.test_list.items():
            path = os.path.join(cls.path, dir)
            os.chdir(path)
            file_list = os.listdir(os.curdir)
            for output in outputs:
                if output in file_list: 
                    if os.path.isdir(os.path.join(path, output)):   shutil.rmtree(output)
                    else:   os.remove(output)
            os.chdir(cls.init_cwd)
        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls.init_cwd)
        return super().tearDownClass()
    
    def compile_test(self):
        for dir, (scripts, outputs) in self.test_list.items():
            printLog("######### {} Test #########".format(dir))
            path = os.path.join(self.path, dir)
            os.chdir(path)
            for script in scripts:
                os.system("python3 {} 2> /dev/null".format(script))
            for output in outputs:
                self.assertTrue(output in os.listdir(os.curdir))
            os.chdir(self.init_cwd)
    
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
        test_suite = ut.TestSuite()
        test_suite.addTest(CompileTest('compile_test'))
        
        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
