import unittest
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import create_as, create_ix, create_node, connect_nodes, get_topology_summary
from runtime import runtime

class TestInfraTools(unittest.TestCase):
    def setUp(self):
        # Reset runtime before each test
        runtime.reset()

    def test_create_as(self):
        result = create_as(100)
        self.assertIn("Created AS 100", result)
        
        base = runtime.get_base()
        self.assertIn(100, base.getAsns())
        
        # Test duplicate
        result = create_as(100)
        self.assertIn("already exists", result)

    def test_create_ix(self):
        result = create_ix(10, "ix10")
        self.assertIn("Created IX ix10", result)
        
        base = runtime.get_base()
        self.assertIn(10, base.getInternetExchangeIds())

    def test_create_node(self):
        create_as(200)
        
        # Test creating router
        result = create_node("router1", 200, "router")
        self.assertIn("Created router 'router1' in AS 200", result)
        
        # Test creating host
        result = create_node("host1", 200, "host")
        self.assertIn("Created host 'host1' in AS 200", result)
        
        base = runtime.get_base()
        as200 = base.getAutonomousSystem(200)
        self.assertIn("router1", as200.getRouters())
        self.assertIn("host1", as200.getHosts())

        # Test invalid AS
        result = create_node("router2", 999, "router")
        self.assertIn("AS 999 does not exist", result)

    def test_connect_nodes(self):
        create_as(300)
        create_node("r1", 300, "router")
        create_node("h1", 300, "host")
        
        result = connect_nodes("r1", "h1")
        self.assertIn("Connected r1 and h1", result)
        
        # Verify topology summary reflects this
        summary_json = get_topology_summary()
        summary = json.loads(summary_json)
        # We can't easily check links in summary yet as it only shows lists
        # But we can check that no exception occurred

    def test_cross_as_connection(self):
        create_as(400)
        create_as(500)
        create_node("r400", 400, "router")
        create_node("r500", 500, "router")
        
        result = connect_nodes("r400", "r500")
        self.assertIn("Cross-connected r400 (AS 400) and r500 (AS 500)", result)

if __name__ == '__main__':
    unittest.main()
