import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    compile_simulation, build_images, start_simulation, 
    stop_simulation, list_containers, create_as, create_node,
    enable_routing_layers, render_simulation
)
from runtime import runtime

class TestDockerTools(unittest.TestCase):
    def setUp(self):
        runtime.reset()

    def test_compile_requires_render(self):
        """compile_simulation should fail if not rendered"""
        result = compile_simulation("./test_output")
        self.assertIn("Error: Simulation not rendered", result)
    
    def test_compile_success(self):
        """compile_simulation should work after render"""
        import tempfile
        
        # Create AS and router
        create_as(100)
        create_node("r1", 100, "router")
        
        # Router needs interfaces - create a network and connect it
        base = runtime.get_base()
        asn = base.getAutonomousSystem(100)
        net = asn.createNetwork("net0")
        router = asn.getRouter("r1")
        router.joinNetwork("net0")
        
        enable_routing_layers(['routing'])
        
        render_result = render_simulation()
        # Render should succeed now
        self.assertIn("successfully", render_result.lower())
        self.assertTrue(runtime.get_emulator().rendered())
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = compile_simulation(tmpdir)
            # Just check it doesn't error on render check
            self.assertNotIn("Error: Simulation not rendered", result)

    def test_build_requires_compile(self):
        """build_images should fail if not compiled"""
        result = build_images()
        self.assertIn("Error: No output directory set", result)
    
    @patch('subprocess.run')
    def test_build_success(self, mock_run):
        """build_images should call docker compose build"""
        runtime.output_dir = "/tmp/test_output"
        mock_run.return_value = MagicMock(returncode=0)
        
        result = build_images()
        self.assertIn("built successfully", result)
        # Check that the build command was called (version check may also be called)
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("build" in c for c in calls))
        
    @patch('subprocess.run')
    def test_start_simulation(self, mock_run):
        """start_simulation should call docker compose up"""
        runtime.output_dir = "/tmp/test_output"
        mock_run.return_value = MagicMock(returncode=0)
        
        result = start_simulation()
        self.assertIn("started", result)
        # Check that the up command was called
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("up" in c for c in calls))
        
    @patch('subprocess.run')
    def test_stop_simulation(self, mock_run):
        """stop_simulation should call docker compose down"""
        runtime.output_dir = "/tmp/test_output"
        mock_run.return_value = MagicMock(returncode=0)
        
        result = stop_simulation()
        self.assertIn("stopped", result)
        # Check that the down command was called
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("down" in c for c in calls))

if __name__ == '__main__':
    unittest.main()
