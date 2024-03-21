#!/usr/bin/env python3
# encoding: utf-8

import random
import unittest as ut
from seedemu import *
from test import SeedEmuTestCase

class KuboTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        
        cls.wait_until_all_containers_up(60)
        
        # numFiles:int = 3
        # # Just add a few files to IPFS on a few random nodes:
        # for i in range(numFiles):
        #     ct = random.choice(cls.containers)
        #     print(ct)
        
        return
    
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
    
    def test_bootstrap_list(self):
        for ct in self.containers:
            exit_code, output = self.ctCmd(ct, "ipfs bootstrap list")
            self.assertEqual(exit_code, 0)
            
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_bootstrap_list'))
        return test_suite
    

if __name__ == "__main__":
    test_suite = KuboTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    
    KuboTestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    KuboTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
