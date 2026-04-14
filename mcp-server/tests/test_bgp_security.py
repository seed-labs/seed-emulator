import unittest
import sys
import os
from unittest.mock import patch, MagicMock
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import bgp_announce_prefix, get_looking_glass
from runtime import runtime

class TestBGPSecurityTools(unittest.TestCase):
    def setUp(self):
        runtime.reset()

    @patch.object(runtime, 'get_docker_client')
    def test_bgp_announce_prefix(self, mock_get_client):
        """bgp_announce_prefix should build a backend-aware command"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"BIRD 2.0\nReading configuration"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = bgp_announce_prefix("as666-attacker", "10.150.0.0/24")
        self.assertIn("Announced prefix", result)
        self.assertIn("10.150.0.0/24", result)
        self.assertGreaterEqual(mock_container.exec_run.call_count, 1)
        command = mock_container.exec_run.call_args[0][0]
        self.assertIn("show bgp summary", command)
        self.assertIn("birdc <<EOF_SEEDOPS_BIRD", command)
        self.assertIn("ip route add 10.150.0.0/24", command)

    @patch.object(runtime, 'get_docker_client')
    def test_get_looking_glass_uses_backend_aware_command(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"10.150.0.0/24 via 10.207.0.1 on eth1"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client

        _ = get_looking_glass("as100-router", "10.150.0.0/24")
        command = mock_container.exec_run.call_args[0][0]
        self.assertIn("show bgp summary", command)
        self.assertIn("birdc \"show route for 10.150.0.0/24 all\"", command)
        
    @patch.object(runtime, 'get_docker_client')
    def test_get_looking_glass_with_prefix(self, mock_get_client):
        """get_looking_glass should return route text with prefix filter"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"10.150.0.0/24 via 10.207.0.1 on eth1"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_looking_glass("as100-router", "10.150.0.0/24")
        self.assertIn("10.150.0.0/24", result)
        
    @patch.object(runtime, 'get_docker_client')
    def test_get_looking_glass_all_routes(self, mock_get_client):
        """get_looking_glass without prefix should show all routes"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"Table master4:\n10.100.0.0/24\n10.200.0.0/24"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_looking_glass("as100-router")
        self.assertIn("Table master4", result)
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("show bgp summary", call_args)
        self.assertIn("show route", call_args)

if __name__ == '__main__':
    unittest.main()
