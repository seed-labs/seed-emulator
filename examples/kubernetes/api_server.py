#!/usr/bin/env python3
"""
SEED Emulator Kubernetes API Server
Bridge between web interface and Kubernetes cluster for real command execution
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import json
import os
import time
import yaml
from kubernetes import client, config
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Kubernetes configuration
try:
    config.load_incluster_config()  # For running inside cluster
except:
    config.load_kube_config()  # For local development

k8s_apps_v1 = client.AppsV1Api()
k8s_core_v1 = client.CoreV1Api()
k8s_networking_v1 = client.NetworkingV1Api()

NAMESPACE = "seedemu"

class KubernetesAPI:
    """Kubernetes API wrapper for SEED Emulator"""
    
    @staticmethod
    def get_pods():
        """Get all pods in seedemu namespace"""
        try:
            pods = k8s_core_v1.list_namespaced_pod(namespace=NAMESPACE)
            return [{
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'ready': all(container.ready for container in pod.status.container_statuses or []),
                'ip': pod.status.pod_ip,
                'node': pod.spec.node_name,
                'created': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                'labels': pod.metadata.labels or {}
            } for pod in pods.items]
        except Exception as e:
            logger.error(f"Error getting pods: {e}")
            return []
    
    @staticmethod
    def get_services():
        """Get all services in seedemu namespace"""
        try:
            services = k8s_core_v1.list_namespaced_service(namespace=NAMESPACE)
            return [{
                'name': svc.metadata.name,
                'type': svc.spec.type,
                'cluster_ip': svc.spec.cluster_ip,
                'external_ip': svc.spec.external_i_ps,
                'ports': [{'port': port.port, 'target_port': port.target_port, 'node_port': port.node_port} 
                         for port in svc.spec.ports or []],
                'selector': svc.spec.selector or {}
            } for svc in services.items]
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return []
    
    @staticmethod
    def get_network_attachments():
        """Get network attachment definitions"""
        try:
            nad = k8s_core_v1.list_namespaced_custom_object(
                group="k8s.cni.cncf.io",
                version="v1",
                plural="network-attachment-definitions",
                namespace=NAMESPACE
            )
            return [{
                'name': item['metadata']['name'],
                'config': item.get('spec', {}).get('config', '')
            } for item in nad.get('items', [])]
        except Exception as e:
            logger.error(f"Error getting network attachments: {e}")
            return []
    
    @staticmethod
    def execute_command(pod_name, command, container=None):
        """Execute command in pod"""
        try:
            if not container:
                # Get first container name if not specified
                pod = k8s_core_v1.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
                container = pod.spec.containers[0].name if pod.spec.containers else None
            
            if not container:
                return {'success': False, 'output': 'No container found'}
            
            # Execute command using kubectl exec
            cmd = [
                'kubectl', 'exec', '-n', NAMESPACE, pod_name, '-c', container,
                '--', 'sh', '-c', command
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'output': '', 'error': 'Command timeout'}
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {'success': False, 'output': '', 'error': str(e)}
    
    @staticmethod
    def get_pod_logs(pod_name, container=None, lines=100):
        """Get pod logs"""
        try:
            logs = k8s_core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=NAMESPACE,
                container=container,
                tail_lines=lines
            )
            return {'success': True, 'logs': logs}
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return {'success': False, 'logs': str(e)}

class NetworkCommands:
    """Network command execution utilities"""
    
    @staticmethod
    def ping_node(target_ip, source_pod=None):
        """Execute ping from a pod to target IP"""
        if not source_pod:
            # Find a router pod to use as source
            pods = KubernetesAPI.get_pods()
            router_pods = [p for p in pods if 'router' in p['name'].lower()]
            if router_pods:
                source_pod = router_pods[0]['name']
            else:
                source_pod = pods[0]['name'] if pods else None
        
        if not source_pod:
            return {'success': False, 'output': 'No source pod available'}
        
        command = f"ping -c 4 {target_ip}"
        return KubernetesAPI.execute_command(source_pod, command)
    
    @staticmethod
    def traceroute_node(target_ip, source_pod=None):
        """Execute traceroute from a pod to target IP"""
        if not source_pod:
            pods = KubernetesAPI.get_pods()
            router_pods = [p for p in pods if 'router' in p['name'].lower()]
            if router_pods:
                source_pod = router_pods[0]['name']
            else:
                source_pod = pods[0]['name'] if pods else None
        
        if not source_pod:
            return {'success': False, 'output': 'No source pod available'}
        
        command = f"traceroute {target_ip}"
        return KubernetesAPI.execute_command(source_pod, command)
    
    @staticmethod
    def get_routing_table(pod_name):
        """Get routing table from a pod"""
        command = "ip route show"
        return KubernetesAPI.execute_command(pod_name, command)
    
    @staticmethod
    def get_bgp_summary(pod_name):
        """Get BGP summary from a router pod"""
        command = "vtysh -c 'show ip bgp summary'"
        return KubernetesAPI.execute_command(pod_name, command)
    
    @staticmethod
    def get_interfaces(pod_name):
        """Get network interfaces from a pod"""
        command = "ip addr show"
        return KubernetesAPI.execute_command(pod_name, command)

# API Routes
@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory('.', 'index.html')

@app.route('/api/status')
def api_status():
    """Get API and cluster status"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'kubernetes_connected': True
    })

