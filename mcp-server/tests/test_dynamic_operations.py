"""Tests for Dynamic Operations tools (Phase 13)."""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime import runtime


class TestInjectFault(unittest.TestCase):
    """Test inject_fault tool."""

    @patch('server.exec_command')
    def test_inject_packet_loss(self, mock_exec):
        """Test packet loss injection."""
        from server import inject_fault
        mock_exec.return_value = "Exit code: 0\n"
        
        result = inject_fault("test_container", "packet_loss", "20")
        
        self.assertIn("20%", result)
        self.assertIn("packet loss", result)
        mock_exec.assert_called_once()

    @patch('server.exec_command')
    def test_inject_latency(self, mock_exec):
        """Test latency injection."""
        from server import inject_fault
        mock_exec.return_value = "Exit code: 0\n"
        
        result = inject_fault("test_container", "latency", "100")
        
        self.assertIn("100ms", result)
        self.assertIn("latency", result)

    @patch('server.exec_command')
    def test_inject_kill_process(self, mock_exec):
        """Test kill process injection."""
        from server import inject_fault
        mock_exec.return_value = "Exit code: 0\n"
        
        result = inject_fault("test_container", "kill_process", "bird")
        
        self.assertIn("bird", result)
        self.assertIn("Killed", result)

    def test_inject_unknown_fault(self):
        """Test unknown fault type returns error."""
        from server import inject_fault
        
        result = inject_fault("test_container", "unknown_fault")
        
        self.assertIn("Error", result)
        self.assertIn("Unknown fault type", result)


class TestStartAttackScenario(unittest.TestCase):
    """Test start_attack_scenario tool."""

    @patch('server.bgp_announce_prefix')
    def test_bgp_hijack_scenario(self, mock_announce):
        """Test BGP hijack scenario."""
        from server import start_attack_scenario
        mock_announce.return_value = "Announced prefix 10.0.0.0/24"
        
        result = start_attack_scenario("bgp_hijack", "attacker", "10.0.0.0/24")
        
        self.assertIn("BGP Hijack", result)
        mock_announce.assert_called_once_with("attacker", "10.0.0.0/24")

    @patch('server.exec_command')
    def test_dos_flood_scenario(self, mock_exec):
        """Test DoS flood scenario."""
        from server import start_attack_scenario
        mock_exec.return_value = "Exit code: 0\n100 packets transmitted"
        
        result = start_attack_scenario("dos_flood", "attacker", "10.0.0.1", "50")
        
        self.assertIn("DoS flood", result)
        self.assertIn("50 packets", result)

    def test_unknown_scenario(self):
        """Test unknown scenario returns error."""
        from server import start_attack_scenario
        
        result = start_attack_scenario("unknown_attack", "attacker", "target")
        
        self.assertIn("Error", result)
        self.assertIn("Unknown scenario", result)


class TestCaptureEvidence(unittest.TestCase):
    """Test capture_evidence tool."""

    @patch('server.exec_command')
    def test_capture_routing_snapshot(self, mock_exec):
        """Test routing snapshot capture."""
        from server import capture_evidence
        mock_exec.return_value = "Exit code: 0\n10.0.0.0/24 via 10.0.0.1"
        
        result = capture_evidence("test_container", "routing_snapshot")
        
        self.assertIn("ROUTING TABLE", result)
        self.assertIn("BGP", result)

    @patch('server.exec_command')
    def test_capture_network_state(self, mock_exec):
        """Test network state capture."""
        from server import capture_evidence
        mock_exec.return_value = "Exit code: 0\neth0: 10.0.0.2/24"
        
        result = capture_evidence("test_container", "network_state")
        
        self.assertIn("INTERFACES", result)
        self.assertIn("ARP TABLE", result)

    @patch('server.exec_command')
    def test_capture_full(self, mock_exec):
        """Test full evidence capture."""
        from server import capture_evidence
        mock_exec.return_value = "Exit code: 0\ndata"
        
        result = capture_evidence("test_container", "full")
        
        self.assertIn("ROUTING TABLE", result)
        self.assertIn("INTERFACES", result)
        self.assertIn("PROCESSES", result)

    def test_capture_unknown_type(self):
        """Test unknown evidence type returns error."""
        from server import capture_evidence
        
        result = capture_evidence("test_container", "unknown_type")
        
        self.assertIn("Error", result)
        self.assertIn("Unknown evidence type", result)


if __name__ == '__main__':
    unittest.main()
