#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu.core import (
    Scope,
    ScopeTier,
    ScopeType,
    BaseOption,
    OptionMode,
    Customizable,
)
from enum import Enum


class SEEDEmuOptionSystemTestCase(ut.TestCase):

    def test_scope(self):
        """!@brief tests proper inclusion/exclusion, intersection and union of Scopes"""
        cmpr =  Scope.collate

        self.assertTrue(
            Scope(ScopeTier.Global) > Scope(ScopeTier.AS, as_id=150),
            "global scope is superset of AS scopes",
        )
        self.assertTrue(
            Scope(ScopeTier.AS, as_id=150) < Scope(ScopeTier.Global),
            "AS scopes are subset of global scope",
        )

        self.assertTrue(
            cmpr(Scope(ScopeTier.AS, as_id=150), Scope(ScopeTier.AS, as_id=160)) == 0,
            "disjoint AS scopes",
        )
        self.assertTrue(
            cmpr(
                Scope(ScopeTier.Node, as_id=150, node_id="br0"),
                Scope(ScopeTier.Node, as_id=160, node_id="br0"),
            )
            == 0,
            "disjoint Nodes scopes different ASes",
        )
        self.assertTrue(
            cmpr(
                Scope(ScopeTier.Node, as_id=150, node_id="br0"),
                Scope(ScopeTier.Node, as_id=150, node_id="br1"),
            )
            == 0,
            "disjoint Nodes scopes same AS",
        )
        self.assertTrue(
            cmpr(
                Scope(ScopeTier.AS, as_id=150, node_type=ScopeType.HNODE),
                Scope(ScopeTier.AS, as_id=150, node_type=ScopeType.BRDNODE),
            )
            == 0,
            "disjoint Types scopes at AS level",
        )
        self.assertTrue(
            cmpr(
                Scope(ScopeTier.AS, as_id=150, node_type=ScopeType.HNODE),
                Scope(ScopeTier.AS, as_id=160, node_type=ScopeType.BRDNODE),
            )
            == 0,
            "disjoint Types as well as ASes",
        )
        self.assertTrue(
            cmpr(
                Scope(ScopeTier.Global, node_type=ScopeType.HNODE),
                Scope(ScopeTier.Global, node_type=ScopeType.BRDNODE),
            )
            == 0,
            "disjoint Types scopes at global level",
        )

        self.assertTrue ( Scope(ScopeTier.AS, as_id=150) >
                          Scope(ScopeTier.Node, as_id=150,
                                 node_id='brd0',
                                 node_type=ScopeType.BRDNODE),
                        'node scope is subset of AS scope')

        self.assertTrue( not ( Scope(ScopeTier.AS, as_id=150) <
                              Scope(ScopeTier.Node, as_id=150,
                                    node_id='brd0',
                                    node_type=ScopeType.BRDNODE)))

        self.assertTrue(
            not (
                Scope(ScopeTier.AS, as_id=150)
                < Scope(
                    ScopeTier.Node,
                    as_id=150,
                    node_id="brd0",
                    node_type=ScopeType.BRDNODE,
                )
            )
        )

        self.assertTrue(
            Scope(ScopeTier.AS, as_id=160) == Scope(ScopeTier.AS, as_id=160),
            "identical AS scope",
        )
        self.assertTrue(
            Scope(ScopeTier.AS, as_id=160, node_type=ScopeType.ANY)
            == Scope(ScopeTier.AS, as_id=160),
            "identical AS scope",
        )
        self.assertTrue(
            Scope(ScopeTier.AS, as_id=160, node_type=ScopeType.ANY)
            > Scope(ScopeTier.AS, as_id=160, node_type=ScopeType.BRDNODE),
            "ANY includes all types",
        )
        self.assertTrue(
            Scope(ScopeTier.AS, as_id=150) != Scope(ScopeTier.AS, as_id=160),
            "not identical scope",
        )
        self.assertTrue(
            Scope(ScopeTier.Node, as_id=150, node_id="brd0")
            == Scope(
                ScopeTier.Node, as_id=150, node_id="brd0", node_type=ScopeType.BRDNODE
            ),
            "same node but with extra type info",
        )
        self.assertTrue(
            Scope(ScopeTier.Global) > Scope(ScopeTier.Node, as_id=150, node_id="brd0")
        )
        self.assertTrue(
            not (
                Scope(ScopeTier.Global, ScopeType.HNODE)
                > Scope(
                    ScopeTier.Node,
                    as_id=150,
                    node_id="brd0",
                    node_type=ScopeType.BRDNODE,
                )
            ),
            "node unaffected by global type",
        )

    def test_customizable(self):
        """!@brief test setting and retrieval of associated options"""

        class _Option(BaseOption, Enum):
            """!@brief dummy option impl"""

            ROTATE_LOGS = "rotate_logs"
            USE_ENVSUBST = "use_envsubst"
            EXPERIMENTAL_SCMP = "experimental_scmp"
            DISABLE_BFD = "disable_bfd"
            LOGLEVEL = "loglevel"
            SERVE_METRICS = "serve_metrics"
            APPROPRIATE_DIGEST = "appropriate_digest"
            MAX_BANDWIDTH = "max_bandwidth"

            def __init__(self, key, value=None):
                self._key = key
                # if value==None:
                #    value = self.defaultValue()
                self._mutable_value = value  # Separate mutable storage
                self._mutable_mode = OptionMode.BUILD_TIME

            @property
            def name(self) -> str:
                return self._key

            @property
            def value(self) -> str:
                return (
                    self._mutable_value
                    if self._mutable_value
                    else str(self.defaultValue()).lower()
                )

            @value.setter
            def value(self, new_value: str):
                """Allow updating the value attribute."""
                self._mutable_value = new_value

            @property
            def mode(self):
                return self._mutable_mode

            @mode.setter
            def mode(self, new_mode):
                self._mutable_mode = new_mode

            def supportedModes(self) -> OptionMode:
                return OptionMode.BUILD_TIME

            def defaultValue(self):
                match self._name_:
                    case "ROTATE_LOGS":
                        return False
                    case "APPROPRIATE_DIGEST":
                        return True
                    case "DISABLE_BFD":
                        return True
                    case "EXPERIMENTAL_SCMP":
                        return False
                    case "LOGLEVEL":
                        return "error"
                    case "SERVE_METRICS":
                        return False
                    case "USE_ENVSUBST":
                        return False
                    case "MAX_BANDWIDTH":
                        return -1

            @classmethod
            def custom(cls, key, value, mode=None):
                valid_keys = set()
                for member in cls:
                    if isinstance(member.name, str):
                        valid_keys.add(member.name)
                if key not in valid_keys:
                    raise ValueError(
                        f"Invalid Option: {key}. Must be one of {valid_keys}."
                    )

                custom_option = object.__new__(cls)
                custom_option._key = key
                custom_option._mutable_value = value
                custom_option._name_ = key.upper()
                custom_option._mode = mode if mode else OptionMode.BUILD_TIME
                return custom_option

            def __repr__(self):
                return f"Option(key={self._key}, value={self._mutable_value})"

        # ----------------------------------------------------------------------
        config = Customizable()

        # Define scopes
        global_scope = Scope(ScopeTier.Global)
        global_router_scope = Scope(ScopeTier.Global, ScopeType.RNODE)
        as_router_scope = Scope(ScopeTier.AS, ScopeType.RNODE, as_id=42)
        node_scope = Scope(ScopeTier.Node, ScopeType.RNODE, node_id="A", as_id=42)

        config.setOption(_Option.custom("max_bandwidth", 100), global_scope)
        config.setOption(_Option.custom("max_bandwidth", 200), global_router_scope)
        config.setOption(_Option.custom("max_bandwidth", 400), as_router_scope)
        config.setOption(_Option.custom("max_bandwidth", 500), node_scope)

        # Retrieve values using a Scope object
        self.assertTrue(
            (
                opt := config.getOption(
                    "max_bandwidth",
                    Scope(ScopeTier.Node, ScopeType.RNODE, node_id="A", as_id=42),
                )
            )
            != None
            and opt.value == 500
        )  # 500 (Node-specific)
        self.assertTrue(
            (
                opt := config.getOption(
                    "max_bandwidth",
                    Scope(ScopeTier.Node, ScopeType.HNODE, node_id="C", as_id=42),
                )
            )
            != None
            and opt.value == 100
        )  # 100 (Global fallback)
        self.assertTrue(
            (
                opt := config.getOption(
                    "max_bandwidth",
                    Scope(ScopeTier.Node, ScopeType.RNODE, node_id="D", as_id=99),
                )
            )
            != None
            and opt.value == 200
        )  # 200 (Global & Type)
        self.assertTrue(
            (
                opt := config.getOption(
                    "max_bandwidth",
                    Scope(ScopeTier.Node, ScopeType.HNODE, node_id="E", as_id=99),
                )
            )
            != None
            and opt.value == 100
        )  # 100 (Global-wide)
        self.assertTrue(
            (
                opt := config.getOption(
                    "max_bandwidth",
                    Scope(ScopeTier.Node, ScopeType.RNODE, node_id="B", as_id=42),
                )
            )
            != None
            and opt.value == 400
        )  # 400 (AS & Type)

        child_config = Customizable()
        child_config._scope = node_scope
        self.assertTrue(not child_config.getOption("max_bandwidth"))
        config.handDown(child_config)
        self.assertTrue(
            (opt := child_config.getOption("max_bandwidth")) != None
            and opt.value == 500
        )

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(SEEDEmuOptionSystemTestCase('test_scope'))
        test_suite.addTest(SEEDEmuOptionSystemTestCase('test_customizable'))

        return test_suite


if __name__ == "__main__":
    test_suite = SEEDEmuOptionSystemTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    print(
        "score: %d of %d (%d errors, %d failures)"
        % (num - (errs + fails), num, errs, fails)
    )
