#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
import os
import shutil
import getopt
import sys
import docker
import time
import subprocess
from typing import List

from tests.utils.compose import detect_compose_command

class SeedEmuTestCase(ut.TestCase):
    init_dir:    str
    emulator_code_dir:   str
    output_dir: str
    emulator_script_name: str
    test_log: str
    container_count_before_up_container: int
    container_count_after_up_container: int
    docker_compose_version:int
    online_testing:bool

    @classmethod
    def setUpClass(cls, testLogOverwrite:bool=False, online:bool=True) -> None:
        '''!
        @brief A classmethod to construct the some thing before
        this test case is started. For this test case, it will create
        a test_log directory, create emulation files, build containers
        and up containers.

        Parameters
        ----------
        testLogOverwrite : bool, optional
            Set True if you want to overwrite testing logs each time, by default False
        online : bool, optional
            Set False if you don't want to compile and run the emulation, by default True
        '''
        cls.init_dir = os.path.dirname(os.path.abspath(sys.modules[cls.__module__].__file__))
        cls.cur_dir = os.path.dirname(__file__)
        cls.emulator_code_dir = os.path.join(cls.init_dir, "emulator-code")
        cls.output_dir = os.path.join(cls.emulator_code_dir, "output")
        cls.emulator_script_name = "test-emulator.py"
        cls.test_log = "test_log"
        cls.test_log_overwrite = testLogOverwrite
        cls.online_testing = online

        # Get information from local Docker:
        if cls.online_testing:
            cls.client = docker.from_env()
            cls.container_count_before_up_container = len(cls.client.containers.list())

        os.chdir(cls.init_dir)
        cls.createDirectory(cls.test_log, cls.test_log_overwrite)
        cls.printLog("==============================")
        cls.printLog("{} Start".format(sys.modules[cls.__module__].__name__))
        cls.printLog("==============================")

        # if system is using a docker-compose version 2, test is done with version2.
        if cls.online_testing:
            cls.compose_cmd, cls.docker_compose_version = detect_compose_command()

        if cls.online_testing:
            cls.gen_emulation_files()
            cls.check_emulation_files()
            cls.build_emulator()
            cls.up_emulator()

        return

    @classmethod
    def tearDownClass(cls) -> None:
        '''
        @brief A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        if cls.online_testing:
            cls.down_emulator()

        return super().tearDownClass()

    @classmethod
    def gen_emulation_files(cls):
        """!
        @brief generate emulation files.
        """
        cls.printLog("Generating Emulation Files...")

        os.chdir(cls.emulator_code_dir)

        log_file = os.path.join(cls.init_dir, cls.test_log, "compile_log")
        f = open(log_file, 'w')
        if os.path.exists(cls.output_dir):
            shutil.rmtree(cls.output_dir)

        result = subprocess.run(["python3",  cls.emulator_script_name], stdout=f, stderr=f)
        f.close()
        os.chdir(cls.init_dir)
        assert result.returncode == 0, "emulation files generation failed"
        cls.printLog("gen_emulation_files: succeed")

    @classmethod
    def check_emulation_files(cls):
        """!
        pre-build hook to check if emulator compile output is valid.
        There's no point in building a misconfigured simulation which won't run.
        So this method provides a quick-out fast fail.
        """
        pass

    @classmethod
    def build_emulator(cls):
        """!
        @brief build all docker containers.
        """
        cls.printLog("Building Docker Containers...")
        os.chdir(os.path.join(cls.emulator_code_dir, cls.output_dir))

        log_file = os.path.join(cls.init_dir, cls.test_log, "build_log")
        f = open(log_file, 'w')

        # Temp Fix for Docker BuildKit
        # Disable BuildKit to avoid issues with Docker Compose v2
        env = os.environ.copy()
        env['DOCKER_BUILDKIT'] = '0'
        
        result = subprocess.run(cls.compose_cmd + ["build"], stderr=f, stdout=f, env=env)

        f.close()
        os.system("echo 'y' | docker system prune > /dev/null")
        os.chdir(cls.init_dir)
        assert result.returncode == 0, "docker build failed"
        cls.printLog("build_emulator: succeed")

    @classmethod
    def up_emulator(cls):
        """!
        @brief up all containers.
        """
        os.chdir(os.path.join(cls.emulator_code_dir, cls.output_dir))
        log_path = os.path.join(cls.init_dir, cls.test_log, "containers_log")
        log_file = open(log_path, "w")
        cls.compose_process = subprocess.Popen(
            cls.compose_cmd + ["up"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        cls.compose_log_handle = log_file
        os.chdir(cls.init_dir)

    @classmethod
    def down_emulator(cls):
        """!
        @brief down all containers.
        """
        os.chdir(os.path.join(cls.emulator_code_dir, cls.output_dir))
        subprocess.run(cls.compose_cmd + ["down"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if getattr(cls, "compose_process", None):
            try:
                cls.compose_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                cls.compose_process.kill()
                cls.compose_process.wait()
            cls.compose_process = None
        if getattr(cls, "compose_log_handle", None):
            cls.compose_log_handle.close()
            cls.compose_log_handle = None

        os.system("echo 'y' | docker system prune > /dev/null")
        os.chdir(cls.init_dir)

    @classmethod
    def detect_compose_command(cls) -> List[str]:
        # Backwards compatibility for subclasses expecting this method.
        cmd, version = detect_compose_command()
        cls.docker_compose_version = version
        return cmd

    @classmethod
    def createDirectory(cls, directory:str, override:bool = False):
        """!
        @brief create directory.

        @param directory directory name to create.
        @param override if true, override the existing directory.
        """
        cur = os.getcwd()
        if os.path.exists(directory):
            if override:
                shutil.rmtree(directory)
            else:
                i = 0
                while True:
                    old_dir = "{}_{}".format(directory, i)
                    if not os.path.exists(old_dir):
                        break
                    i += 1
                    assert i<100, "remove log history. history can be stored up to 100."
                os.rename(directory, old_dir)
        os.mkdir(directory)
        os.chdir(cur)

    @classmethod
    def wait_until_all_containers_up(cls, total_containers:int) -> None:
        """!
        @brief wait until all containers up before running a testcase.

        @param total_containers a expected total container counts
        """
        current_time = time.time()
        while True:
            cls.printLog("--------------------------------------------------")
            cls.printLog("------ Waiting until all containers up : {} ------".format(total_containers))

            cls.containers = cls.client.containers.list()

            cur_container_count = len(cls.containers) - cls.container_count_before_up_container
            cls.printLog("current containers counts : ", cur_container_count)
            if cur_container_count >= total_containers:
                # wait until the initial setting in containers such as bird configuration.
                time.sleep(30)
                return True
            if time.time() - current_time > 300:
                cls.printLog("TimeExhausted: 5 min")
                cls.printLog("Containers up failed")
                return False
            time.sleep(10)

    @classmethod
    def ping_test(cls, container, ip, expected_exit_code=0):
        """!
        @brief test ping 3 times

        @param container container to run a ping test
        @param ip destination ip to send a ping signal
        @param expected_exit_code if expected result is success, expected_exit_code is 0.

        @returns true if exit code of ping test is same with the expected_exit_code
        """

        exit_code, output = container.exec_run("ping -c 3 {}".format(ip))
        if exit_code == 0: cls.printLog("ping test {} Succeed".format(ip))
        else: cls.printLog("ping test {} Failed".format(ip))
        return exit_code == expected_exit_code

    @classmethod
    def http_get_test(cls, container, dst, expected_status_code:int = 200) -> bool:
        """!
        @brief Send an HTTP GET request with curl.

        @param container Container to send the request
        @param dst Request destination

        @returns True if the HTTP status code of the response is `expected_status_code`.
        """
        ec, output = container.exec_run(f"curl -so /dev/null -w '%{{http_code}}' {dst}")
        if ec != 0:
            cls.printLog(f"http GET {dst} test failed: {output.decode()}")
            return False
        http_status = int(output.decode())
        if http_status != expected_status_code:
            cls.printLog(f"http GET test {dst} failed with HTTP status {http_status}"
                         f", expected {expected_status_code}")
            return False
        cls.printLog(f"http GET {dst} test succeeded")
        return True

    @classmethod
    def get_test_suite(cls):
        """!
        @brief create a test suite with an order and return it.

        @returns test suite.
        """

        '''
        example)
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_internet_connection'))
        test_suite.addTest(cls('test_customized_ip_address'))
        test_suite.addTest(cls('test_real_world_as'))
        return test_suite
        '''

        raise NotImplementedError('getTestSuite not implemented')

    @classmethod
    def printLog(cls, *args, **kwargs):
        """!
        @brief print logs to a terminal and a file .
        """

        print(*args, **kwargs)
        with open(os.path.join(cls.init_dir, cls.test_log, 'test_result.txt'),'a') as file:
            print(*args, **kwargs, file=file)
        with open(os.path.join(os.path.join(cls.cur_dir, 'test_result.txt')),'a') as file:
            print(*args, **kwargs, file=file)
