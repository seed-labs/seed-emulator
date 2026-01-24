import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    create_as, create_ix, create_node, connect_nodes, connect_to_ix,
    enable_routing_layers, configure_direct_peering, configure_ix_peering
)
from runtime import runtime

class TestRoutingTools(unittest.TestCase):
    def setUp(self):
        # Reset runtime before each test
        runtime.reset()

    def test_enable_routing(self):
        result = enable_routing_layers(['routing', 'ospf'])
        self.assertIn('Routing', result)
        self.assertIn('Ospf', result)
        
        # Check emulator has layers
        emu = runtime.get_emulator()
        layers = [l.getName() for l in emu.getLayers()]
        self.assertIn('Routing', layers)
        self.assertIn('Ospf', layers)

    def test_configure_cross_connect_peering(self):
        create_as(100)
        create_as(200)
        create_node("r100", 100, "router")
        create_node("r200", 200, "router")
        
        # Create physical link
        connect_nodes("r100", "r200")
        
        # Enable layers
        enable_routing_layers(['routing', 'ebgp'])
        
        # Configure BGP
        result = configure_direct_peering(100, 200, 'peer')
        self.assertIn("Cross-Connect", result)
        self.assertIn("AS 100", result)
        self.assertIn("AS 200", result)

    def test_configure_ix_peering(self):
        create_as(300)
        create_as(400)
        create_ix(10, 'ix10')
        create_node("r300", 300, "router")
        create_node("r400", 400, "router")
        
        # Connect to IX using new tool
        connect_to_ix("r300", 10)
        connect_to_ix("r400", 10)
        
        # Enable layers
        enable_routing_layers(['routing', 'ebgp'])
        
        # Configure BGP
        result = configure_ix_peering(10, 300, 400, 'peer')
        self.assertIn("Private Peering at IX 10", result)

if __name__ == '__main__':
    unittest.main()
