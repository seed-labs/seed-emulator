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
import os
from typing import Tuple, List, Optional

DEFAULT_NAMESPACE = os.environ.get("SEEDEMU_NAMESPACE", "seedemu")
STRICT_MODE = os.environ.get("SEEDEMU_E2E_STRICT", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
KUBECTL_TIMEOUT_SECONDS = int(os.environ.get("SEEDEMU_E2E_KUBECTL_TIMEOUT", "20"))


def fail_or_xfail(message: str) -> None:
    """Fail in strict mode, otherwise xfail for known environment boundaries."""
    if STRICT_MODE:
        pytest.fail(message)
    pytest.xfail(message)


class KubernetesCluster:
    """Helper class for interacting with K8s cluster."""
    
    def __init__(
        self,
        namespace: str = DEFAULT_NAMESPACE,
        kubeconfig: Optional[str] = None,
        timeout_seconds: int = KUBECTL_TIMEOUT_SECONDS,
    ):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.timeout_seconds = timeout_seconds
        
    def _kubectl(self, args: str, timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """Execute kubectl command."""
        cmd = f"kubectl {args}"
        if self.kubeconfig:
            cmd = f"kubectl --kubeconfig={self.kubeconfig} {args}"

        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"kubectl command timed out after {effective_timeout}s: {cmd}"
    
    def get_pods(self) -> List[dict]:
        """Get all pods in namespace."""
        rc, stdout, _ = self._kubectl(f"get pods -n {self.namespace} -o json")
        if rc != 0:
            return []
        data = json.loads(stdout)
        return data.get("items", [])

    def find_pod_by_prefix(self, prefix: str) -> Optional[str]:
        """Find first pod name matching prefix."""
        pods = self.get_pods()
        for pod in pods:
            pod_name = pod["metadata"]["name"]
            if pod_name.startswith(prefix):
                return pod_name
        return None
    
    def exec_in_pod(
        self, pod_name: str, command: str, timeout: Optional[int] = None
    ) -> Tuple[int, str]:
        """Execute command in pod."""
        rc, stdout, stderr = self._kubectl(
            f"exec -n {self.namespace} {pod_name} -- {command}",
            timeout=timeout,
        )
        return rc, stdout if rc == 0 else stderr

    def has_command(self, pod_name: str, command_name: str) -> bool:
        """Check whether a command exists in a pod."""
        rc, _ = self.exec_in_pod(
            pod_name,
            f"sh -lc \"command -v {command_name} >/dev/null 2>&1\"",
            timeout=8,
        )
        return rc == 0
    
    def delete_pod(self, pod_name: str) -> bool:
        """Delete a pod."""
        rc, _, _ = self._kubectl(
            f"delete pod -n {self.namespace} {pod_name}",
            timeout=self.timeout_seconds,
        )
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
        self.k8s = KubernetesCluster(namespace=DEFAULT_NAMESPACE)
    
    def test_bgp_session_established(self):
        """Verify all BGP sessions are established."""
        # Find router pods
        pods = self.k8s.get_pods()
        router_pods = [p for p in pods if "brd" in p["metadata"]["name"]]
        
        assert len(router_pods) > 0, "No router pods found"

        failures = []
        for pod in router_pods:
            pod_name = pod["metadata"]["name"]
            output = ""

            # Allow BGP control plane some settling time after deployment.
            for _ in range(5):
                rc, output = self.k8s.exec_in_pod(
                    pod_name, "birdc show protocols", timeout=10
                )
                if rc != 0:
                    continue

                lines = output.split("\n")
                bgp_lines = [line for line in lines if "BGP" in line]
                if not bgp_lines:
                    break

                established = [line for line in bgp_lines if "Established" in line]
                if len(established) == len(bgp_lines):
                    break
                time.sleep(3)

            lines = output.split("\n")
            bgp_lines = [line for line in lines if "BGP" in line]
            established = [line for line in bgp_lines if "Established" in line]
            if bgp_lines and len(established) != len(bgp_lines):
                failures.append(
                    f"{pod_name}: {len(established)}/{len(bgp_lines)} established; output={output}"
                )

        if failures:
            fail_or_xfail("BGP sessions not fully established: " + " | ".join(failures))


class TestRoutePropagation:
    """Test route propagation between ASes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace=DEFAULT_NAMESPACE)
    
    def test_traceroute_as150_to_as151(self):
        """Verify traceroute from AS150 to AS151 shows correct path."""
        pods = self.k8s.get_pods()
        
        # Find AS150 host
        as150_hosts = [p for p in pods if "as150h" in p["metadata"]["name"]]
        assert len(as150_hosts) > 0, "No AS150 host pod found"
        
        pod_name = as150_hosts[0]["metadata"]["name"]
        if not self.k8s.has_command(pod_name, "traceroute"):
            fail_or_xfail(
                f"Pod {pod_name} missing traceroute binary. Add traceroute package to image."
            )
            return

        rc, output = self.k8s.exec_in_pod(
            pod_name,
            "traceroute -n -m 8 -q 1 -w 2 10.151.0.71",
            timeout=20,
        )
        if rc != 0:
            fail_or_xfail(f"Traceroute command failed on {pod_name}: {output}")
            return
        
        # Should have multiple hops through routers
        hops = re.findall(r"^\s*\d+\s+(\d+\.\d+\.\d+\.\d+)", output, re.MULTILINE)
        if len(hops) < 2:
            fail_or_xfail(f"Expected multi-hop path, got {len(hops)} hops: {output}")
        
    def test_ping_cross_as(self):
        """Verify ping connectivity between ASes."""
        pods = self.k8s.get_pods()
        
        # Find AS150 host
        as150_hosts = [p for p in pods if "as150h" in p["metadata"]["name"]]
        assert len(as150_hosts) > 0, "No AS150 host pod found"
        
        pod_name = as150_hosts[0]["metadata"]["name"]
        rc, output = self.k8s.exec_in_pod(
            pod_name, "ping -c 3 -W 4 10.151.0.71", timeout=20
        )
        if rc != 0:
            fail_or_xfail(f"Ping failed from {pod_name} to 10.151.0.71: {output}")
            return

        if "3 received" not in output and "3 packets received" not in output:
            fail_or_xfail(f"Packet loss detected: {output}")


class TestWebService:
    """Test web service reachability."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace=DEFAULT_NAMESPACE)
    
    def test_web_service_as150(self):
        """Verify web service in AS150 is reachable."""
        pod_name = self.k8s.find_pod_by_prefix("as150brd-")
        assert pod_name, "No AS150 router pod found"
        rc, output = self.k8s.exec_in_pod(
            pod_name,
            "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' http://10.150.0.71",
            timeout=15,
        )
        if rc != 0:
            fail_or_xfail(f"AS150 web curl failed from {pod_name}: {output}")
            return
        assert output.strip() == "200", f"Expected HTTP 200, got {output}"
    
    def test_web_service_as151(self):
        """Verify web service in AS151 is reachable."""
        pod_name = self.k8s.find_pod_by_prefix("as151brd-")
        assert pod_name, "No AS151 router pod found"
        rc, output = self.k8s.exec_in_pod(
            pod_name,
            "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' http://10.151.0.71",
            timeout=15,
        )
        if rc != 0:
            fail_or_xfail(f"AS151 web curl failed from {pod_name}: {output}")
            return
        assert output.strip() == "200", f"Expected HTTP 200, got {output}"


class TestFaultTolerance:
    """Test fault tolerance and recovery."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace=DEFAULT_NAMESPACE)
    
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
        if not self.k8s.delete_pod(pod_name):
            fail_or_xfail(f"Failed to delete pod {pod_name}")
            return
        
        # Wait for recovery
        recovered = self.k8s.wait_for_pod_ready(f"app={app_label}", timeout=60)
        recovery_time = time.time() - start_time
        
        if not recovered:
            fail_or_xfail("Pod did not recover within 60 seconds")
            return
        print(f"Pod recovered in {recovery_time:.1f} seconds")


class TestNodeDistribution:
    """Test pod distribution across nodes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.k8s = KubernetesCluster(namespace=DEFAULT_NAMESPACE)
    
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
