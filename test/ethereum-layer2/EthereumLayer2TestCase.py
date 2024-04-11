#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut


from test import SeedEmuTestCase

class EthereumLayer2TestCase(SeedEmuTestCase):


    def test_sc_compilation(self):
        pass

    def test_sc_deployment(self):
        pass

    def test_seq_node_connection(self):
        pass

    def test_seq_node_status(self):
        pass

    def test_ns_node_synchronization(self):
        pass

    def test_chain_id(self):
        pass

    def test_tx_execution(self):
        pass

    def test_deposit(self):
        pass

    def test_batch_submission(self):
        pass

    def test_state_submission(self):
        pass


    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()

        test_suite.addTest(cls("test_sc_compilation"))
        test_suite.addTest(cls("test_sc_deployment"))
        test_suite.addTest(cls("test_seq_node_connection"))
        test_suite.addTest(cls("test_seq_node_status"))
        test_suite.addTest(cls("test_ns_node_synchronization"))
        test_suite.addTest(cls("test_chain_id"))
        test_suite.addTest(cls("test_tx_execution"))
        test_suite.addTest(cls("test_deposit"))
        test_suite.addTest(cls("test_batch_submission"))
        test_suite.addTest(cls("test_state_submission"))

        return test_suite

if __name__ == "__main__":
    test_suite = EthereumLayer2TestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    EthereumLayer2TestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    EthereumLayer2TestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))