@app.route('/api/pods')
def api_pods():
    """Get all pods"""
    return jsonify(KubernetesAPI.get_pods())

@app.route('/api/services')
def api_services():
    """Get all services"""
    return jsonify(KubernetesAPI.get_services())

@app.route('/api/network-attachments')
def api_network_attachments():
    """Get network attachment definitions"""
    return jsonify(KubernetesAPI.get_network_attachments())

@app.route('/api/execute', methods=['POST'])
def api_execute():
    """Execute command in pod"""
    data = request.json
    pod_name = data.get('pod_name')
    command = data.get('command')
    container = data.get('container')
    
    if not pod_name or not command:
        return jsonify({'success': False, 'error': 'pod_name and command required'}), 400
    
    result = KubernetesAPI.execute_command(pod_name, command, container)
    return jsonify(result)

@app.route('/api/ping', methods=['POST'])
def api_ping():
    """Ping target IP"""
    data = request.json
    target_ip = data.get('target_ip')
    source_pod = data.get('source_pod')
    
    if not target_ip:
        return jsonify({'success': False, 'error': 'target_ip required'}), 400
    
    result = NetworkCommands.ping_node(target_ip, source_pod)
    return jsonify(result)

@app.route('/api/traceroute', methods=['POST'])
def api_traceroute():
    """Traceroute to target IP"""
    data = request.json
    target_ip = data.get('target_ip')
    source_pod = data.get('source_pod')
    
    if not target_ip:
        return jsonify({'success': False, 'error': 'target_ip required'}), 400
    
    result = NetworkCommands.traceroute_node(target_ip, source_pod)
    return jsonify(result)

@app.route('/api/routes/<pod_name>')
def api_routes(pod_name):
    """Get routing table for pod"""
    result = NetworkCommands.get_routing_table(pod_name)
    return jsonify(result)

@app.route('/api/bgp/<pod_name>')
def api_bgp(pod_name):
    """Get BGP summary for pod"""
    result = NetworkCommands.get_bgp_summary(pod_name)
    return jsonify(result)

@app.route('/api/interfaces/<pod_name>')
def api_interfaces(pod_name):
    """Get network interfaces for pod"""
    result = NetworkCommands.get_interfaces(pod_name)
    return jsonify(result)

@app.route('/api/logs/<pod_name>')
def api_logs(pod_name):
    """Get logs for pod"""
    container = request.args.get('container')
    lines = int(request.args.get('lines', 100))
    result = KubernetesAPI.get_pod_logs(pod_name, container, lines)
    return jsonify(result)

@app.route('/api/network-status')
def api_network_status():
    """Get comprehensive network status"""
    pods = KubernetesAPI.get_pods()
    services = KubernetesAPI.get_services()
    network_attachments = KubernetesAPI.get_network_attachments()
    
    # Count different types of pods
    router_pods = [p for p in pods if 'router' in p['name'].lower()]
    host_pods = [p for p in pods if 'host' in p['name'].lower()]
    
    # Get BGP status from router pods
    bgp_status = {}
    for router_pod in router_pods[:3]:  # Check first 3 routers
        bgp_result = NetworkCommands.get_bgp_summary(router_pod['name'])
        if bgp_result['success']:
            bgp_status[router_pod['name']] = bgp_result['output']
    
    return jsonify({
        'pods': {
            'total': len(pods),
            'running': len([p for p in pods if p['status'] == 'Running']),
            'routers': len(router_pods),
            'hosts': len(host_pods)
        },
        'services': {
            'total': len(services),
            'nodeport': len([s for s in services if s['type'] == 'NodePort']),
            'clusterip': len([s for s in services if s['type'] == 'ClusterIP'])
        },
        'networks': {
            'attachments': len(network_attachments),
            'multus_enabled': len(network_attachments) > 0
        },
        'bgp_status': bgp_status,
        'timestamp': time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
