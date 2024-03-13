import unittest, os, time, json, docker
import subprocess as sp
from seedemu import *
from time import sleep

EMU_CLASS_NAME = 'KuboService'

class TestKuboServer(unittest.TestCase):
    def setUp(self):
        self.emu = Emulator()
        self.emu.load('./base-component.bin')
    
    def dockerRun(self):
        # Render and compile 
        docker = Docker(internetMapEnabled=True)
        self.emu.render()
        self.emu.compile(docker, '../emulator', override = True)
        # os.system('docker-compose build -f ../emulator/docker-compose.yml')
        # os.system('docker-compose -f ../emulator/docker-compose.yml up -d --build &>/dev/null')
        cmd = ['docker-compose', '-f', '../emulator/docker-compose.yml', 'up', '-d', '--build']
        sp.run(cmd, check=True, capture_output=True)
        sleep(30)
        
    def tearDown(self):
        # os.system('docker-compose -f ../emulator/docker-compose.yml down -v &>/dev/null')
        # cmd = ['docker-compose', '-f', '../emulator/docker-compose.yml', 'down',  '-v']
        # sp.run(cmd, check=True)
        # time.sleep(30)
        pass
        
    def getDockerInfo(self) -> dict:
        client = docker.from_env()
        containers = client.containers.list()
        info = {}
        
        for container in containers:
            cmd = ['docker', 'inspect', "--format='{{json .Config.Labels}}'", container.short_id]
            inspection = json.loads(sp.check_output(cmd).decode().rstrip().rstrip("'").lstrip("'"))
            try:
                _, numPeers = container.exec_run('ipfs swarm peers | wc -l')
                numPeers = numPeers.decode()
            except:
                numPeers = None
            try:
                _, numBoots = container.exec_run('ipfs bootstrap list | wc -l')
                numBoots = numBoots.decode()
            except:
                numBoots = None
            
            if EMU_CLASS_NAME not in info.get('org.seedsecuritylabs.seedemu.meta.class', []):
                info['peer_count'] = numPeers
                info['boot_count'] = numBoots
                info[container.short_id] = inspection
            
        return info 
        
    def test_basic_setup(self):
        ipfs = KuboService()
        numHosts:int = 1
        i:int = 0
        bootnodes = []

        for asNum in range(150, 172):
            try:
                curAS = self.emu.getLayer('Base').getAutonomousSystem(asNum)
            except:
                print(f'AS {asNum} does\'t appear to exist.')
            else:
                for h in range(numHosts):
                    vnode = f'kubo-{i}'
                    displayName = f'Kubo-{i}_'
                    cur = ipfs.install(vnode)
                    if i % 5 == 0:
                        cur.setBootNode(True)
                        displayName += 'Boot'
                        bootnodes.append(vnode)
                    else:
                        displayName += 'Peer'
                    
                    self.emu.getVirtualNode(vnode).setDisplayName(displayName)
                    self.emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName=f'host_{h}')))
                    i += 1
                
        self.emu.addLayer(ipfs)
        
        self.dockerRun()
        with open('testOutput.json', 'w') as f:
            f.write(json.dumps(self.getDockerInfo(), indent=2))
        self.assertTrue(True)
        
    
#     def test_init_distro(self):
#         ...
        
#     def test_init_version(self):
#         # Try: v0.27.0, v0.26.0
#         ...
        
#     def test_init_arch(self):
#         ...
        
#     def test_init_is_bootnode(self):
#         ...
        
#     def test_init_config(self):
#         ...
        
#     def test_init_profile(self):
#         ...
    
#     def test_install(self):
#         ...
        
#     def test_isBootNode(self):
#         ...
        
#     def test_setBootNode(self):
#         ...
        
#     def test_importConfig(self):
#         ...
        
#     def test_setProfile(self):
#         ...
        
        
        
class TestDottedDict(unittest.TestCase):
    """Test construction of the KuboUtils.DottedDict class.
    """
    
    def setUp(self):
        pass
    
    def test_constructor(self):
        dd = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                1: ['1', '11', '111']
            }
        })
        
        d = {
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                1: ['1', '11', '111']
            }
        }
        
        self.assertEqual(dd, d)
        self.assertEqual(DottedDict(), {})
        self.assertEqual(DottedDict([('test', True), ('a', 5)]), {'test': True, 'a': 5})
        # self.assertEqual(DottedDict([('test', True), ('a', [('b', [('c', 3)]), (1, ['1', '11', '111'])])]), dd)
    
    def test_getitem(self):
        d = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111']
            }
        })
        
        self.assertTrue(d['test'])
        self.assertEqual(d['a.b.c'], 3)
        self.assertEqual(d['a.1'], ['1', '11', '111'])
        
        with self.assertRaises(TypeError):
            d[0]
        
        
    def test_setitem(self):
        d = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        
        d['test'] = False
        self.assertEqual(d['test'], False)
        d['a.d'] = 'New'
        self.assertEqual(d['a.d'], 'New')
        d['a.b.c'] = 'Done'
        self.assertEqual(d['a.b.c'], 'Done')
        d['a.1'].append('2222')
        self.assertIn('2222', d['a.1'])
        d['test.blue'] = True
        self.assertIsInstance(d['test'], DottedDict)
        self.assertEqual(d['test.blue'], True)
        with self.assertRaises(TypeError):
            d[1] = 10
        d['new'] = {"x-test-header": ["test"]}
        self.assertEqual(d['new'], {"x-test-header": ["test"]})
        
    def test_delitem(self):
        d = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        with self.assertRaises(KeyError):
            del d['a.b']
            d['a.b']
        
        del d['a.1'][0]
        self.assertEqual(d['a.1'][0], '11')
        
        with self.assertRaises(KeyError):
            del d['a']
            d['a']
            
        with self.assertRaises(TypeError):
            del d[0]
            
    def test_contains(self):
        d = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        self.assertIn('test', d)
        self.assertIn('a', d)
        self.assertIn('a.b', d)
        self.assertIn('a.b.c', d)
        self.assertIn('a.1', d)
        
        self.assertNotIn('1', d)
        self.assertNotIn('test.a', d)
        self.assertNotIn('a.b.1', d)
        self.assertNotIn('a.b.c.d', d)
        
    def test_merge(self):
        d = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        newDotted = DottedDict({
            'new': True,
            'a': {
                'f': 5,
                'b': {
                    'c': 100,
                    'e': {
                        'purple': False
                    }
                }
            }
        })
        
        newDict = {
            'new': True,
            'a': {
                'f': 5,
                'b': {
                    'c': 100,
                    'e': {
                        'purple': False
                    }
                }
            }
        }
        
        mergedDotted = DottedDict({
            'new': True,
            'test': True,
            'a': {
                'f': 5,
                'b': {
                    'c': 100,
                    'e': {
                        'purple': False
                    }
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        d1 = d.copy()
        d2 = d.copy()
        d1.merge(newDotted)
        self.assertEqual(d1, mergedDotted)
        d2.merge(newDict)
        self.assertEqual(d2, mergedDotted)
        
    def test_json(self):
        dd = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        d = {
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        }
        
        self.assertEqual(json.dumps(dd), json.dumps(d))
        
    def test_empty(self):
        dd1 = DottedDict()
        dd2 = DottedDict({
            'test': True,
            'a': {
                'b': {
                    'c': 3
                },
                '1': ['1', '11', '111'],
                'd': 'Old'
            }
        })
        
        self.assertTrue(dd1.empty())
        self.assertFalse(dd2.empty())
        
                
if __name__ == "__main__":
    unittest.main()