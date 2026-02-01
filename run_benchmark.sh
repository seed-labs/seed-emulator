#!/bin/bash
set -a

# Results file
RESULT_FILE="benchmark_results.txt"
echo "SeedEmulator Benchmark: Docker Compose vs Kubernetes" > $RESULT_FILE
echo "==================================================" >> $RESULT_FILE
echo "" >> $RESULT_FILE

measure_time() {
    start_time=$(date +%s)
    "$@"
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "Time taken: ${duration} seconds"
    echo "$1: ${duration} seconds" >> $RESULT_FILE
}

# --- Docker Compose Benchmark ---
echo "--- Benchmarking Docker Compose ---"
CDIR="examples/basic/A00_simple_as/output"

# Pre-build images to measure deployment time only
echo "Pre-building Docker images..."
(cd $CDIR && docker compose build --quiet)

echo "Starting Docker Compose deployment..."
run_docker() {
    (cd $CDIR && docker compose up -d)
    # Wait for all containers to be running
    echo "Waiting for containers to be running..."
    while [ "$(docker compose -f $CDIR/docker-compose.yml ps --format json | grep -c '"State":"running"')" -lt 9 ]; do
        sleep 1
    done
}

measure_time run_docker

# Cleanup Docker
echo "Cleaning up Docker..."
(cd $CDIR && docker compose down)
echo "" >> $RESULT_FILE

# --- Kubernetes Benchmark ---
echo "--- Benchmarking Kubernetes ---"
KDIR="examples/kubernetes/output_simple_as"
NAMESPACE="seedemu"

# Ensure images are ready (assuming previous setup)
# We assume images are in localhost:5001 from previous steps

echo "Starting Kubernetes deployment..."
run_k8s() {
    kubectl apply -f $KDIR/k8s.yaml
    # Wait for all pods to be Ready
    echo "Waiting for pods to be Ready..."
    kubectl wait --for=condition=Ready pods --all -n $NAMESPACE --timeout=300s > /dev/null
}

measure_time run_k8s

# Cleanup Kubernetes
echo "Cleaning up Kubernetes..."
kubectl delete -f $KDIR/k8s.yaml --wait=true

cat $RESULT_FILE
