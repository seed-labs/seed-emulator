import json
from typing import List, Tuple, Union

from tests.SeedEmuTestCase import SeedEmuTestCase


class ScionTestCase(SeedEmuTestCase):
    """!
    @brief Extends SeedEmuTestCase with SCION-specific tests.
    """
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

    def scion_ping_test(self, container, dst: str, count: int = 1, pred: str = "0*") -> bool:
        """!
        @brief Ping a SCION host three times.

        @param container Container of the source host
        @param dst Destination host in ISD-ASN,IP format
        @param count Number of echo requests to send
        @param pred Space separated list of hop predicates (see 'scion ping --help')

        @return True if ping was successful, False if destination did not respond
        or no working paths match the predicate.
        """

        exit_code, _ = container.exec_run(f"scion ping {dst} -c {count} --sequence='{pred}'")
        self.printLog(f"CMD: scion ping {dst} -c {count} --sequence='{pred}'")
        if exit_code == 0:
            self.printLog(f"scion ping test {dst} succeeded")
            return True
        else:
            self.printLog(f"scion ping test {dst} failed")
            return False

    def scion_path_test(self, container, dst: str, pred: str = "0*", ret_paths: bool = False
                        ) -> Union[bool, Tuple[bool, List]]:
        """!
        @brief Test whether a path matching the given path predicate exists and is alive.

        @param container Container of the source host
        @param dst Destination host in ISD-ASN,IP format
        @param pred Space separated list of hop predicates (see 'scion showpaths --help')
        @param ret_paths If true, return the paths found by the showpaths command.

        @return True if at least one path matching the hop predicates is alive or source and
        destination are identical. If \p ret_paths is True, returns a pair of the pass/fail
        condition and a list of the available paths.
        """

        exit_code, output = container.exec_run(
            f"scion showpaths {dst} --format json --sequence='{pred}'")
        assert 0 <= exit_code < 2, "got unexpected exit code from 'scion showpaths'"
        
        self.printLog(f"CMD: scion showpaths {dst} --format json --sequence='{pred}'")
        paths = json.loads(output).get('paths', [])

        if exit_code == 0:
            self.printLog(f"found {len(paths)} path(s) to {dst} matching predicate '{pred}'")
            return True, paths if ret_paths else True
        else:
            self.printLog(f"scion path test (dst: {dst}) with predicate '{pred}' failed")
            return False, paths if ret_paths else False
