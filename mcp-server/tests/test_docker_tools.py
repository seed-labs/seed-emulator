import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    compile_simulation, build_images, start_simulation, 
    stop_simulation, list_containers, create_as, create_node,
    enable_routing_layers, render_simulation, attach_to_simulation
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
        self.assertIn("Error: No current compiled output", result)
    
    @patch('subprocess.run')
    def test_build_success(self, mock_run):
        """build_images should call docker compose build"""
        runtime.mark_rendered()
        runtime.mark_compiled("/tmp/test_output")
        mock_run.return_value = MagicMock(returncode=0)
        
        result = build_images()
        self.assertIn("built successfully", result)
        self.assertTrue(runtime.is_build_current())
        # Check that the build command was called (version check may also be called)
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("build" in c for c in calls))
        
    @patch('subprocess.run')
    def test_start_simulation(self, mock_run):
        """start_simulation should call docker compose up"""
        runtime.mark_rendered()
        runtime.mark_compiled("/tmp/test_output")
        runtime.mark_built()
        mock_run.return_value = MagicMock(returncode=0)
        
        result = start_simulation()
        self.assertIn("started", result)
        self.assertEqual(runtime.get_phase().value, "running")
        # Check that the up command was called
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("up" in c for c in calls))
        
    @patch('subprocess.run')
    def test_stop_simulation(self, mock_run):
        """stop_simulation should call docker compose down"""
        runtime.mark_rendered()
        runtime.mark_compiled("/tmp/test_output")
        mock_run.return_value = MagicMock(returncode=0)
        
        result = stop_simulation()
        self.assertIn("stopped", result)
        # Check that the down command was called
        calls = [str(c) for c in mock_run.call_args_list]
        self.assertTrue(any("down" in c for c in calls))

    def test_topology_mutation_invalidates_compiled_state(self):
        create_as(100)
        create_node("r1", 100, "router")
        runtime.mark_rendered()
        runtime.mark_compiled("/tmp/test_output")
        runtime.mark_built()

        self.assertTrue(runtime.is_compile_current())
        self.assertTrue(runtime.is_build_current())

        create_node("h1", 100, "host")
        self.assertFalse(runtime.is_render_current())
        self.assertFalse(runtime.is_compile_current())
        self.assertFalse(runtime.is_build_current())
        self.assertEqual(runtime.lifecycle_contract()["phase"], "designing")

    def test_attach_updates_lifecycle_contract(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            compose = Path(td) / "docker-compose.yml"
            compose.write_text("services: {}\n", encoding="utf-8")
            result = attach_to_simulation(td)
            self.assertIn('"attached": true', result.lower())
            lifecycle = runtime.lifecycle_contract()
            self.assertTrue(lifecycle["attached"])
            self.assertIn("workspace_refresh", lifecycle["next_actions"])
            self.assertEqual(lifecycle["attached_output_dir"], td)

if __name__ == '__main__':
    unittest.main()
