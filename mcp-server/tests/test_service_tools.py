import unittest
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    create_as, create_node, install_service, render_simulation, get_node_info
)
from runtime import runtime

class TestServiceTools(unittest.TestCase):
    def setUp(self):
        # Reset runtime before each test
        runtime.reset()

    def test_install_webservice(self):
        create_as(100)
        create_node("web1", 100, "host")
        
        # Connect node to network to ensure it has IP
        base = runtime.get_base()
        as100 = base.getAutonomousSystem(100)
        as100.createNetwork('net0')
        as100.getHost('web1').joinNetwork('net0')
        
        # Install WebService
        params = json.dumps({
            "url": "www.example.com",
            "index_html": "<h1>Test</h1>"
        })
        
        result = install_service("web1", "WebService", params)
        self.assertIn("Installed WebService on web1", result)

    def test_install_dns(self):
        create_as(100)
        create_node("dns1", 100, "host")
        create_node("web1", 100, "host") # Target
        
        # Connect nodes
        base = runtime.get_base()
        as100 = base.getAutonomousSystem(100)
        as100.createNetwork('net0')
        as100.getHost('dns1').joinNetwork('net0')
        as100.getHost('web1').joinNetwork('net0')
        
        params = json.dumps({
            "zones": [
                {
                    "name": "example.com",
                    "records": [
                        {"name": "www", "type": "A", "value": "web1"}
                    ]
                }
            ]
        })
        
        result = install_service("dns1", "DomainNameService", params)
        self.assertIn("Installed DomainNameService on dns1", result)

    def test_render_simulation(self):
        create_as(100)
        create_node("r1", 100, "router")
        
        result = render_simulation()
        self.assertIn("Simulation rendered successfully", result)
        self.assertTrue(runtime.get_emulator().rendered())

if __name__ == '__main__':
    unittest.main()
