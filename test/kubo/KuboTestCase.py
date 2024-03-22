#!/usr/bin/env python3
# encoding: utf-8

import random, json, time, os
import unittest as ut
from seedemu import *
from test import SeedEmuTestCase

class KuboTestCase(SeedEmuTestCase):
    @classmethod
    def ctCmd(cls, container, cmd) -> Tuple[int, str]:
        """Runs a command on a given container.

        Parameters
        ----------
        container : _type_
            A docker container that is currently running.
        cmd : str
            The command to be run.

        Returns
        -------
        Tuple[int, str]
            A tuple of the exit code (int) and the command output (str).
        """
        exit_code, output = container.exec_run(cmd)
        return exit_code, output
    
    @classmethod
    def isKubo(cls, container) -> bool:
        """Check if a container is a Kubo node.

        Parameters
        ----------
        container : Docker Container
            A docker container object.

        Returns
        -------
        bool
            True if the container is running Kubo.
        """
        try:
            isKubo = 'KuboService' in json.loads(container.attrs["Config"]["Labels"].get("org.seedsecuritylabs.seedemu.meta.class", "[]"))
        except:
            exit_code, _ = cls.ctCmd(container, "ipfs")
            isKubo = exit_code == 0
        return isKubo
    
    @classmethod
    def isBoot(cls, container) -> bool:
        """Check if a container is a Kubo boot node.

        Parameters
        ----------
        container : _type_
            A Docker container object

        Returns
        -------
        bool
            True if the container is a Kubo boot node.
        """
        
        return container.attrs["Config"]["Labels"].get("org.seedsecuritylabs.seedemu.meta.kubo.boot_node", "False") == "True"
        
    
    @classmethod
    def getCtName(cls, container) -> str:
        """Get the name of a Docker container.

        Parameters
        ----------
        container : _type_
            A docker container.

        Returns
        -------
        str
            The name of the container.
        """
        return container.attrs.get("Name").strip('/')
    
    @classmethod
    def pullKuboLogs(cls, container) -> None:
        """Retrieve Kubo bootstrap log file from container and place it in the test_log directory.

        Parameters
        ----------
        container : Docker Container
            A Docker container running Kubo.
        """
        assert cls.isKubo(container), f"Cannot pull Kubo bootstrap logs; {cls.getCtName(container)} is not running Kubo."
        exit_code, output = cls.ctCmd(container, "cat /var/log/kubo_bootstrap*")
        if exit_code == 0:
            log_contents = output.decode()
            log_file = os.path.join(cls.init_dir, cls.test_log, f"kubo_bootstrap_log{cls.getCtName(container)}")
            with open(log_file, 'w') as f:
                f.write(log_contents)
        else:
            raise Exception(output.decode())
    
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass(testLogOverwrite=True)
        
        # Populate some class variables:
        cls.regexPatterns = {
            'ipv4': '([0-9]{1,3}\.){3}[0-9]{1,3}',
            'port': '[0-9]{1,5}'
        }
        
        cls.wait_until_all_containers_up(31)
        
        # Determine which nodes are Kubo nodes:
        cls.kubo_containers = []
        cls.kubo_boot_containers = []
        for ct in cls.containers:
            if cls.isKubo(ct): cls.kubo_containers.append(ct)
            if cls.isBoot(ct): cls.kubo_boot_containers.append(ct)
        
        numFiles:int = 3
        # Just add a few files to IPFS on a few random nodes:
        for i in range(numFiles):
            ct = random.choice(cls.containers)
            cls.ctCmd(ct, f'echo Test File #{i} > test{i}.txt')
            cls.ctCmd(ct, f'ipfs add test{i}.txt')
        return
    
    # @classmethod
    # def tearDownClass(cls) -> None:
    #     # Retrieve bootstrapping log files from each node before teardown:
    #     cls.printLog(f'{" Teardown: pullKuboLogs ":=^100}')
    #     for ct in cls.kubo_containers:
    #         cls.printLog(f'Pulling Kubo bootstrap log file for {cls.getCtName(ct)}: ', end='')
    #         try:
    #             cls.pullKuboLogs(ct)
    #         except Exception as e:
    #             cls.printLog(f'failed\n\t{e}')
    #             cls.printLog(f'\t{cls.ctCmd(ct, "ls /var/log/")[1].decode()}')
    #         else:
    #             cls.printLog('succeed')
        
    #     super().tearDownClass()
    
    
    def test_kubo_install(self):
        self.printLog(f'{" Test Case: test_kubo_install ":=^100}')
        for ct in self.kubo_containers:
            exit_code, output = self.ctCmd(ct, "ipfs version")
            self.printLog(f'{self.getCtName(ct)}: {output.decode()}')
            self.assertEqual(exit_code, 0)
    
    def test_bootstrap_list(self):
        self.printLog(f'{" Test Case: test_bootstrap_list ":=^100}')
        for ct in self.kubo_containers:
            exit_code, output = self.ctCmd(ct, "ipfs bootstrap list")
            bootstrap_list = output.decode().splitlines()
            self.printLog(f'{self.getCtName(ct)}:')
            for b in bootstrap_list:
                self.printLog(f'\t{b}')
                self.assertRegexpMatches(b, f'/ip4/{self.regexPatterns["ipv4"]}/tcp/{self.regexPatterns["port"]}/p2p/.*')
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(self.kubo_boot_containers), len(bootstrap_list))
            
    def test_peering(self):
        self.printLog(f'{" Test Case: test_peering ":=^100}')
        for ct in self.kubo_containers:
            exit_code, output = self.ctCmd(ct, "ipfs swarm peers")
            peers = output.decode().splitlines()
            # Second try if peering is not yet complete:
            if len(peers) < len(self.kubo_containers):
                time.sleep(15)
                exit_code, output = self.ctCmd(ct, "ipfs swarm peers")
                peers = output.decode().splitlines()
            # Print peers to logs:
            self.printLog(f'{self.getCtName(ct)} ({len(peers)}):')
            for p in peers:
                self.printLog(f'\t{p}')
                
            self.assertGreaterEqual(len(peers), len(self.kubo_containers))
            
            
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_kubo_install'))
        test_suite.addTest(cls('test_bootstrap_list'))
        test_suite.addTest(cls('test_peering'))
        return test_suite
    

if __name__ == "__main__":
    test_suite = KuboTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    
    KuboTestCase.printLog("----------Test---------")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    KuboTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
