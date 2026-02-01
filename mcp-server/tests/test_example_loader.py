"""Tests for Example Loader and Agent State tools (Phase 10-11)."""

import unittest
import json
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime import runtime, AgentPhase


class TestAgentPhase(unittest.TestCase):
    """Test AgentPhase state machine."""

    def setUp(self):
        runtime.reset()

    def test_initial_phase_is_idle(self):
        """Test that initial phase is IDLE."""
        self.assertEqual(runtime.get_phase(), AgentPhase.IDLE)

    def test_set_phase(self):
        """Test setting phase."""
        runtime.set_phase(AgentPhase.DESIGNING)
        self.assertEqual(runtime.get_phase(), AgentPhase.DESIGNING)
        
        runtime.set_phase(AgentPhase.RUNNING)
        self.assertEqual(runtime.get_phase(), AgentPhase.RUNNING)

    def test_examples_dir_exists(self):
        """Test examples directory is set correctly."""
        self.assertTrue(os.path.exists(runtime.examples_dir))
        self.assertIn('examples', runtime.examples_dir)


class TestListExamples(unittest.TestCase):
    """Test list_examples tool."""

    def setUp(self):
        runtime.reset()

    def test_list_all_examples(self):
        """Test listing all examples."""
        from server import list_examples
        result = list_examples()
        data = json.loads(result)
        
        # Should have at least basic category
        self.assertIn('basic', data)
        
        # basic should have A00_simple_as
        basic_names = [e['name'] for e in data['basic']]
        self.assertIn('A00_simple_as', basic_names)

    def test_list_examples_by_category(self):
        """Test filtering by category."""
        from server import list_examples
        result = list_examples(category="internet")
        data = json.loads(result)
        
        # Should only have internet category
        self.assertIn('internet', data)
        self.assertNotIn('basic', data)

    def test_list_examples_invalid_category(self):
        """Test invalid category returns empty."""
        from server import list_examples
        result = list_examples(category="nonexistent")
        data = json.loads(result)
        
        self.assertEqual(data, {})


class TestGetAgentState(unittest.TestCase):
    """Test get_agent_state tool."""

    def setUp(self):
        runtime.reset()

    def test_get_initial_state(self):
        """Test getting initial agent state."""
        from server import get_agent_state
        result = get_agent_state()
        data = json.loads(result)
        
        self.assertEqual(data['phase'], 'idle')
        self.assertIsNone(data['current_example'])
        self.assertFalse(data['is_rendered'])
        self.assertIn('topology', data)

    def test_state_reflects_phase_change(self):
        """Test state reflects phase changes."""
        from server import get_agent_state
        
        runtime.set_phase(AgentPhase.DESIGNING)
        runtime.current_example = "basic/A00_simple_as"
        
        result = get_agent_state()
        data = json.loads(result)
        
        self.assertEqual(data['phase'], 'designing')
        self.assertEqual(data['current_example'], 'basic/A00_simple_as')


class TestDiscoverSimulation(unittest.TestCase):
    """Test discover_running_simulation tool."""

    def test_discover_no_simulation(self):
        """Test discovering when no simulation is running."""
        from server import discover_running_simulation
        result = discover_running_simulation()
        data = json.loads(result)
        
        # Either found is False or there are containers (if other tests left some)
        self.assertIn('found', data)


if __name__ == '__main__':
    unittest.main()
