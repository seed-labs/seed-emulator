#!/bin/bash
# SEED Emulator - Run E2E Tests Locally
# Usage: ./scripts/run_e2e_tests.sh [namespace]

set -e

NAMESPACE=${1:-seedemu-v2}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "SEED Emulator - E2E Test Runner"
echo "=============================================="
echo "Namespace: $NAMESPACE"
echo ""

# Check prerequisites
check_prereqs() {
    echo "[1/4] Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        echo "ERROR: kubectl not found"
        exit 1
    fi
    
    if ! command -v pytest &> /dev/null; then
        echo "Installing pytest..."
        pip3 install pytest pytest-html pytest-timeout
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        echo "ERROR: Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    echo "✓ Prerequisites OK"
}

# Check pod status
check_pods() {
    echo "[2/4] Checking pod status..."
    
    READY_PODS=$(kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.status.phase}{"\n"}{end}' | grep -c Running || echo "0")
    TOTAL_PODS=$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
    
    echo "  Running pods: $READY_PODS / $TOTAL_PODS"
    
    if [ "$READY_PODS" -lt "$TOTAL_PODS" ]; then
        echo "  Warning: Not all pods are running"
        kubectl get pods -n $NAMESPACE -o wide
    fi
    
    echo "✓ Pod check complete"
}

# Run tests
run_tests() {
    echo "[3/4] Running E2E tests..."
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Export namespace for tests
    export SEEDEMU_NAMESPACE=$NAMESPACE
    
    # Run pytest with HTML report
    pytest tests/e2e_test.py -v \
        --html=test-report.html \
        --self-contained-html \
        --timeout=120 \
        || true
    
    echo ""
    echo "✓ Tests complete"
}

# Generate report
generate_report() {
    echo "[4/4] Generating report..."
    
    echo ""
    echo "=============================================="
    echo "Test Report: $PROJECT_ROOT/test-report.html"
    echo "=============================================="
    
    # Quick summary
    if [ -f "test-report.html" ]; then
        PASSED=$(grep -o 'passed' test-report.html | wc -l)
        FAILED=$(grep -o 'failed' test-report.html | wc -l)
        echo "Summary: $PASSED passed, $FAILED failed"
    fi
}

# Main
check_prereqs
check_pods
run_tests
generate_report

echo ""
echo "Done! Open test-report.html to view detailed results."
