# Local Quick Runbook: Kind + Multus + KubeVirt

This runbook is the public local-development path for the SEED K8s backend.
Use it when you want a **single-machine smoke environment** for compiler,
network, and hybrid-runtime work.

The repository root is written as `<repo_root>` throughout this document.

## 1. What this runbook validates

This runbook covers two local tracks:

1. **Degraded runtime**  
   All-container validation to prove the compiler, image path, Kubernetes
   manifests, and experiment network are healthy.
2. **Full hybrid runtime**  
   VM router plus container hosts, used to validate the KubeVirt path and
   multi-interface behavior.

Both tracks use:

```bash
scripts/validate_kubevirt_hybrid.sh
```

and write evidence into `SEED_ARTIFACT_DIR`.

## 2. Prerequisites

### 2.1 Required commands

```bash
command -v docker kubectl conda rg kind || true
docker version
kubectl version --client
```

Expected:

- Docker is available.
- `kubectl` is available.
- Conda is available.
- `kind` is optional because `setup_kubevirt_cluster.sh` can install it.

### 2.2 Python environment

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda env list | rg -n "seedemu-k8s-py310" || true
conda activate seedemu-k8s-py310
python -V
python -c "import yaml; import geopy; print('deps-ok')"
```

If the environment does not exist yet:

```bash
conda create -n seedemu-k8s-py310 python=3.10 -y
conda activate seedemu-k8s-py310
cd <repo_root>
pip install -r requirements.txt -r tests/requirements.txt
```

### 2.3 Repository guardrails

```bash
cd <repo_root>
source scripts/env_seedemu.sh
python -c "import seedemu; print('seedemu-import-ok')"
echo "REPO_ROOT=$REPO_ROOT"
echo "PYTHONPATH=$PYTHONPATH"
```

This is the local equivalent of making sure Docker Compose runs from the correct
project directory. It prevents import-path drift.

## 3. Bootstrap the local cluster

### 3.1 Create or repair the local cluster

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_CLUSTER_NAME=seedemu-kvtest WORKER_COUNT=2 ./setup_kubevirt_cluster.sh
kubectl config use-context kind-seedemu-kvtest
```

This prepares:

- a Kind cluster,
- a local registry,
- Multus,
- KubeVirt.

### 3.2 Health check

```bash
kubectl get nodes -o wide
kubectl -n kube-system get ds kube-multus-ds -o wide
kubectl -n kubevirt get pods -o wide
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg -n "kind-registry|registry"
```

Expected:

- all nodes are `Ready`,
- `kube-multus-ds` is healthy on every node,
- KubeVirt control-plane Pods are running,
- the local registry container is present.

## 4. Track A: degraded runtime

Use this first. It is the fastest local path and gives the clearest signal when
the backend or runtime wiring is broken.

### 4.1 Run it

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_NAMESPACE=seedemu-local-quick \
SEED_REGISTRY=localhost:5001 \
SEED_CNI_TYPE=bridge \
SEED_RUNTIME_PROFILE=degraded \
SEED_CLEAN_NAMESPACE=true \
SEED_ARTIFACT_DIR="${REPO_ROOT}/output/kubevirt_validation_local_quick" \
./scripts/validate_kubevirt_hybrid.sh
```

### 4.2 Expected outcome

- the runtime profile resolves to `degraded`,
- Deployments become ready,
- BGP evidence includes `Established`,
- connectivity succeeds directly or within the retry window,
- recovery evidence shows that a deleted Pod returns.

### 4.3 First evidence files to inspect

```bash
ls -la "${REPO_ROOT}/output/kubevirt_validation_local_quick"
cat "${REPO_ROOT}/output/kubevirt_validation_local_quick/runtime_profile.json"
cat "${REPO_ROOT}/output/kubevirt_validation_local_quick/recovery_check.json"
sed -n '1,80p' "${REPO_ROOT}/output/kubevirt_validation_local_quick/bird_protocols.txt"
```

## 5. Track B: full hybrid runtime

Use this to validate the actual VM path.

### 5.1 Run it

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_NAMESPACE=seedemu-local-full \
SEED_REGISTRY=localhost:5001 \
SEED_CNI_TYPE=bridge \
SEED_RUNTIME_PROFILE=full \
SEED_CLEAN_NAMESPACE=true \
SEED_ARTIFACT_DIR="${REPO_ROOT}/output/kubevirt_validation_local_full" \
./scripts/validate_kubevirt_hybrid.sh
```

### 5.2 Live observation

```bash
kubectl -n seedemu-local-full get pods -o wide
kubectl -n seedemu-local-full get vm,vmi -o wide
kubectl -n seedemu-local-full get events --sort-by=.lastTimestamp | tail -n 30
```

Expected:

- a `virt-launcher-*` Pod appears,
- the `VirtualMachineInstance` becomes ready,
- the experiment Pods and VMs share the same validation flow.

### 5.3 First evidence files to inspect

```bash
ls -la "${REPO_ROOT}/output/kubevirt_validation_local_full"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/runtime_profile.json"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/vm_vmi.txt"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/recovery_check.json"
```

## 6. Run core examples directly

Use this section when you are editing example scripts and want a shorter loop
than the full validation harness.

### 6.1 `k8s_transit_as.py`

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-transit-as
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_transit_as.py
cd output_transit_as
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
```

### 6.2 `k8s_mini_internet.py`

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-mini
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_mini_internet.py
cd output_mini_internet
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
```

### 6.3 `k8s_mini_internet_with_visualization.py`

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-mini-viz
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_mini_internet_with_visualization.py
cd output_mini_internet_with_viz
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
kubectl -n "${SEED_NAMESPACE}" port-forward service/seedemu-internet-map-service 8080:8080
```

Then open:

- `http://127.0.0.1:8080/`

## 7. Fast troubleshooting

### 7.1 Pod stuck in `ContainerCreating`

```bash
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -n 50
```

If the message points to Multus:

```bash
kubectl -n kube-system get ds kube-multus-ds -o wide
kubectl -n kube-system get pods -l name=multus -o wide
```

### 7.2 Image pull failures

```bash
docker ps | rg -n "kind-registry"
kubectl -n kube-public get cm local-registry-hosting -o yaml | sed -n '1,80p'
kubectl -n <ns> describe pod <pod> | rg -n "Failed|ImagePull|Back-off|pull" || true
```

### 7.3 BGP is not established

```bash
kubectl -n <ns> get pods -l seedemu.io/name=router0 -o name
kubectl -n <ns> exec <router-pod> -- birdc s p
```

### 7.4 VMI is not ready

```bash
kubectl -n <ns> get vm,vmi -o wide
kubectl -n <ns> describe vmi <vmi-name> | sed -n '1,260p'
kubectl -n kubevirt get pods -o wide
kubectl -n kubevirt logs -l kubevirt.io=virt-handler --tail=120 || true
```

## 8. Cleanup

### 8.1 Delete experiment namespaces

```bash
kubectl delete ns seedemu-local-quick --ignore-not-found
kubectl delete ns seedemu-local-full --ignore-not-found
```

### 8.2 Reset the local Kind environment

```bash
kind delete cluster --name seedemu-kvtest
docker rm -f kind-registry || true
```
