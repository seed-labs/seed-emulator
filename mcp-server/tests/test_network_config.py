import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    create_as, create_node, connect_nodes, render_simulation, enable_routing_layers,
    configure_link_properties, add_static_route, get_node_interfaces
)
from runtime import runtime


class TestNetworkConfigTools(unittest.TestCase):
    """Tests for network configuration tools.
    
    Note: SEED Emulator uses lazy interface creation. Interfaces are only created
    during the render() phase, so configure_link_properties and get_node_interfaces
    require render() to be called first for full functionality.
    """
    
    def setUp(self):
        runtime.reset()

    def test_configure_link_properties_node_not_found(self):
        """configure_link_properties should error for unknown node"""
        result = configure_link_properties("nonexistent", 0)
        self.assertIn("not found", result)
        
    def test_configure_link_properties_no_interfaces_pre_render(self):
        """configure_link_properties should handle node without interfaces (pre-render)"""
        create_as(100)
        create_node("r1", 100, "router")
        # Pre-render, node has no interfaces - this is expected
        result = configure_link_properties("r1", 0)
        self.assertIn("out of range", result)

    def test_add_static_route_node_not_found(self):
        """add_static_route should error for unknown node"""
        result = add_static_route("nonexistent", "10.0.0.0/8", "10.1.0.1")
        self.assertIn("not found", result)
        
    def test_add_static_route_success(self):
        """add_static_route should add route to node"""
        create_as(100)
        create_node("h1", 100, "host")
        
        result = add_static_route("h1", "0.0.0.0/0", "10.100.0.254")
        self.assertIn("0.0.0.0/0", result)
        self.assertIn("10.100.0.254", result)
        
    def test_get_node_interfaces_not_found(self):
        """get_node_interfaces should error for unknown node"""
        result = get_node_interfaces("nonexistent")
        self.assertIn("not found", result)
        
    def test_get_node_interfaces_empty_pre_render(self):
        """get_node_interfaces should return empty for node before render"""
        create_as(100)
        create_node("r1", 100, "router")
        
        # Pre-render: no interfaces yet
        result = get_node_interfaces("r1")
        self.assertIn("[]", result)  # Empty JSON array


if __name__ == '__main__':
    unittest.main()

