import os
import sys
import tempfile
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.store import SeedOpsStore
from seedops.workspaces import WorkspaceManager, extract_container_names_from_compose, resolve_compose_output_dir


class TestSeedOpsAttachCompose(unittest.TestCase):
    def test_extract_container_names(self):
        mcp_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(mcp_server_dir, "output_e2e_demo")

        names = extract_container_names_from_compose(output_dir)
        self.assertTrue(len(names) > 0)
        self.assertTrue(any("as150" in n for n in names))

    def test_resolve_compose_output_dir_supports_repo_root_relative_path(self):
        mcp_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo_root = os.path.dirname(mcp_server_dir)
        current = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            try:
                os.chdir(td)
                resolved = resolve_compose_output_dir("mcp-server/output_e2e_demo")
            finally:
                os.chdir(current)

        self.assertEqual(resolved, os.path.join(repo_root, "mcp-server", "output_e2e_demo"))

    def test_attach_compose_normalizes_repo_root_relative_path(self):
        mcp_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo_root = os.path.dirname(mcp_server_dir)
        current = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            manager = WorkspaceManager(store=store)
            ws = manager.create("attach-demo")
            manager.refresh = lambda workspace_id, redacted=False: {"workspace_id": workspace_id}  # type: ignore[method-assign]

            try:
                os.chdir(td)
                result = manager.attach_compose(ws.workspace_id, "mcp-server/output_e2e_demo")
            finally:
                os.chdir(current)

            self.assertEqual(result["workspace_id"], ws.workspace_id)
            attached = manager.get(ws.workspace_id)
            assert attached is not None
            self.assertEqual(
                attached.attach_config.get("output_dir"),
                os.path.join(repo_root, "mcp-server", "output_e2e_demo"),
            )


if __name__ == "__main__":
    unittest.main()
