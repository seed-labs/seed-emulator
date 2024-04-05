#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu.services.KuboService.KuboUtils import *
from test import SeedEmuTestCase

class DottedDictTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass(testLogOverwrite=True, online=False)
        
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
                        self.assertEqual(type(ddErr), type(dErr))
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
                self.assertEqual(dd[testKey], expectedVal)
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
                with self.assertRaises(KeyError):
                    dd[testKey]
                self.assertDictEqual(dd, self.nestedDictDeep)
                self.printLog(f'{f"DottedDict[{testKey}] -> KeyError":<70}[PASS]')
                
                
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
                self.assertEqual(dd[testKey], expectedVal)
                self.printLog(f'{f"DottedDict[{testKey}] = {dd[testKey]}":<120}[PASS]')
                
        # Extra test case:
        dd = DottedDict(self.nestedDictDeep)
        dd['a.deepest.level1.newLeaf'] = True
        self.assertEqual(dd['a.deepest.level1.level2.level3.level4.level5'], 'done')
        self.assertEqual(dd['a.deepest.level1.newLeaf'], True)
        
        
    def test_set_item_unexpected(self):
        self.printLog(f'{" Test Case: test_get_item_unexpected ":=^100}')
        # Create test cases for multiple different values to get:
        cases = ['', '.', '.a', 'a.', 'a.b.', 'a..b..c', 'a.c.orange.',
                 'a..deepest', '..a.deepest.level1.level2.level3.level4.level5..', 'simple..'
        ]
        # Test cases:
        dd = DottedDict(self.nestedDictDeep)
        for testKey in cases:
            with self.subTest(case=testKey):
                with self.assertRaises(KeyError):
                    dd[testKey] = 'test 1 2 3'
                self.printLog(f'{f"DottedDict[{testKey}] -> KeyError":<70}[PASS]')
                
    
    def test_del_item_expected(self):
        ...
        
    
    def test_del_item_unexpected(self):
        ...
        
        
    def test_contains_expected(self):
        ...
    
    
    def test_contains_unexpected(self):
        ...
        
        
    def test_copy(self):
        ...
        
    
    def test_merge(self):
        ...
        
        
    def test_empty(self):
        ...
                
    
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
        return test_suite
    
class UtilsTestCase(ut.TestCase):
    ...
    
    
if __name__ == '__main__':
    test_suite = ut.TestSuite()
    test_suite.addTests(DottedDictTestCase.get_test_suite())
    # test_suite.addTests(UtilsTestCase.get_test_suite())
    res = ut.TextTestRunner(verbosity=2).run(test_suite)
    
    DottedDictTestCase.printLog(f'{" Test Results ":=^100}')
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    DottedDictTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))