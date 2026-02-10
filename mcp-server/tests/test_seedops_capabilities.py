import asyncio
import json
import os
import sys
import tempfile
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from seedops import SeedOpsServices, register_tools


class TestSeedOpsCapabilities(unittest.TestCase):
    def test_seedops_capabilities_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_db = os.environ.get("SEEDOPS_DB_PATH")
            prev_data = os.environ.get("SEEDOPS_DATA_DIR")
            try:
                os.environ["SEEDOPS_DB_PATH"] = os.path.join(tmpdir, "seedops.db")
                os.environ["SEEDOPS_DATA_DIR"] = os.path.join(tmpdir, "data")

                mcp = FastMCP("seedops-capabilities-test")
                services = SeedOpsServices()
                register_tools(mcp, services=services)

                async def call_tool() -> dict:
                    result = await mcp.call_tool("seedops_capabilities", arguments={})
                    text = ""
                    if isinstance(result, tuple):
                        content_blocks = result[0] if result else []
                        if isinstance(content_blocks, list):
                            text_parts = [x.text for x in content_blocks if getattr(x, "type", "") == "text"]
                            text = "\n".join(text_parts)
                        if not text and len(result) > 1 and isinstance(result[1], dict):
                            text = str(result[1].get("result") or "")
                    return json.loads(text)

                payload = asyncio.run(call_tool())
                self.assertEqual(payload["playbook_version"], 1)
                self.assertIn("routing_bgp_summary", payload["supported_actions"])
                self.assertIn("seedops_capabilities", payload["tool_names"])
                self.assertIn("default_limits", payload)
                self.assertEqual(payload["default_limits"]["parallelism"], 20)
                services.store.close()
            finally:
                if prev_db is None:
                    os.environ.pop("SEEDOPS_DB_PATH", None)
                else:
                    os.environ["SEEDOPS_DB_PATH"] = prev_db
                if prev_data is None:
                    os.environ.pop("SEEDOPS_DATA_DIR", None)
                else:
                    os.environ["SEEDOPS_DATA_DIR"] = prev_data


if __name__ == "__main__":
    unittest.main()
