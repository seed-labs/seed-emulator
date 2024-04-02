#!/usr/bin/env python3
# encoding: utf-8

import random, json, os
import unittest as ut
from seedemu import *
from test import SeedEmuTestCase
from faker import Faker
from time import sleep

LOG_DIR = '/var/log/'
TMP_DIR = '/tmp/kubo/'

class KuboTestCase(SeedEmuTestCase):
    @classmethod
    def ctCmd(cls, container, cmd, **kwargs) -> Tuple[int, str]:
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
    def getCtKuboLabel(cls, container, key:str) -> str:
        """Get the value of a given label for the Kubo service.

        Parameters
        ----------
        container : Docker Container
            An instnace representing a Docker container.
        key : str
            A string representing the path of the label (e.g. 'version', 'test.groups')

        Returns
        -------
        str
            Value of that label.
        """
        label = container.attrs["Config"]["Labels"].get(f'org.seedsecuritylabs.seedemu.meta.kubo.{key}', '')
        try:
            label = json.loads(label)
        except:
            pass
        
        return label
    
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
    def getTestGroups(cls, container) -> list[str]:
        """Get test group as specified in container label.
           Label located at org.seedsecuritylabs.seedemu.meta.kubo.test.group
           Formatted as a list '["group1", "group2"]'

        Parameters
        ----------
        container : Docker Container
            Docker container object.

        Returns
        -------
        list[str]
            Label representing group; empty list if none.
        """
        labels = json.loads(container.attrs["Config"]["Labels"].get("org.seedsecuritylabs.seedemu.meta.kubo.test.group", ""))
        return labels
    
    
    @classmethod
    def addTestGroup(cls, container, group:str) -> None:
        """Add a container to a test group at runtime.

        Parameters
        ----------
        container : Docker Container
            A Docker container instance.
        group : str
            String representing a group (default groups are 'all' and 'boot').
        """
        if group not in cls.kubo_containers: cls.kubo_containers[group] = []
        cls.kubo_containers[group].append(container)
    
    
    @classmethod
    def getTestContainers(cls, group:str='all') -> list:
        """Get a list of container objects for a given test group.

        Parameters
        ----------
        group : str, optional
            Test group specified in container label (automatically 'all' and 'boot' groups), by default 'all'

        Returns
        -------
        list
            List of Docker container objects in the requested test group.
        """
        # Iterate through all Kubo containers and gather by group:
        return cls.kubo_containers.get(group, [])
    
    @classmethod
    def pullKuboLogs(cls, container) -> None:
        """Retrieve Kubo bootstrap log file from container and place it in the test_log directory.

        Parameters
        ----------
        container : Docker Container
            A Docker container running Kubo.
        """
        assert cls.isKubo(container), f"Cannot pull Kubo bootstrap logs; {cls.getCtName(container)} is not running Kubo."
        
        exit_code, output = cls.ctCmd(container, "cat /var/log/kubo_bootstrap.log")
        if exit_code == 0:
            log_contents = output.decode()
            log_file = os.path.join(cls.kubo_test_log_dir, f"{cls.getCtName(container)}_log")
            with open(log_file, 'w') as f:
                f.write(log_contents)
        else:
            raise Exception(output.decode())
    
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass(testLogOverwrite=True)
        
        # Populate some class variables:
        cls.fake = Faker()
        cls.regexPatterns = {
            'ipv4': '([0-9]{1,3}\.){3}[0-9]{1,3}',
            'port': '[0-9]{1,5}'
        }
        cls.kubo_log_dir = LOG_DIR if LOG_DIR.endswith('/') else LOG_DIR + '/'
        cls.kubo_tmp_dir = TMP_DIR if TMP_DIR.endswith('/') else TMP_DIR + '/'
            
        # Create additional log folder:
        cls.kubo_test_log_dir = os.path.join(cls.init_dir, cls.test_log, 'kubo_bootstrap/')
        # Create log directory if it doesn't already exist
        #    Note: won't exist if first run or if overwriting logs.
        if not os.path.exists(cls.kubo_test_log_dir):
            os.mkdir(cls.kubo_test_log_dir)
        
        cls.wait_until_all_containers_up(31)
        
        # Populate the cls.kubo_containers data structure: {group: [container1, container2]}
        cls.kubo_containers = {
            'all': []
        }
        for ct in cls.containers:
            # If this is any sort of Kubo container, add it to the "all" group:
            if cls.isKubo(ct):
                if 'all' not in cls.kubo_containers: cls.kubo_containers['all'] = []
                cls.kubo_containers['all'].append(ct)
                # If this is a boot node, add it to that group:
                if cls.isBoot(ct):
                    if 'boot' not in cls.kubo_containers: cls.kubo_containers['boot'] = []
                    cls.kubo_containers['boot'].append(ct)
                # If this is in another group, add it to that group:
                for g in cls.getTestGroups(ct):
                    if g not in cls.kubo_containers: cls.kubo_containers[g] = []
                    cls.kubo_containers[g].append(ct)
        cls.printLog(f'Test Containers: {json.dumps({group : len(cts) for group, cts in cls.kubo_containers.items()})}')
        
        # Just create a test file on few random nodes:
        numFiles:int = 3
        cls.kubo_file_host_containers = {}  # {container: {'cid': cid, 'contents': file_contents}}
        for i in range(numFiles):
            ct = random.choice(cls.getTestContainers())
            file_contents = f'Test File {i}\n{cls.fake.sentence()}'
            exit_code, output = cls.ctCmd(ct, f"""bash -c 'echo "{file_contents}" > test.txt'""", workdir=cls.kubo_tmp_dir)
            if exit_code != 0: cls.printLog(f'Failed to add test file ({exit_code}): {output.decode()}')
            cls.kubo_file_host_containers[ct] = {'contents': file_contents}
            
        return
    
    @classmethod
    def tearDownClass(cls) -> None:
        # Retrieve bootstrapping log files from each node before teardown:
        for ct in cls.getTestContainers():
            try:
                cls.pullKuboLogs(ct)
            except Exception as e:
                cls.printLog(f'KuboTestCase::tearDownClass FAILED\n\t{e}')
                cls.printLog(f"\t{cls.ctCmd(ct, f'ls {cls.kubo_log_dir}')[1].decode()}")
        
        super().tearDownClass()
    
    
    def test_kubo_install(self):
        errors = []  # Track errors to make assertions non-fatal
        
        self.printLog(f'{" Test Case: test_kubo_install ":=^100}')
        for ct in self.getTestContainers():
            exit_code, _ = self.ctCmd(ct, "ipfs")
            self.printLog(f'{self.getCtName(ct)}: ', end='')
            try:
                self.assertEqual(exit_code, 0)
            except Exception as e:
                errors.append(e)
                self.printLog('[FAILURE]')
            else:
                self.printLog('[SUCCESS]')
            
        # Ensure no errors have been raised:
        self.assertEqual(errors, [])
        
    
    def test_kubo_version(self):
        errors = []  # Track errors to make assertions non-fatal
        
        self.printLog(f'{" Test Case: test_kubo_version ":=^100}')
        
        for ct in self.getTestContainers():
            self.printLog(f'{self.getCtName(ct)}: ', end='')
            exit_code, output = self.ctCmd(ct, 'ipfs version')
            kuboVersion = re.search('(?:\d{1,3}\.){2}(?:\d{1,3})', output.decode())
            intendedVersion = re.search('(?:\d{1,3}\.){2}(?:\d{1,3})', self.getCtKuboLabel(ct, 'version'))
            try:
                self.assertIsNotNone(kuboVersion)
                self.assertIsNotNone(intendedVersion)
                kuboVersion = kuboVersion.group(0)
                intendedVersion = intendedVersion.group(0)
                self.assertEqual(kuboVersion, intendedVersion)
            except Exception as e:
                errors.append(e)
                self.printLog(f'[FAILURE] {type(e)}: {e}')
            else:
                self.printLog(f'[SUCCESS] {kuboVersion}')
        
        # Ensure no errors have been raised:
        self.assertEqual(errors, [])
            
    def test_bootstrap_script(self):
        self.printLog(f'{" Test Case: test_bootstrap_script ":=^100}')
        errors = []
        for ct in self.getTestContainers():
            self.printLog(f'{self.getCtName(ct)}:', end='')
            
            # Make sure bootstrap script is present:
            self.printLog('\t\tScript Present ', end='')
            exit_code, _ = self.ctCmd(ct, f'cat {self.kubo_tmp_dir}bootstrap.sh')
            try:
                self.assertEqual(exit_code, 0)
            except Exception as e:
                errors.append(e)
                self.printLog('[FAILURE]', end='')
            else:
                self.printLog('[SUCCESS]', end='')
            
            # Make sure bootstrap script has run:
            self.printLog('\t\tScript Run ', end='')
            exit_code, _ = self.ctCmd(ct, f'cat {self.kubo_log_dir}kubo_bootstrap.log')
            try:
                self.assertEqual(exit_code, 0)
            except Exception as e:
                errors.append(e)
                self.printLog('[FAILURE]', end='')
            else:
                self.printLog('[SUCCESS]')
                
        # Ensure no errors have been raised:
        self.assertEqual(errors, [])
    
    def test_bootstrap_list(self):
        errors = []  # Track errors to make assertions non-fatal
        
        self.printLog(f'{" Test Case: test_bootstrap_list ":=^100}')
        for ct in self.getTestContainers(group='basic'):
            exit_code, output = self.ctCmd(ct, "ipfs bootstrap list")
            bootstrap_list = output.decode().splitlines()
            self.printLog(f'{self.getCtName(ct)}:')
            for b in bootstrap_list:
                self.printLog(f'\t{b}')
                try:
                    self.assertRegexpMatches(b, f'/ip4/{self.regexPatterns["ipv4"]}/tcp/{self.regexPatterns["port"]}/p2p/.*')
                except Exception as e:
                    errors.append(e)
                    self.printLog(f'\t[FAILURE] {type(e)}: {e}')
                else:
                    try:
                        self.assertEqual(exit_code, 0)
                        self.assertEqual(len(self.getTestContainers(group='boot')), len(bootstrap_list))
                    except Exception as e:
                        errors.append(e)
                        self.printLog(f'\t[FAILURE] {type(e)}: {e}')

        # Raise exception if assertions failed in above tests:
        self.assertEqual(errors, [])
    
    def test_service_config(self):
        self.printLog(f'{" Test Case: test_service_config ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        for ct in self.getTestContainers(group='basic'):
            self.printLog(f'{self.getCtName(ct)}:', end='')

            # Confirm RPC API address bound to all interfaces:
            self.printLog('\t\tRPC API ', end='')
            exit_code, output = self.ctCmd(ct, 'ipfs config Addresses.API')
            try:
                self.assertEqual(exit_code, 0)
                self.assertEqual(output.decode().strip(), '/ip4/0.0.0.0/tcp/5001')
            except Exception as e:
                self.printLog('[FAILURE]', end='')
                errors.append(e)
            else:
                self.printLog('[SUCCESS]', end='')
            
            # Confirm HTTP Gateway address bound to all interfaces:
            self.printLog('\t\tHTTP Gateway ', end='')
            exit_code, output = self.ctCmd(ct, 'ipfs config Addresses.Gateway')
            try:
                self.assertEqual(exit_code, 0)
                self.assertEqual(output.decode().strip(), '/ip4/0.0.0.0/tcp/8080')
            except Exception as e:
                self.printLog('[FAILURE]')
                errors.append(e)
            else:
                self.printLog('[SUCCESS]')
            
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
    
    def test_peering(self):
        self.printLog(f'{" Test Case: test_peering ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        for ct in self.getTestContainers(group='basic'):
            # Attempt to fetch peers multiple times to allow peering relationships to form:
            peers = []
            attempts = 5
            while (attempts > 0) and (len(peers) < len(self.getTestContainers(group='basic'))):
                exit_code, output = self.ctCmd(ct, "ipfs swarm peers")
                if exit_code == 0:
                    peers = output.decode().splitlines()
                attempts -= 1
                sleep(5)
            
            # Print results to logs:
            self.printLog(f'{self.getCtName(ct)} ({len(peers)}): ', end='')
            try:
                self.assertGreaterEqual(len(peers), len(self.getTestContainers(group='basic')))
            except Exception as e:
                errors.append(e)
                self.printLog('[FAILURE]')
            else:
                self.printLog('[SUCCESS]')
            
            # Print peers to logs:
            for p in peers:
                self.printLog(f'\t{p}')
        
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
                
    
    def test_kubo_add(self):
        self.printLog(f'{" Test Case: test_kubo_add ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        # Each of these containers has a file test.txt in the Kubo temp directory (KuboTestCase::SetUpClass):
        for ct in self.kubo_file_host_containers.keys():
            if 'basic' in self.getTestGroups(ct):
                self.printLog(f'{self.getCtName(ct)}: ', end='')
                
                exit_code, output = self.ctCmd(ct, 'ipfs add test.txt', workdir=self.kubo_tmp_dir)
                # exit_code, output = self.ctCmd(ct, f"bash -c 'ls ; cat test.txt'", workdir=self.kubo_tmp_dir)
                try:
                    self.assertEqual(exit_code, 0)
                except Exception as e:
                    errors.append(e)
                    self.printLog(f'[FAILURE] {type(e)}: {e}\n\t{output.decode()}')
                else:
                    # Get CID from output of the ips add <file> command:
                    cid = re.search('added ([a-zA-Z0-9]+) \S+', output.decode().strip())
                
                    # Process CID further if it was found in the IPFS output:
                    try:
                        self.assertIsNotNone(cid)
                    except Exception as e:
                        errors.append(e)
                        self.printLog(f'[FAILURE] {type(e)}: {e}\n\t{output.decode()}')
                    else:
                        cid = cid.group(1)
                        self.kubo_file_host_containers[ct]['cid'] = cid
                        self.printLog(f'[SUCCESS] Added file with CID of {cid}')
            
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
        
    def test_kubo_cat(self):
        self.printLog(f'{" Test Case: test_kubo_cat ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        # Make sure that each Kubo node can access each file added:
        for ct in self.getTestContainers(group='basic'):
            self.printLog(f'{self.getCtName(ct)}:')
            
            # Check that node can access file through IPFS (skip if this node originates the data):
            for host_ct, file_info in self.kubo_file_host_containers.items():
                self.printLog(f'\tipfs cat {file_info["cid"]} ', end='')
                if host_ct != ct:
                    exit_code, output = self.ctCmd(ct, f'ipfs cat {file_info["cid"]}', demux=True)
                    
                    try:
                        self.assertEqual(exit_code, 0)
                        self.assertEqual(output[0].decode().strip(), file_info["contents"])
                    except Exception as e:
                        errors.append(e)
                        self.printLog(f'[FAILURE] {type(e)}: {e}\n\t\t{output}')
                    else:
                        self.printLog(f'[SUCCESS]')
                else:
                    self.printLog('[SKIPPED] *')
                        
        
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
        
    
    def test_specify_profile(self):
        self.printLog(f'{" Test Case: test_specify_profile ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        # Find the container with profile testing flag:
        for ct in self.getTestContainers(group='profile'):
            self.printLog(f'{self.getCtName(ct)}: ', end='')
            with open(os.path.join(self.init_dir, self.test_log, 'config.json'), 'w') as f:
                exit_code, output = self.ctCmd(ct, 'cat config', workdir='/root/.ipfs')
                try:
                    self.assertEqual(exit_code, 0)
                except Exception as e:
                    errors.append(e)
                    self.printLog(f'[FAILURE] {type(e)}: {e}')
                else:
                    config = json.loads(output)
                    try:
                        # Check against changes this profile applies to the config:
                        self.assertIn('Type', config.get('Swarm').get('ConnMgr'))
                        self.assertEqual(config.get('Reprovider').get('Interval'), '0s')
                        self.assertEqual(config.get('AutoNAT').get('ServiceMode'), 'disabled')
                    except Exception as e:
                        errors.append(e)
                        self.printLog(f'[FAILURE] {type(e)}: {e}')
                    else:
                        # Success!
                        self.printLog('[SUCCESS]')
                    
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
        
    def test_custom_config(self):
        self.printLog(f'{" Test Case: test_custom_config ":=^100}')
        errors = []  # Store failed assertions to be nonfatal
        
        # Find the container with config testing flag:
        for ct in self.getTestContainers(group='config'):
            self.printLog(f'{self.getCtName(ct)}: ', end='')
            
            # Get actual config from the container:
            exit_code, output = self.ctCmd(ct, 'cat config', workdir='/root/.ipfs')
            try:
                self.assertEqual(exit_code, 0)
            except Exception as e:
                errors.append(e)
                self.printLog(f'[FAILURE] {type(e)}: {e}')
            else:
                ct_config = json.loads(output)
            
                # Get the test config from a file:
                with open(os.path.join(self.emulator_code_dir, 'sample-config.json'), 'r') as f:
                    test_config = json.loads(f.read())
                    
                # Ensure that actual and test config are the same:
                try:
                    self.assertEqual(ct_config, test_config)
                except Exception as e:
                    errors.append(e)
                    self.printLog(f'[FAILURE] {type(e)}: {e}')
                else:
                    self.printLog('[SUCCESS]')
                
        # Ensure no failed assertions have ocurred:
        self.assertEqual(errors, [])
            
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_kubo_install'))
        test_suite.addTest(cls('test_kubo_version'))
        test_suite.addTest(cls('test_bootstrap_script'))
        test_suite.addTest(cls('test_bootstrap_list'))
        test_suite.addTest(cls('test_service_config'))
        test_suite.addTest(cls('test_peering'))
        test_suite.addTest(cls('test_kubo_add'))
        test_suite.addTest(cls('test_kubo_cat'))
        test_suite.addTest(cls('test_specify_profile'))
        test_suite.addTest(cls('test_custom_config'))
        return test_suite
    

if __name__ == "__main__":
    test_suite = KuboTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    
    KuboTestCase.printLog("----------Test---------")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    KuboTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
