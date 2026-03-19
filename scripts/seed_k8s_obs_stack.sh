#!/usr/bin/env bash
set -euo pipefail

# Optional Prometheus + Grafana stack for demos / papers.
# Not part of PASS/FAIL. Default path remains: evidence artifacts + showcase + kubectl.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1090
source "${SCRIPT_DIR}/env_seedemu.sh"

ACTION="${1:-help}"

SEED_OBS_NAMESPACE="${SEED_OBS_NAMESPACE:-seedemu-observe}"
SEED_OBS_GRAFANA_PASSWORD="${SEED_OBS_GRAFANA_PASSWORD:-seedemu}"

log() { echo "[obs] $*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_kubeconfig() {
  if kubectl get nodes >/dev/null 2>&1; then
    return 0
  fi

  local kubeconfig_path
  kubeconfig_path="${REPO_ROOT}/output/kubeconfigs/seedemu-k3s.yaml"
  if [ -f "${kubeconfig_path}" ]; then
    export KUBECONFIG="${kubeconfig_path}"
  fi

  kubectl get nodes >/dev/null 2>&1
}

apply_manifest() {
  kubectl apply -f -
}

apply_namespaced_manifest() {
  kubectl -n "${SEED_OBS_NAMESPACE}" apply -f -
}

up() {
  require_cmd kubectl
  ensure_kubeconfig

  log "Creating namespace ${SEED_OBS_NAMESPACE}"
  kubectl create namespace "${SEED_OBS_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null

  log "Applying Prometheus RBAC"
  cat <<EOF | apply_manifest
apiVersion: v1
kind: ServiceAccount
metadata:
  name: seedemu-observe-prometheus
  namespace: ${SEED_OBS_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: seedemu-observe-prometheus
rules:
  - apiGroups: [""]
    resources: ["nodes", "nodes/metrics", "nodes/proxy", "services", "endpoints", "pods", "namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["discovery.k8s.io"]
    resources: ["endpointslices"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: seedemu-observe-prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: seedemu-observe-prometheus
subjects:
  - kind: ServiceAccount
    name: seedemu-observe-prometheus
    namespace: ${SEED_OBS_NAMESPACE}
EOF

  log "Applying Prometheus config + deployment"
  cat <<'EOF' | sed "s|__SEED_OBS_NAMESPACE__|${SEED_OBS_NAMESPACE}|g" | apply_namespaced_manifest
apiVersion: v1
kind: ConfigMap
metadata:
  name: seedemu-observe-prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets: ["127.0.0.1:9090"]

      # Scrape kubelet metrics (for node/pod resources). Works on most clusters; TLS is often self-signed.
      - job_name: kubelet
        scheme: https
        tls_config:
          insecure_skip_verify: true
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        kubernetes_sd_configs:
          - role: node
        relabel_configs:
          - action: labelmap
            regex: __meta_kubernetes_node_label_(.+)
        metrics_path: /metrics

      # Scrape cAdvisor metrics (container-level). Can be heavy; keep as optional.
      - job_name: cadvisor
        scheme: https
        tls_config:
          insecure_skip_verify: true
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        kubernetes_sd_configs:
          - role: node
        metrics_path: /metrics/cadvisor
        relabel_configs:
          - action: labelmap
            regex: __meta_kubernetes_node_label_(.+)
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seedemu-observe-prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: seedemu-observe-prometheus
  template:
    metadata:
      labels:
        app: seedemu-observe-prometheus
    spec:
      serviceAccountName: seedemu-observe-prometheus
      containers:
        - name: prometheus
          image: prom/prometheus:v2.51.2
          args:
            - "--config.file=/etc/prometheus/prometheus.yml"
            - "--storage.tsdb.path=/prometheus"
            - "--storage.tsdb.retention.time=24h"
          ports:
            - containerPort: 9090
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          volumeMounts:
            - name: config
              mountPath: /etc/prometheus
            - name: data
              mountPath: /prometheus
      volumes:
        - name: config
          configMap:
            name: seedemu-observe-prometheus-config
        - name: data
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: seedemu-observe-prometheus
spec:
  selector:
    app: seedemu-observe-prometheus
  ports:
    - name: http
      port: 9090
      targetPort: 9090
EOF

  log "Applying Grafana (datasource provisioned)"
  cat <<'EOF' | sed "s|__SEED_OBS_NAMESPACE__|${SEED_OBS_NAMESPACE}|g" | apply_namespaced_manifest
apiVersion: v1
kind: ConfigMap
metadata:
  name: seedemu-observe-grafana-datasources
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://seedemu-observe-prometheus:9090
        isDefault: true
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seedemu-observe-grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: seedemu-observe-grafana
  template:
    metadata:
      labels:
        app: seedemu-observe-grafana
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:10.4.1
          ports:
            - containerPort: 3000
          env:
            - name: GF_SECURITY_ADMIN_USER
              value: admin
            - name: GF_SECURITY_ADMIN_PASSWORD
              value: __SEED_OBS_GRAFANA_PASSWORD__
            - name: GF_USERS_DEFAULT_THEME
              value: dark
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: datasources
              mountPath: /etc/grafana/provisioning/datasources
      volumes:
        - name: datasources
          configMap:
            name: seedemu-observe-grafana-datasources
---
apiVersion: v1
kind: Service
metadata:
  name: seedemu-observe-grafana
spec:
  selector:
    app: seedemu-observe-grafana
  ports:
    - name: http
      port: 3000
      targetPort: 3000
EOF

  # Patch grafana password without leaking into the manifest file.
  kubectl -n "${SEED_OBS_NAMESPACE}" set env deployment/seedemu-observe-grafana \
    "GF_SECURITY_ADMIN_PASSWORD=${SEED_OBS_GRAFANA_PASSWORD}" >/dev/null 2>&1 || true

  log "Waiting for pods Ready"
  kubectl -n "${SEED_OBS_NAMESPACE}" rollout status deploy/seedemu-observe-prometheus --timeout=300s
  kubectl -n "${SEED_OBS_NAMESPACE}" rollout status deploy/seedemu-observe-grafana --timeout=300s

  log "Up. Next: ${SCRIPT_DIR}/seed_k8s_obs_stack.sh port-forward"
}

down() {
  require_cmd kubectl
  ensure_kubeconfig

  log "Deleting namespace ${SEED_OBS_NAMESPACE}"
  kubectl delete namespace "${SEED_OBS_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  log "Down."
}

port_forward() {
  require_cmd kubectl
  ensure_kubeconfig

  log "Grafana: http://127.0.0.1:3000/ (user=admin pass=${SEED_OBS_GRAFANA_PASSWORD})"
  log "Prometheus: http://127.0.0.1:9090/"
  log "Press Ctrl+C to stop."

  kubectl -n "${SEED_OBS_NAMESPACE}" port-forward svc/seedemu-observe-grafana 3000:3000 &
  kubectl -n "${SEED_OBS_NAMESPACE}" port-forward svc/seedemu-observe-prometheus 9090:9090 &
  wait
}

usage() {
  cat <<USAGE
Usage: scripts/seed_k8s_obs_stack.sh <up|down|port-forward>

This is OPTIONAL: used for demos / paper plots.
It does NOT affect PASS/FAIL (verify/report artifacts remain the source of truth).

Env:
  SEED_OBS_NAMESPACE=${SEED_OBS_NAMESPACE}
  SEED_OBS_GRAFANA_PASSWORD=<password> (default: ${SEED_OBS_GRAFANA_PASSWORD})
USAGE
}

case "${ACTION}" in
  up) up ;;
  down) down ;;
  port-forward) port_forward ;;
  -h|--help|help) usage ;;
  *)
    usage
    exit 1
    ;;
esac

