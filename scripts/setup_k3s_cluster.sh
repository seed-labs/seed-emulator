#!/bin/bash
# SEED Emulator - K3s Multi-Node Cluster Setup Script
# This script sets up a 3-node K3s cluster for ultra-high standards testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "SEED Emulator - K3s Multi-Node Cluster Setup"
echo "=============================================="

# Check prerequisites
check_prerequisites() {
    echo "[1/5] Checking prerequisites..."
    
    if ! command -v ansible &> /dev/null; then
        echo "Installing Ansible..."
        pip3 install ansible
    fi
    
    if ! command -v ssh &> /dev/null; then
        echo "ERROR: SSH not found"
        exit 1
    fi
    
    echo "✓ Prerequisites OK"
}

# Verify VM connectivity
verify_connectivity() {
    echo "[2/5] Verifying VM connectivity..."
    
    HOSTS=("192.168.64.10" "192.168.64.11" "192.168.64.12")
    for host in "${HOSTS[@]}"; do
        if ping -c 1 -W 2 "$host" &> /dev/null; then
            echo "  ✓ $host reachable"
        else
            echo "  ✗ $host unreachable"
            echo ""
            echo "Please ensure VMs are running with these IPs:"
            echo "  - 192.168.64.10 (k3s-master)"
            echo "  - 192.168.64.11 (k3s-worker1)"
            echo "  - 192.168.64.12 (k3s-worker2)"
            exit 1
        fi
    done
    
    echo "✓ All VMs reachable"
}

# Run Ansible playbook
run_ansible() {
    echo "[3/5] Installing K3s cluster..."
    
    cd "$PROJECT_ROOT/ansible"
    ansible-playbook -i inventory.yml k3s-install.yml
    
    echo "✓ K3s cluster installed"
}

# Setup private registry
setup_registry() {
    echo "[4/5] Setting up private registry..."
    
    ssh parallels@192.168.64.10 "docker run -d -p 5000:5000 --restart=always --name registry registry:2" || true
    
    echo "✓ Registry running at 192.168.64.10:5000"
}

# Verify cluster
verify_cluster() {
    echo "[5/5] Verifying cluster..."
    
    ssh parallels@192.168.64.10 "kubectl get nodes -o wide"
    
    echo ""
    echo "=============================================="
    echo "K3s Cluster Ready!"
    echo "=============================================="
    echo ""
    echo "To use the cluster:"
    echo "  export KUBECONFIG=\$(ssh parallels@192.168.64.10 'cat /etc/rancher/k3s/k3s.yaml')"
    echo ""
    echo "To deploy SEED Emulator:"
    echo "  cd examples/kubernetes"
    echo "  PYTHONPATH=../.. python3 k8s_multinode_demo_dynamic.py"
    echo "  cd output_multinode_bridge"
    echo "  ./build_images.sh"
    echo "  # Push to registry: docker tag <img> 192.168.64.10:5000/<img> && docker push"
}

# Main
check_prerequisites
verify_connectivity
run_ansible
setup_registry
verify_cluster
