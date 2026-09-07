#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import unittest as ut
from unittest.mock import patch

import docker


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from tests.SeedEmuTestCase import SeedEmuTestCase


class DnsAgentTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        docker_from_env = docker.from_env
        with patch.object(
            docker,
            "from_env",
            side_effect=lambda **kwargs: docker_from_env(version="auto", **kwargs),
        ):
            super().setUpClass()
        cls.wait_until_all_containers_up(63)
        cls.registrar = cls._find_container(150, "registrar")
        cls.com_master = cls._find_container(151, "host_0")
        cls.com_secondary = cls._find_container(152, "host_0")

    @classmethod
    def gen_emulation_files(cls):
        cls.printLog("Generating Emulation Files...")
        log_path = os.path.join(cls.init_dir, cls.test_log, "compile_log")
        if os.path.exists(cls.output_dir):
            shutil.rmtree(cls.output_dir)
        with open(log_path, "w") as log:
            result = subprocess.run(
                [sys.executable, cls.emulator_script_name],
                cwd=cls.emulator_code_dir,
                stdout=log,
                stderr=log,
            )
        assert result.returncode == 0, (
            "emulation files generation failed; see {}".format(log_path)
        )
        cls.printLog("gen_emulation_files: succeed")

    @classmethod
    def build_emulator(cls):
        cls.printLog("Building Docker Containers with BuildKit...")
        environment = os.environ.copy()
        environment["DOCKER_BUILDKIT"] = "1"
        environment["COMPOSE_DOCKER_CLI_BUILD"] = "1"
        environment.setdefault("COMPOSE_PARALLEL_LIMIT", "8")
        environment.setdefault("BUILDKIT_PROGRESS", "plain")
        command = (
            ["docker-compose", "build"]
            if cls.docker_compose_version == 1
            else ["docker", "compose", "build"]
        )
        log_path = os.path.join(cls.init_dir, cls.test_log, "build_log")
        with open(log_path, "w") as log:
            result = subprocess.run(
                command,
                cwd=cls.output_dir,
                env=environment,
                stdout=log,
                stderr=log,
            )
        assert result.returncode == 0, "docker build failed; see {}".format(log_path)
        cls.printLog("build_emulator: succeed")

    @classmethod
    def up_emulator(cls):
        command = (
            ["docker-compose", "up", "-d"]
            if cls.docker_compose_version == 1
            else ["docker", "compose", "up", "-d"]
        )
        result = subprocess.run(
            command,
            cwd=cls.output_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert result.returncode == 0, "docker compose up failed"

    @classmethod
    def down_emulator(cls):
        command = (
            ["docker-compose", "down"]
            if cls.docker_compose_version == 1
            else ["docker", "compose", "down"]
        )
        subprocess.run(
            command,
            cwd=cls.output_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @classmethod
    def _find_container(cls, asn, node_name):
        for container in cls.containers:
            labels = container.labels
            if (
                labels.get("org.seedsecuritylabs.seedemu.meta.asn") == str(asn)
                and labels.get("org.seedsecuritylabs.seedemu.meta.nodename") == node_name
            ):
                return container
        return None

    def _exec(self, container, command):
        self.assertIsNotNone(container)
        exit_code, output = container.exec_run(["sh", "-lc", command])
        self.assertEqual(
            exit_code,
            0,
            output.decode(errors="replace"),
        )
        return output.decode()

    def _provision(self):
        output = self._exec(
            self.registrar,
            "curl -fsS -X POST http://127.0.0.1:8053/v1/delegations "
            "-H 'Content-Type: application/json' "
            "--data '{\"domain\":\"traditional-test.com\",\"nameservers\":["
            "{\"name\":\"ns1.seedemu-dns.net.\"},"
            "{\"name\":\"ns2.seedemu-dns.net.\"}]}'",
        )
        return json.loads(output)

    def test_provisioner_health(self):
        output = self._exec(
            self.registrar,
            "curl -fsS http://127.0.0.1:8053/health",
        )
        self.assertEqual(json.loads(output)["status"], "ok")

    def test_parent_delegation(self):
        result = self._provision()
        self.assertEqual(result["status"], "delegated")
        self.assertTrue(result["changed"])
        self.assertEqual(result["master"], "10.151.0.71")
        self.assertEqual(result["secondaries"], ["10.152.0.71"])

    def test_master_and_secondary_converged(self):
        expected = "ns1.seedemu-dns.net.\nns2.seedemu-dns.net."
        for container in (self.com_master, self.com_secondary):
            output = self._exec(
                container,
                "dig +noall +authority @127.0.0.1 traditional-test.com NS "
                "| awk '$4 == \"NS\" {print $5}' | sort",
            )
            self.assertEqual(output.strip(), expected)

        master_soa = self._exec(
            self.com_master,
            "dig +short @127.0.0.1 com. SOA",
        )
        secondary_soa = self._exec(
            self.com_secondary,
            "dig +short @127.0.0.1 com. SOA",
        )
        self.assertEqual(master_soa.strip(), secondary_soa.strip())

    def test_repeated_delegation_is_idempotent(self):
        result = self._provision()
        self.assertEqual(result["status"], "delegated")
        self.assertFalse(result["changed"])

    @classmethod
    def get_test_suite(cls):
        suite = ut.TestSuite()
        suite.addTest(cls("test_provisioner_health"))
        suite.addTest(cls("test_parent_delegation"))
        suite.addTest(cls("test_master_and_secondary_converged"))
        suite.addTest(cls("test_repeated_delegation_is_idempotent"))
        return suite


if __name__ == "__main__":
    test_suite = DnsAgentTestCase.get_test_suite()
    result = ut.TextTestRunner(verbosity=2).run(test_suite)

    errors = len(result.errors)
    failures = len(result.failures)
    passed = max(0, result.testsRun - errors - failures)
    summary = "score: %d of %d (%d errors, %d failures)" % (
        passed,
        result.testsRun,
        errors,
        failures,
    )
    if hasattr(DnsAgentTestCase, "init_dir") and os.path.isdir(
        os.path.join(DnsAgentTestCase.init_dir, DnsAgentTestCase.test_log)
    ):
        DnsAgentTestCase.printLog("==========Test=========")
        DnsAgentTestCase.printLog(summary)
    else:
        print("==========Test=========")
        print(summary)
