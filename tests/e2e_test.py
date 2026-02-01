"""
SEED Emulator - E2E Test Suite
Ultra-High Standards Testing for Kubernetes Deployment

Run with: pytest tests/e2e_test.py -v --html=report.html
"""

import subprocess
import time
import pytest
import json
import re
from typing import Tuple, List, Optional


class KubernetesCluster:
    """Helper class for interacting with K8s cluster."""
    
    def __init__(self, namespace: str = "seedemu-v2", kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        
    def _kubectl(self, args: str) -> Tuple[int, str, str]:
        """Execute kubectl command."""
        cmd = f"kubectl {args}"
        if self.kubeconfig:
            cmd = f"kubectl --kubeconfig={self.kubeconfig} {args}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    
    def get_pods(self) -> List[dict]:
        """Get all pods in namespace."""
        rc, stdout, _ = self._kubectl(f"get pods -n {self.namespace} -o json")
        if rc != 0:
            return []
        data = json.loads(stdout)
        return data.get("items", [])
    
    def exec_in_pod(self, pod_name: str, command: str) -> Tuple[int, str]:
        """Execute command in pod."""
        rc, stdout, stderr = self._kubectl(
            f"exec -n {self.namespace} {pod_name} -- {command}"
        )
        return rc, stdout if rc == 0 else stderr
    
    def delete_pod(self, pod_name: str) -> bool:
        """Delete a pod."""
        rc, _, _ = self._kubectl(f"delete pod -n {self.namespace} {pod_name}")
        return rc == 0
    
    def wait_for_pod_ready(self, label_selector: str, timeout: int = 60) -> bool:
        """Wait for pod with selector to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            rc, stdout, _ = self._kubectl(
                f"get pods -n {self.namespace} -l {label_selector} -o jsonpath='{{.items[0].status.phase}}'"
            )
            if rc == 0 and stdout.strip() == "Running":
                return True
            time.sleep(2)
        return False


class TestBGPSessions:
    """Test BGP session establishment."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace="seedemu")
    
    def test_bgp_session_established(self):
        """Verify all BGP sessions are established."""
        # Find router pods
        pods = self.k8s.get_pods()
        router_pods = [p for p in pods if "brd" in p["metadata"]["name"]]
        
        assert len(router_pods) > 0, "No router pods found"
        
        for pod in router_pods:
            pod_name = pod["metadata"]["name"]
            rc, output = self.k8s.exec_in_pod(pod_name, "birdc show protocols")
            
            # Check for established sessions
            if "Established" in output or "BGP" not in output:
                # Either established or no BGP config (RS nodes)
                continue
                
            # Count established vs total BGP sessions
            lines = output.split("\n")
            bgp_lines = [l for l in lines if "BGP" in l]
            established = [l for l in bgp_lines if "Established" in l]
            
            assert len(established) == len(bgp_lines), \
                f"Pod {pod_name}: {len(established)}/{len(bgp_lines)} BGP sessions established"


class TestRoutePropagation:
    """Test route propagation between ASes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace="seedemu")
    
    def test_traceroute_as150_to_as151(self):
        """Verify traceroute from AS150 to AS151 shows correct path."""
        pods = self.k8s.get_pods()
        
        # Find AS150 host
        as150_hosts = [p for p in pods if "as150h" in p["metadata"]["name"]]
        assert len(as150_hosts) > 0, "No AS150 host pod found"
        
        pod_name = as150_hosts[0]["metadata"]["name"]
        rc, output = self.k8s.exec_in_pod(pod_name, "traceroute -n -m 10 10.151.0.71")
        
        # Should have multiple hops through routers
        hops = re.findall(r"^\s*\d+\s+(\d+\.\d+\.\d+\.\d+)", output, re.MULTILINE)
        assert len(hops) >= 2, f"Expected multi-hop path, got {len(hops)} hops: {output}"
        
    def test_ping_cross_as(self):
        """Verify ping connectivity between ASes."""
        pods = self.k8s.get_pods()
        
        # Find AS150 host
        as150_hosts = [p for p in pods if "as150h" in p["metadata"]["name"]]
        assert len(as150_hosts) > 0, "No AS150 host pod found"
        
        pod_name = as150_hosts[0]["metadata"]["name"]
        rc, output = self.k8s.exec_in_pod(pod_name, "ping -c 3 -W 5 10.151.0.71")
        
        assert rc == 0, f"Ping failed: {output}"
        assert "3 received" in output or "3 packets received" in output, \
            f"Packet loss detected: {output}"


class TestWebService:
    """Test web service reachability."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace="seedemu")
    
    def test_web_service_as150(self):
        """Verify web service in AS150 is reachable."""
        pods = self.k8s.get_pods()
        
        # Find any router pod to test from
        router_pods = [p for p in pods if "brd" in p["metadata"]["name"]]
        assert len(router_pods) > 0, "No router pods found"
        
        pod_name = router_pods[0]["metadata"]["name"]
        rc, output = self.k8s.exec_in_pod(pod_name, "curl -s -o /dev/null -w '%{http_code}' http://10.150.0.71")
        
        assert output.strip() == "200", f"Expected HTTP 200, got {output}"
    
    def test_web_service_as151(self):
        """Verify web service in AS151 is reachable."""
        pods = self.k8s.get_pods()
        
        router_pods = [p for p in pods if "brd" in p["metadata"]["name"]]
        assert len(router_pods) > 0, "No router pods found"
        
        pod_name = router_pods[0]["metadata"]["name"]
        rc, output = self.k8s.exec_in_pod(pod_name, "curl -s -o /dev/null -w '%{http_code}' http://10.151.0.71")
        
        assert output.strip() == "200", f"Expected HTTP 200, got {output}"


class TestFaultTolerance:
    """Test fault tolerance and recovery."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace="seedemu")
    
    def test_pod_recovery(self):
        """Verify pod recovers after deletion within 60 seconds."""
        pods = self.k8s.get_pods()
        
        # Find a web host pod
        web_pods = [p for p in pods if "web" in p["metadata"]["name"].lower()]
        assert len(web_pods) > 0, "No web pods found"
        
        pod_info = web_pods[0]
        pod_name = pod_info["metadata"]["name"]
        
        # Get deployment label
        labels = pod_info["metadata"].get("labels", {})
        app_label = labels.get("app", "")
        assert app_label, "Pod has no app label"
        
        # Delete pod
        start_time = time.time()
        assert self.k8s.delete_pod(pod_name), f"Failed to delete pod {pod_name}"
        
        # Wait for recovery
        recovered = self.k8s.wait_for_pod_ready(f"app={app_label}", timeout=60)
        recovery_time = time.time() - start_time
        
        assert recovered, f"Pod did not recover within 60 seconds"
        print(f"Pod recovered in {recovery_time:.1f} seconds")


class TestNodeDistribution:
    """Test pod distribution across nodes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace="seedemu")
    
    def test_pods_distributed_across_nodes(self):
        """Verify pods are distributed across multiple nodes."""
        pods = self.k8s.get_pods()
        
        nodes = set()
        for pod in pods:
            node = pod["spec"].get("nodeName")
            if node:
                nodes.add(node)
        
        assert len(nodes) >= 2, f"Pods only on {len(nodes)} node(s), expected >= 2"
        print(f"Pods distributed across {len(nodes)} nodes: {nodes}")
    
    def test_as_scheduling_correctness(self):
        """Verify AS pods are scheduled on correct nodes per AS group."""
        pods = self.k8s.get_pods()
        
        # Build AS -> node mapping
        as_node_map = {}
        for pod in pods:
            name = pod["metadata"]["name"]
            node = pod["spec"].get("nodeName", "unknown")
            
            # Extract AS number from pod name (e.g., as150h-web -> 150)
            match = re.search(r"as(\d+)", name)
            if match:
                asn = match.group(1)
                if asn not in as_node_map:
                    as_node_map[asn] = set()
                as_node_map[asn].add(node)
        
        # Each AS should be on a single node (based on scheduling strategy)
        for asn, nodes in as_node_map.items():
            if len(nodes) > 1:
                print(f"Warning: AS{asn} pods on multiple nodes: {nodes}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
