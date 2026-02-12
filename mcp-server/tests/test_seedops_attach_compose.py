import os
import sys
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.workspaces import extract_container_names_from_compose


class TestSeedOpsAttachCompose(unittest.TestCase):
    def test_extract_container_names(self):
        mcp_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(mcp_server_dir, "output_e2e_demo")

        names = extract_container_names_from_compose(output_dir)
        self.assertTrue(len(names) > 0)
        self.assertTrue(any("as150" in n for n in names))


if __name__ == "__main__":
    unittest.main()

