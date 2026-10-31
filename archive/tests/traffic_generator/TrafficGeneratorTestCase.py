#!/usr/bin/env python3
# encoding: utf-8

from typing import Tuple
import unittest as ut
from tests import SeedEmuTestCase


class TrafficGeneratorTestCase(SeedEmuTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(67)
        for container in cls.containers:
            if "iperf-receiver-1" in container.name:
                cls.iperf_receiver_1 = container
            elif "iperf-receiver-2" in container.name:
                cls.iperf_receiver_2 = container
            elif "iperf-generator" in container.name:
                cls.iperf_generator = container
            elif "ditg-receiver" in container.name:
                cls.ditg_receiver = container
            elif "ditg-generator" in container.name:
                cls.ditg_generator = container
            elif "multi-traffic-receiver" in container.name:
                cls.multi_traffic_receiver = container
            elif "multi-traffic-generator" in container.name:
                cls.multi_traffic_generator = container
            elif "scapy-generator" in container.name:
                cls.scapy_generator = container
        return

    @classmethod
    def runCommand(cls, container, cmd, **kwargs) -> Tuple[int, str]:
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
        exit_code, output = container.exec_run(cmd, **kwargs)

        return exit_code, output

    def test_package_installed(self):
        self.printLog("\n-------- package installation test --------")
        self.printLog("container : iperf-receiver-1")
        exit_code, _ = self.runCommand(self.iperf_receiver_1, "which iperf3")
        self.assertTrue(exit_code == 0)

        self.printLog("container : iperf-receiver-2")
        exit_code, _ = self.runCommand(self.iperf_receiver_2, "which iperf3")
        self.assertTrue(exit_code == 0)

        self.printLog("container : iperf-generator")
        exit_code, _ = self.runCommand(self.iperf_generator, "which iperf3")
        self.assertTrue(exit_code == 0)

        self.printLog("container : ditg-receiver")
        exit_code, _ = self.runCommand(self.ditg_receiver, "which ITGRecv")
        self.assertTrue(exit_code == 0)

        self.printLog("container : ditg-generator")
        exit_code, _ = self.runCommand(self.ditg_generator, "which ITGSend")
        self.assertTrue(exit_code == 0)

        self.printLog("container : scapy-generator")
        exit_code, _ = self.runCommand(self.scapy_generator, "which scapy")
        self.assertTrue(exit_code == 0)

        self.printLog("container : multi-traffic-receiver")
        exit_code, _ = self.runCommand(self.multi_traffic_receiver, "which iperf3")
        self.assertTrue(exit_code == 0)
        exit_code, _ = self.runCommand(self.multi_traffic_receiver, "which ITGRecv")
        self.assertTrue(exit_code == 0)

        self.printLog("container : multi-traffic-generator")
        exit_code, _ = self.runCommand(self.multi_traffic_receiver, "which iperf3")
        self.assertTrue(exit_code == 0)
        exit_code, _ = self.runCommand(self.multi_traffic_receiver, "which ITGSend")
        self.assertTrue(exit_code == 0)

    def test_traffc_targets_file_created(self):
        self.printLog("\n-------- traffic targets file creation test --------")

        self.printLog("container : iperf-generator")
        exit_code, output = self.runCommand(
            self.iperf_generator, "cat /root/traffic-targets"
        )
        self.assertTrue(exit_code == 0)
        self.assertTrue("iperf-receiver-1" in output.decode())
        self.assertTrue("iperf-receiver-2" in output.decode())

        self.printLog("container : ditg-generator")
        exit_code, output = self.runCommand(
            self.ditg_generator, "cat /root/traffic-targets"
        )
        self.assertTrue(exit_code == 0)
        self.assertTrue("ditg-receiver" in output.decode())

        self.printLog("container : scapy-generator")
        exit_code, output = self.runCommand(
            self.scapy_generator, "cat /root/traffic-targets"
        )
        self.assertTrue(exit_code == 0)
        self.assertTrue("10.164.0.0/24" in output.decode())
        self.assertTrue("10.170.0.0/24" in output.decode())

        self.printLog("container : multi-traffic-generator")
        exit_code, output = self.runCommand(
            self.multi_traffic_generator, "cat /root/traffic-targets"
        )
        self.assertTrue(exit_code == 0)
        self.assertTrue("multi-traffic-receiver" in output.decode())

    def test_traffic_generator_script_created(self):
        self.printLog("\n-------- traffic generation script creation test --------")

        self.printLog("container : iperf-generator")
        exit_code, _ = self.runCommand(
            self.iperf_generator, "cat /root/traffic_generator_iperf3.sh"
        )
        self.assertTrue(exit_code == 0)


        self.printLog("container : ditg-generator")
        exit_code, _ = self.runCommand(
            self.ditg_generator, "cat /root/traffic_generator_ditg.sh"
        )
        self.assertTrue(exit_code == 0)

        self.printLog("container : scapy-generator")
        exit_code, _ = self.runCommand(
            self.scapy_generator, "/root/traffic_generator.py"
        )
        self.assertTrue(exit_code == 0)

        self.printLog("container : multi-traffic-generator")
        exit_code, _ = self.runCommand(
            self.multi_traffic_generator, "cat /root/traffic_generator_iperf3.sh"
        )
        self.assertTrue(exit_code == 0)
        exit_code, _ = self.runCommand(
            self.multi_traffic_generator, "cat /root/traffic_generator_ditg.sh"
        )
        self.assertTrue(exit_code == 0)

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls("test_package_installed"))
        test_suite.addTest(cls("test_traffc_targets_file_created"))
        test_suite.addTest(cls("test_traffic_generator_script_created"))
        return test_suite


if __name__ == "__main__":
    test_suite = TrafficGeneratorTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    TrafficGeneratorTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    TrafficGeneratorTestCase.printLog(
        "score: %d of %d (%d errors, %d failures)"
        % (num - (errs + fails), num, errs, fails)
    )
