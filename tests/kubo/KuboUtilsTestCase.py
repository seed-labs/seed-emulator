#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu.services.KuboService.KuboUtils import *
from seedemu import *
from tests import SeedEmuTestCase
from faker import Faker
from faker.providers import internet
from time import time

class DottedDictTestCase(SeedEmuTestCase):
    """Test cases that evaluate KuboUtils::DottedDict.
    """
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass(testLogOverwrite=False, online=False)
        
        # Initialize some class variables:
        cls.simpleDict = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'red': True, 'blue': 50}
        cls.nestedDict = {
            'a': {'b': 2},
            'test': {'1': 2},
            'c': 3,
            'blue': 'red'
        }
        cls.nestedDictDeep = {
            'a': {
                'b': 2,
                'c': {
                    'red': False,
                    'orange': True,
                    'yellow': False,
                    'green': True,
                    'blue': True,
                    'purple': True,
                    'pink': True
                },
                'deepest': {
                    'level1': {
                        'level2': {
                            'level3': {
                                'level4': {
                                    'level5': 'done'
                                }
                            }
                        }
                    }
                }
            },
            'simple': True,
            ' ': False,
            ',': {
                '!': '#'
            }
        }
        
        return
    
    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()
    
    def test_init_empty(self):
        self.printLog(f'{" Test Case: test_init_empty ":=^100}')
        
        # Create a test case for initializing with nothing:
        dd = DottedDict()
        self.assertIsInstance(dd, DottedDict, 'Not a DottedDict')
        self.assertTrue(dd.empty(), 'DottedDict returns not empty')
        self.printLog(f'{"DottedDict()":<30}[PASS]')

        # Create a test case for initializing with multiple empty data types:
        cases = [[], {}, set(), tuple()]
        for case in cases:
            with self.subTest(case=type(case)):
                dd = DottedDict(case)
                self.assertIsInstance(dd, DottedDict, 'Not a DottedDict')
                self.assertTrue(dd.empty(), 'DottedDict returns not empty')
                self.printLog(f'{f"DottedDict({case})":<30}[PASS]')
                
    
    def test_init_good(self):
        self.printLog(f'{" Test Case: test_init_good ":=^100}')
        
        # Create a test case for multiple data types that should succeed:
        cases = [
            [('a', 1), ('b', 2), (5, 'ff'), (55.7, True)],
            [('a', 1), ('b', [('c', [('d', 4), ('e', 5)])]), ('f', 6)],
            (('a', 1), ('b', 2), (5, 'ff'), (55.7, True)),
            (('a', 1), ('b', ('c', (('d', 4), ('e', 5)))), ('f', 6)),
            {('a', 1), ('b', 2), (5, 'ff'), (55.7, True)},
            {'a': 1, 'b': 2, 5: 'ff', 55.7: True},
            {'a': 1, 'b': {'c': {'d': 4, 'e': 5}}, 'f': 6}
        ]
        for test in cases:
            with self.subTest(case=test, type=type(test)):
                dd = DottedDict(test)
                self.assertIsInstance(dd, DottedDict, 'Instance is not a DottedDict')
                self.assertEqual(dd, dict(test), 'DottedDict did not produce expected data structure')
                self.assertDictEqual(dd, dict(test), 'DottedDict did not produce expected data structure')
                self.printLog(f'{f"DottedDict({test})":<75}[PASS]')
       
                
    def test_init_bad(self):
        self.printLog(f'{" Test Case: test_init_bad ":=^100}')
        # Create a test case for multiple data types and constructions that should fail:
        cases = [
            True, False, 1, 346.72, 55555,
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            range(10),
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
            (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
            [(1, 'a'), 2, 3],
            (1, (2, 'b'), 3, 4, 5),
            [{'a': 1}, True]
        ]
        for test in cases:
            with self.subTest(case=test, type=type(test)):
                try:
                    dd = DottedDict(test)
                except Exception as ddErr:
                # self.assertIsInstance(dd, DottedDict, 'Instance is not a DottedDict')
                    try:
                        d = dict(test)
                    except Exception as dErr:
                        self.assertEqual(type(ddErr), type(dErr), 'DottedDict should raise same exception type as dict.')
                    else:
                        self.printLog(f'Case: {test} {type(test)}\n{dd}')
                        self.fail('dict init was successful but DottedDict was not')
                else:
                    # Initialization was successful; does that work for dict:
                    self.printLog(f'Case: {test} {type(test)}\n{dd}')
                    self.assertDictEqual(dd, dict(test), 'DottedDict was successful but dict was not')
                self.printLog(f'{f"DottedDict({test})":<50}[PASS]')
                
                
    def test_get_item_expected(self):
        self.printLog(f'{" Test Case: test_get_item_expected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = [('simple', True), ('a.b', 2),
                 ('a.c', DottedDict({'red': False, 'orange': True, 'yellow': False, 'green': True, 'blue': True, 'purple': True, 'pink': True})),
                 ('a.c.red', False), ('a.c.orange', True), ('a.c.blue', True),
                 ('a.deepest', DottedDict({'level1': {'level2': {'level3': {'level4': {'level5': 'done'}}}}})),
                 ('a.deepest.level1.level2.level3.level4.level5', 'done'),
                 ('simple', True),
                 (' ', False),
                 (',', DottedDict({'!': '#'})),
                 (',.!', '#')
        ]
        # Test cases:
        dd = DottedDict(self.nestedDictDeep.copy())
        for testKey, expectedVal in cases:
            with self.subTest(case=testKey):
                self.assertEqual(dd[testKey], expectedVal, 'DottedDict::getitem did not get expected value.')
                self.printLog(f'{f"DottedDict[{testKey}] = {dd[testKey]}":<90}[PASS]')

                
                
    def test_get_item_unexpected(self):
        self.printLog(f'{" Test Case: test_get_item_unexpected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = ['', '.', '\t', '.a', 'a.', 'a.b.', 'a.b.c', 'a.c.c', 'a.c.red.orange', 'a.c.orange.',
                 'a.c.blue.deepest', 'a..deepest', '..a.deepest.level1.level2.level3.level4.level5..', 'simple..'
        ]
        # Test cases:
        dd = DottedDict(self.nestedDictDeep.copy())
        for testKey in cases:
            with self.subTest(case=testKey):
                with self.assertRaises(KeyError, msg='Invalid key on getitem did not raise KeyError.'):
                    dd[testKey]
                self.assertDictEqual(dd, self.nestedDictDeep, 'DottedDict changed on getitem operation.')
                self.printLog(f'{f"DottedDict[{testKey}] -> KeyError":<75}[PASS]')
                
                
    def test_set_item_expected(self):
        self.printLog(f'{" Test Case: test_set_item_expected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = [('simple', False), ('a.b', 4),
                 ('a.c', DottedDict({'level1': 1, 'level2': {'diff': 4, 'bbb': False}})),
                 ('a.c.red', 6), ('a.c.orange', 'apple'), ('a.c.blue', 36.788),
                 ('a.deepest.level1.level2.level3.level4.level5', 'ready'),
                 ('a.deepest', DottedDict({'apple': {'bicycle': {'car': {'dream': {'engine': 'huh', 'fog': 'yes', 'golf': 'ball'}}}}})),
                 ('simple', False),
                 (' ', True),
                 (',.!', '#'),
                 (',', ['!', '#']),
        ]
        # Test cases:
        for testKey, expectedVal in cases:
            with self.subTest(case=testKey):
                dd = DottedDict(self.nestedDictDeep.copy())
                dd[testKey] = expectedVal
                self.assertEqual(dd[testKey], expectedVal, 'Getting set item should match expected value.')
                self.printLog(f'{f"DottedDict[{testKey}] = {dd[testKey]}":<120}[PASS]')
                
        # Extra test case:
        dd = DottedDict(self.nestedDictDeep)
        dd['a.deepest.level1.newLeaf'] = True
        self.assertEqual(dd['a.deepest.level1.level2.level3.level4.level5'], 'done')
        self.assertEqual(dd['a.deepest.level1.newLeaf'], True)
        
        
    def test_set_item_unexpected(self):
        self.printLog(f'{" Test Case: test_set_item_unexpected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = ['', '.', '.a', 'a.', 'a.b.', 'a..b..c', 'a.c.orange.',
                 'a..deepest', '..a.deepest.level1.level2.level3.level4.level5..', 'simple..'
        ]
        # Test cases:
        dd = DottedDict(self.nestedDictDeep)
        for testKey in cases:
            with self.subTest(case=testKey):
                with self.assertRaises(KeyError, msg='Should raise KeyError for invalid key on set item.'):
                    dd[testKey] = 'test 1 2 3'
                self.printLog(f'{f"DottedDict[{testKey}] -> KeyError":<75}[PASS]')
                
    
    def test_del_item_expected(self):
        self.printLog(f'{" Test Case: test_del_item_expected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = [
            'simple', 'a.b', 'a.c', 'a.c.red', 'a.c.orange', 'a.c.blue',
            'a.deepest', 'a.deepest.level1.level2.level3.level4.level5',
            'simple', ' ', ',', ',.!'
        ]
        # Test cases:
        for testKey in cases:
            with self.subTest(case=testKey):
                dd = DottedDict(self.nestedDictDeep.copy())
                # Trigger __delitem__:
                del dd[testKey]
                # Should no longer be in DottedDict:
                self.assertNotIn(testKey, dd, 'Deleted item should no longer be in DottedDict.')
                # Should now raise KeyError on get:
                with self.assertRaises(KeyError, msg='Getting deleted item from DottedDict should raise KeyError.'):
                    dd[testKey]
                self.printLog(f'{f"del DottedDict[{testKey}]":<75}[PASS]')
        
    
    def test_del_item_unexpected(self):
        self.printLog(f'{" Test Case: test_del_item_unexpected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = [
            'simpl', '.a.b', 'a..c', 'a..c..red', '..a.c.orange', 'a.c.blue.',
            'a.deepest...', 'a.deepest.level2.level2.level3.level4.level5',
            'simple.', '', ',.', ',.!.'
        ]
        # Test cases:
        for testKey in cases:
            with self.subTest(case=testKey):
                dd = DottedDict(self.nestedDictDeep.copy())
                # Trigger __delitem__:
                with self.assertRaises(KeyError, msg='Invalid key should raise key error.'):
                    del dd[testKey]
                # Should now raise KeyError on get:
                with self.assertRaises(KeyError, msg='Accessing a deleted value should now raise KeyError.'):
                    dd[testKey]
                self.printLog(f'{f"del DottedDict[{testKey}]":<75}[PASS]')
        
        
    def test_contains_expected(self):
        self.printLog(f'{" Test Case: test_contains_expected ":=^100}')
        # Create test cases for valid keys:
        cases = [
            'simple', 'a.b', 'a.c', 'a.c.red', 'a.c.orange', 'a.c.blue',
            'a.deepest', 'a.deepest.level1.level2.level3.level4.level5',
            'simple', ' ', ',', ',.!'
        ]
        # Test cases:
        for testKey in cases:
            with self.subTest(case=testKey):
                dd = DottedDict(self.nestedDictDeep.copy())
                # Should no longer be in DottedDict:
                self.assertIn(testKey, dd, 'Key exists but contains returns False.')
                self.printLog(f'{f"del DottedDict[{testKey}]":<75}[PASS]')
    
    
    def test_contains_unexpected(self):
        self.printLog(f'{" Test Case: test_contains_unexpected ":=^100}')
        # Create test cases for nonexistent keys:
        cases = [
            'simplest', 'a.b.c', 'b.a.c', 'a.cat.red', 'a.c.cyan', 'simple.c.blue',
            'deepest', 'a.deepest.level1.level2.level5.level4.level5',
            'simple.1', 'a. ', 'b.,', ',.!.%'
        ]
        # Test cases:
        for testKey in cases:
            with self.subTest(case=testKey, group='nonexistent'):
                dd = DottedDict(self.nestedDictDeep.copy())
                self.assertNotIn(testKey, dd, 'Key does not exist but "in" returned True.')
                self.printLog(f'{f"{testKey} in DottedDict -> False":<75}[PASS]')
        
        # Create test cases for invalid keys:
        cases = [
            '', '.', '.a', 'a.', 'a.b.', 'a.c.orange.', 'a..deepest',
            '..a.deepest.level1.level2.level3.level4.level5..', 'simple..'
        ]
        # Test cases:
        for testKey in cases:
            with self.subTest(case=testKey, group='invalid'):
                dd = DottedDict(self.nestedDictDeep.copy())
                with self.assertRaises(KeyError, msg='Key is invalid but did not raise an error.'):
                    testKey in dd
                self.printLog(f'{f"{testKey} in DottedDict -> KeyError":<75}[PASS]')
        
        
    def test_copy(self):
        self.printLog(f'{" Test Case: test_copy ":=^100}')
        # Create original and copy:
        dOg = DottedDict(self.simpleDict)
        dCp = dOg.copy()
        self.printLog('Testing copy operation... ', end='')
        self.assertIsInstance(dCp, DottedDict, 'Copy should also be a DottedDict, but is not.')
        self.assertDictEqual(dOg, dCp, 'Copied DottedDict is not equal to original.')
        self.assertNotEqual(id(dOg), id(dCp), 'Copy should be new instance in memory but is not.')
        self.printLog('[PASS]')
        # Changing copy should not affect original
        self.printLog('Testing modification of copy... ', end='')
        dCp['test'] = [1, 2, 3]
        self.assertNotEqual(dOg, dCp, 'Original should not equal modified DottedDict.')
        self.assertNotIn('test', dOg, 'New key should not exist in original DottedDict.')
        self.printLog('[PASS]')
        
    
    def test_merge(self):
        self.printLog(f'{" Test Case: test_merge ":=^100}')
        # Create test cases; dictionaries to transform and try merging:
        cases = [
            ({chr(n) : n for n in range(97,123)}, {'test': True, 'deep': {'level1': {'level2': 'done'}, 'end': False}}),
            ({'test': True, 'deep': {'level1': {'level2': 'done'}, 'end': False}}, {'deep': {'level1': {'leaf': True}}}),
            ({chr(n) : n for n in range(97,123)}, {chr(n) : n for n in range(97,123)}),
            ({chr(n) : n for n in range(97,123)}, {'new': True}),
            ({'test': True, 'deep': {'level1': {'level2': 'done'}, 'end': False}}, {'deep': {'level1': {'level2': 'merged'}, 'end': 'merged'}})
        ]
        # Test cases:
        for dictDest, dictSrc in cases:
            with self.subTest(src=dictSrc, dst=dictDest):
                dd = DottedDict(dictDest)
                dd.merge(dictSrc)
                d = dict(dictDest)
                mergeNestedDicts(d, dictSrc)
                self.assertDictEqual(dd, d, 'Merged dictionary is not equal to merged DottedDicts.')
                self.printLog(f'[PASS] {f"{dd} = {d}":>90}')
    
        
    def test_empty(self):
        self.printLog(f'{" Test Case: test_empty ":=^100}')
        # Create test cases for multiple different values to get:
        validCases = [
            None, (), {}, set(), dict(), []
        ]
        # Test cases on valid empty constructor:
        for test in validCases:
            with self.subTest(case=test, group='valid'):
                dd = DottedDict(test)
                self.assertTrue(dd.empty())
                self.printLog(f'{f"DottedDict({test})":<50}[PASS]')
        
        # Test cases on invalid constructor, leaving instance empty:
        invalidCases = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            range(10),
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
            (0, 1, 2, 3, 4, 5)
        ]
        for test in invalidCases:
            with self.subTest(case=test, group='invalid'):
                with self.assertRaises(Exception, msg='Invalid init source did not raise an exception.'):
                    dd = DottedDict(test)
                    self.assertTrue(dd.empty())
                self.printLog(f'{f"DottedDict({test})":<50}[PASS]')
                
        # Test case on DottedDict that becomes empty:
        dd = DottedDict({'a': 1, 'b': 2, 'c': {'d': 4}})
        while len(dd) > 0: dd.popitem()
        self.assertTrue(dd.empty(), 'DottedDict should be empty.')
        self.printLog(f'{"DottedDict::popitem":<50}[PASS]')
        
        dd = DottedDict(self.simpleDict)
        dd.clear()
        self.assertTrue(dd.empty(), 'DottedDict::clear should empty the data structure.')
        self.printLog(f'{f"DottedDict::clear":<50}[PASS]')
        
    def test_dottedItems(self):
        self.printLog(f'{" Test Case: test_dottedItems ":=^100}')
        cases = [
            (self.simpleDict, [('a', 1), ('b', 2), ('c', 3), ('d', 4), ('red', True), ('blue', 50)]),
            (self.nestedDict, [('a.b', 2), ('test.1', 2), ('c', 3), ('blue', 'red')]),
            (self.nestedDictDeep, [('a.b', 2), ('a.c.red', False), ('a.c.orange', True), ('a.c.yellow', False), ('a.c.green', True), ('a.c.blue', True), ('a.c.purple', True), ('a.c.pink', True), ('a.deepest.level1.level2.level3.level4.level5', 'done'), ('simple', True), (' ', False), (',.!', '#')]),
        ]
        
        for test in cases:
            with self.subTest(case=cases.index(test)):
                dd = DottedDict(test[0])
                self.assertListEqual(dd.dottedItems(), test[1])
                self.printLog(f'{f"DottedDict::dottedItems() #{cases.index(test)}":<50}[PASS]')
                
    
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_init_empty'))
        test_suite.addTest(cls('test_init_good'))
        test_suite.addTest(cls('test_init_bad'))
        test_suite.addTest(cls('test_get_item_expected'))
        test_suite.addTest(cls('test_get_item_unexpected'))
        test_suite.addTest(cls('test_set_item_expected'))
        test_suite.addTest(cls('test_set_item_unexpected'))
        test_suite.addTest(cls('test_del_item_expected'))
        test_suite.addTest(cls('test_del_item_unexpected'))
        test_suite.addTest(cls('test_contains_expected'))
        test_suite.addTest(cls('test_contains_unexpected'))
        test_suite.addTest(cls('test_copy'))
        test_suite.addTest(cls('test_merge'))
        test_suite.addTest(cls('test_empty'))
        test_suite.addTest(cls('test_dottedItems'))
        return test_suite
    
class KuboUtilFuncsTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass(testLogOverwrite=False, online=False)
        
        # Set up some class variables to use later:
        Faker.seed(time())
        cls.fake = Faker()
        cls.fake.add_provider(internet)
        
    
    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()
    
    
    def test_getIP(self):
        self.printLog(f'{" Test Case: test_getIP ":=^100}')
        
        # Create an environment in the emulator:
        numHosts = 2
        emu = Makers.makeEmulatorBaseWith5StubASAndHosts(numHosts)
        emu.render()
        # Get IPs for nodes in each AS:
        for asn in range(150, 155):
            self.printLog(f'Testing nodes in AS {asn}:')
            curAS = emu.getLayer('Base').getAutonomousSystem(asn)
            # Get IP for each host in the current AS:
            for host in curAS.getHosts():
                node = curAS.getHost(host)
                ip = getIP(node)
                with self.subTest(device=host, ip=str(ip), type='host'):
                    self.assertIsNotNone(ip, 'No IP found.')
                    self.printLog(f'\t{host} -> {ip} [PASS]')
            # Get an IP for each router in the current AS:
            #   Note: this function is meant to be used on hosts with a single NIC;
            #         performing on a router will only get one NIC's IP.
            for router in curAS.getRouters():
                node = curAS.getRouter(router)
                ip = getIP(node)
                with self.subTest(device=router, ip=str(ip), type='router'):
                    self.assertIsNotNone(ip, 'No IP found.')
                    self.printLog(f'\t{router} -> {ip} [PASS]')
                
                
    def test_isIPv4(self):
        self.printLog(f'{" Test Case: test_isIPv4 ":=^100}')
        
        # Test with randomly-generated valid IPs:
        numTests = 10
        for i in range(numTests):
            ip = self.fake.ipv4()
            with self.subTest(ip=ip, group='valid'):
                self.assertTrue(isIPv4(ip))
                self.printLog(f'[PASS] isIPv4({ip}) -> True')
        
        # Test with invalid IPs:
        invalidIPs = [
            '255.255.255.256', '300.1.1.1', '55.288.155.0', '0.0.888.1',
            '55.55.55', '55.55', '55', '1.1.1.1.1'
        ]
        for ip in invalidIPs:
            with self.subTest(ip=ip, group='invalid'):
                self.assertFalse(isIPv4(ip))
                self.printLog(f'[PASS] isIPv4({ip}) -> False')
            
    
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_getIP'))
        test_suite.addTest(cls('test_isIPv4'))
        return test_suite
    
    
def mergeNestedDicts(dest:Mapping, src:Mapping):
    """Merge nested dictionaries.

    Parameters
    ----------
    dest : Mapping
        The dict-like object into which data will be merged.
    src : Mapping
        The dict-like object from which data will be merged (will not be altered).
    """
    for key, value in src.items():
        # If item being copied already exists and both values are dict-like, merge those:
        if key in dest and isinstance(value, Mapping) and isinstance(dest[key], Mapping):
                mergeNestedDicts(dest[key], value)
        # In any other case, just take the value from the source dict:
        else:
            dest[key] = value
    
if __name__ == '__main__':
    test_suite = ut.TestSuite()
    test_suite.addTests(DottedDictTestCase.get_test_suite())
    test_suite.addTests(KuboUtilFuncsTestCase.get_test_suite())
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    
    # Insert summary line in output for each:
    for testCase in [DottedDictTestCase, KuboUtilFuncsTestCase]:
        testCase.printLog(f'{" Test Results ":=^100}')
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        testCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))