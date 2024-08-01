#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu import *
import shutil
import os, subprocess
import getopt
import sys


class CompileTest(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
       # Set the platform information
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            cls.platform = "amd"
        elif len(sys.argv) == 2 and sys.argv[1].lower() in ['amd', 'arm']:
            cls.platform = sys.argv[1].lower()
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)
        
        cls.platform 
        cls.test_list = {
            "basic/A00_simple_as":          (["simple_as.py"] , ["output"]),
            "basic/A01_transit_as" :        (["transit_as.py"], ["output"]),
            "basic/A02_transit_as_mpls" :   (["transit_as_mpls.py"], ["output"]), 
            "basic/A03_real_world" :        (["real_world.py"], ["output"]),
            "basic/A04_visualization" :     (["visualization.py"], ["output", "base_component.bin"]), 
            "basic/A05_components" :        (["components.py"], ["output",  "base_component.bin"]),
            "basic/A06_merge_emulation" :   (["merge_emulation.py"], ["output"]),
            "basic/A07_compilers" :         (["compilers.py"], ["output",  "base_component.bin"]),
            "basic/A08_buildtime_docker" :  (["create_eth_account.py"], ["output"]),
            "basic/A20_nano_internet" :     (["nano_internet.py"], ["output", "base_component.bin"]),
            "basic/A21_shadow_internet" :   (["shadow_internet.py"], ["output"]),
            "internet/B00_mini_internet" :              (["mini_internet.py"], ["output"]),
            "internet/B01_dns_component" :              (["dns_component.py"], ["dns_component.bin"]),
            "internet/B02_mini_internet_with_dns" :     (["mini_internet_with_dns.py"], ["output", "base_internet.bin", "dns_component.bin"]),
            "internet/B03_hybrid_internet" :            (["hybrid_internet.py"], ["output"]),
            "internet/B04_hybrid_dns_component" :       (["hybrid_dns_component.py"], ["hybrid_dns_component.bin"]),
            "internet/B05_hybrid_internet_with_dns" :   (["hybrid_internet_with_dns.py"], ["output", "base_hybrid_component.bin", "hybrid_dns_component.bin"]),
            "internet/B20_dhcp" :                       (["dhcp.py"], ["output", "base_internet.bin"]),
            "internet/B21_etc_hosts":                   (["etc_hosts.py"], ["output", "base_internet.bin"]),
            "internet/B22_botnet":                   (["botnet_basic.py"], ["output", "base_internet.bin"]),
            "internet/B23_darknet_tor":                   (["darknet_tor.py"], ["output", "base_internet.bin"]),
            "internet/B24_ip_anycast":                   (["ip_anycast.py"], ["output", "base_internet.bin"]),
            "internet/B25_pki":                   (["pki.py", "pki_with_dns.py"], ["output", "base_internet.bin", "base_internet_dns.bin"]),
            "internet/B26_ipfs_kubo":                   (["kubo.py"], ["output", "base_component.bin"]),
            "internet/B27_ipfs_kubo_dapp":                   (["kubo-eth.py"], ["output", "base_component.bin"]),
            "internet/B28_traffic_generator/0-iperf-traffic-generator":                   (["iperf-traffic-generator.py"], ["output", "base_internet.bin"]),
            "internet/B28_traffic_generator/1-ditg-traffic-generator":                   (["ditg-traffic-generator.py"], ["output", "base_internet.bin"]),
            "internet/B28_traffic_generator/2-scapy-traffic-generator":                   (["scapy-traffic-generator.py"], ["output", "base_internet.bin"]),
            "internet/B28_traffic_generator/3-multi-traffic-generator":                   (["multi-traffic-generator.py"], ["output", "base_internet.bin"]),
            "internet/B50_bring_your_own_internet":     (["bring_your_own_internet.py", "bring_your_own_internet_client.py"], ["output", "output_0", "output_1", "output_2", "output_3", 'base_component.bin', 'base_hybrid_component.bin', 'hybrid_base_with_dns.bin', 'hybrid_dns_component.bin']),
            "internet/B51_bgp_prefix_hijacking":                   (["bgp_prefix_hijacking.py"], ["output", 'base_internet.bin']),
            "blockchain/D00_ethereum_poa" :                         (["ethereum_poa.py"], ["output", "component_base.bin", "component_poa.bin"]),
            "blockchain/D01_ethereum_pos" :                         (["ethereum_pos.py"], ["output"]),
            "blockchain/D05_ethereum_small" :                         (["ethereum_small.py"], ["output"]),
            "blockchain/D20_faucet" :                         (["faucet.py"], ["output", "component_base.bin", "component_poa.bin", "blockchain_poa.bin"]),
            "blockchain/D21_deploy_contract" :                         (["deploy_contract.py"], ["output", "component_base.bin", "component_poa.bin", "blockchain_poa.bin"]),
            "blockchain/D22_oracle" :                         (["simple_oracle.py"], ["output", "ethereum-small.bin"]),
            "blockchain/D31_chainlink" :                         (["chainlink.py"], ["output", "component_base.bin", "component_poa.bin", "blockchain_poa.bin"]),
            "blockchain/D50_blockchain" :                         (["blockchain.py"], ["output", "blockchain_poa.bin"]),
        }
        # This is my path
        cls.init_cwd = os.getcwd()

        cls.path = os.path.join(cls.init_cwd, "../../examples")
        for dir, (scripts, outputs) in cls.test_list.items():
            path = os.path.join(cls.path, dir)
            os.chdir(path)
            file_list = os.listdir(os.curdir)
            for output in outputs:
                if output in file_list: 
                    if os.path.isdir(output):   shutil.rmtree(output)
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
                os.system("python3 {} {} 2> /dev/null".format(script, self.platform))
            for output in outputs:
                self.assertTrue(output in os.listdir(os.curdir))
            os.chdir(self.init_cwd)

    def build_test(self):
        log_file = os.path.join(self.init_cwd, 'test_log', "build_log.txt")
        print(log_file)
        with open(os.devnull, 'w') as f:
            result = subprocess.run(["docker", "compose"], stdout=f)
            if result.returncode == 0:
                docker_compose_version = 2
            else:
                docker_compose_version = 1
        for dir, (scripts, outputs) in self.test_list.items():
            path = os.path.join(self.path, dir)
            os.chdir(path)
            for script in scripts:
                os.system("python3 {} {} 2> /dev/null".format(script, self.platform))
            for output in outputs:
                if os.path.isdir(output) and "docker-compose.yml" in os.listdir(output):
                    os.chdir(os.path.join(path, output))
                    print(path)
                    print(output)
                    with open(log_file, 'a') as f:
                        f.write('########### {} Test ##############\n'.format(dir))
                        if(docker_compose_version == 1):
                            result = subprocess.run(["docker-compose", "build"], stderr=f, stdout=f)
                        else:
                            result = subprocess.run(["docker", "compose", "build"], stderr=f, stdout=f)

                    os.system("echo 'y' | docker system prune > /dev/null")
                    assert result.returncode == 0, "docker build failed"
                    os.chdir(path)
            os.chdir(self.init_cwd)

def printLog(*args, **kwargs):
    print(*args, **kwargs)
    with open('./test_log/log.txt','a') as file:
        print(*args, **kwargs, file=file)


if __name__ == "__main__":
    result = []

    os.system("rm -rf test_log")
    os.system("mkdir test_log")
    
    test_suite = ut.TestSuite()
    test_suite.addTest(CompileTest('compile_test'))
    test_suite.addTest(CompileTest('build_test'))
    
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    succeed = "succeed" if res.wasSuccessful() else "failed"
    result.append(res)

    os.chdir(os.getcwd())
    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
