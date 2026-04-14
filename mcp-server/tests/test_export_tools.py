import unittest
import sys
import os
import json
import tempfile

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    create_as, create_node, connect_nodes,
    get_topology_summary, export_topology, export_python_script
)
from runtime import runtime

class TestExportTools(unittest.TestCase):
    def setUp(self):
        runtime.reset()
        
    def test_get_topology_summary_json_structure(self):
        """get_topology_summary should return valid JSON with expected keys"""
        create_as(100)
        create_node("r1", 100, "router")
        
        result = get_topology_summary()
        data = json.loads(result)
        
        self.assertIn("autonomous_systems", data)
        self.assertIn("internet_exchanges", data)
        self.assertIn("total_routers", data)
        self.assertEqual(data["total_routers"], 1)
        
    def test_export_topology_json(self):
        """export_topology with format='json' should match get_topology_summary"""
        create_as(100)
        
        result_json = export_topology("json")
        result_summary = get_topology_summary()
        
        self.assertEqual(result_json, result_summary)
        
    def test_export_topology_mermaid(self):
        """export_topology with format='mermaid' should return graph definition"""
        create_as(100)
        create_node("r1", 100, "router")
        
        result = export_topology("mermaid")
        
        self.assertIn("graph LR", result)
        self.assertIn("subgraph AS100", result)
        self.assertIn("r1[(", result) # Check router Node syntax in mermaid
        
    def test_export_topology_graphviz(self):
        """export_topology with format='graphviz' should return DOT definition"""
        create_as(100)
        create_node("h1", 100, "host")
        
        result = export_topology("graphviz")
        
        self.assertIn("digraph Topology", result)
        self.assertIn("subgraph cluster_AS100", result)
        self.assertIn("h1 [shape=box]", result) # Check host Node shape
        
    def test_export_topology_invalid_format(self):
        """export_topology should handle unknown formats gracefully"""
        result = export_topology("xml")
        self.assertIn("Error: Unknown format", result)
        
    def test_export_python_script_content(self):
        """export_python_script should return script content with logged calls"""
        create_as(150)
        create_node("router1", 150, "router")
        
        script = export_python_script()
        
        self.assertIn("from seedemu.core import Emulator", script)
        self.assertIn("createAutonomousSystem(150)", script)
        self.assertIn("createRouter('router1')", script)
        
    def test_export_python_script_file(self):
        """export_python_script should save to file if path provided"""
        create_as(150)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            result = export_python_script(tmp_path)
            self.assertIn(f"Python script saved to {tmp_path}", result)
            
            with open(tmp_path, 'r') as f:
                content = f.read()
                self.assertIn("createAutonomousSystem(150)", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
