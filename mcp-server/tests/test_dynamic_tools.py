import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    exec_command, get_logs, ping_test, get_routing_table, get_bgp_status,
    traceroute, capture_traffic, get_interface_stats
)
from runtime import runtime

class TestDynamicTools(unittest.TestCase):
    def setUp(self):
        runtime.reset()

    @patch.object(runtime, 'get_docker_client')
    def test_exec_command(self, mock_get_client):
        """exec_command should execute command in container"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"Hello World"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = exec_command("test_container", "echo Hello World")
        self.assertIn("Exit code: 0", result)
        self.assertIn("Hello World", result)
        mock_container.exec_run.assert_called_once()
        
    @patch.object(runtime, 'get_docker_client')
    def test_get_logs(self, mock_get_client):
        """get_logs should return container logs"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Log line 1\nLog line 2"
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_logs("test_container", tail=10)
        self.assertIn("Log line 1", result)
        mock_container.logs.assert_called_once_with(tail=10)
        
    @patch.object(runtime, 'get_docker_client')
    def test_ping_test(self, mock_get_client):
        """ping_test should execute ping command"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data."
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = ping_test("src_container", "10.0.0.1", count=3)
        self.assertIn("PING", result)
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("ping", call_args)
        self.assertIn("-c 3", call_args)

    @patch.object(runtime, 'get_docker_client')
    def test_get_routing_table(self, mock_get_client):
        """get_routing_table should execute ip route"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"default via 10.0.0.1 dev eth0"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_routing_table("test_router")
        self.assertIn("default via", result)
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("ip route", call_args)

    @patch.object(runtime, 'get_docker_client')
    def test_get_bgp_status(self, mock_get_client):
        """get_bgp_status should execute birdc show protocol"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"BIRD 2.0 ready.\nName    Proto Table State"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_bgp_status("test_router")
        self.assertIn("BIRD", result)
        mock_container.exec_run.assert_called_once()
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("birdc", call_args)

    @patch.object(runtime, 'get_docker_client')
    def test_traceroute(self, mock_get_client):
        """traceroute should execute traceroute command"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"1  10.0.0.254  0.1 ms"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = traceroute("src_container", "8.8.8.8")
        self.assertIn("10.0.0.254", result)
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("traceroute", call_args)

    @patch.object(runtime, 'get_docker_client')
    def test_capture_traffic(self, mock_get_client):
        """capture_traffic should use timeout and tcpdump"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"tcpdump output line 1\nline 2"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = capture_traffic("test_pod", duration=5, filter="port 80")
        self.assertIn("tcpdump output", result)
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("timeout 5", call_args)
        self.assertIn("tcpdump", call_args)
        self.assertIn("port 80", call_args)
        
    @patch.object(runtime, 'get_docker_client')
    def test_get_interface_stats(self, mock_get_client):
        """get_interface_stats should execute ip link show"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"[{\"ifname\":\"eth0\", \"stats64\":{\"rx\":{\"bytes\":100}}}]"
        )
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        result = get_interface_stats("test_container")
        self.assertIn("eth0", result)
        call_args = mock_container.exec_run.call_args[0][0]
        self.assertIn("ip -s -j link show", call_args)

if __name__ == '__main__':
    unittest.main()
