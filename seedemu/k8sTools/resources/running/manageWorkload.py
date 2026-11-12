"""Build and deploy compiler workloads with the B62/B63 staged design.

Inputs: configRunning.yaml, configK3s.yaml, compiler manifests/image contexts.
Outputs: output/k8stools/ manifests, image plans, stage receipts and queue logs.
Side effects: build shared Docker bases, import node-specific containerd images,
prepare VLAN parents, and create the selected namespace's workload resources.
Called by ManageRunningStage.py from its packaged temporary running directory.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

import yaml

import ManageK8sManifest as manifestTools
import ManageRunningStage as stages
from deployWorkerQueues import dispatchQueues


LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
CONTROLLERS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet", "Pod"}
DEFAULT_DEPLOY = dict(controllerApplyMode="worker-queue", workerConcurrencyMode="resource",
    workerMaxInFlight=4, workerCpuPerStartup=0.5, workerMemoryGiBPerStartup=1,
    workerReservedCpu=1, workerReservedMemoryGiB=2, workerConcurrencyCeiling=64,
    workerPollSeconds=2, workerStartupTimeoutSeconds=600, batchSize=20,
    subnetBatchSize=250)


def loadDocuments(path):
    """Load nonempty Kubernetes mappings from path, including JSON Lists."""
    with Path(path).open() as handle:
        docs = [doc for doc in yaml.load_all(handle, Loader=LOADER) if doc]
    return [item for doc in docs for item in
            (doc.get("items", []) if doc.get("kind") == "List" else [doc])]


def writeDocuments(path, docs):
    """Write docs as JSON documents separated by YAML markers for kubectl."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n---\n".join(json.dumps(doc) for doc in docs) + "\n")


def readOptions(config):
    """Resolve packaged running/deploy options from config and its setup state."""
    running = manifestTools.load_yaml(str(config))
    values = manifestTools.running_context(str(config))
    setup = manifestTools.load_yaml(values["setupConfig"])
    options = {**(setup.get("k8sTools", {}).get("running") or {}),
               **(running.get("running") or {})}
    deploy = {**DEFAULT_DEPLOY, **(setup.get("deploy") or {}), **(running.get("deploy") or {})}
    for key, default in [("preloadNodeConcurrency", 4), ("imageBuildTimeoutSeconds", 1800)]:
        value = options.setdefault(key, default)
        if type(value) is not int or value <= 0:
            raise ValueError(f"k8sTools.running.{key} must be a positive integer")
    mode = options.setdefault("imageBuildMode", "fast")
    if mode not in {"fast", "registry"}:
        raise ValueError("k8sTools.running.imageBuildMode must be fast or registry")
    for key in ("batchSize", "subnetBatchSize"):
        if type(deploy[key]) is not int or deploy[key] <= 0:
            raise ValueError(f"deploy.{key} must be a positive integer")
    return values, options, deploy


@contextmanager
def recordStage(root, name):
    """Record actual success/failure and timing of name under artifact root."""
    began = time.monotonic()
    row = dict(name=name, status="RUNNING", started=time.time())
    path = root / (name + ".json")
    path.write_text(json.dumps(row, indent=2))
    print(f"[k8sTools] {name} started", flush=True)
    try:
        yield
        row["status"] = "PASS"
    except BaseException as error:
        row.update(status="FAIL", error=str(error))
        raise
    finally:
        row.update(durationSeconds=time.monotonic()-began, finished=time.time())
        path.write_text(json.dumps(row, indent=2))
        print(f"[k8sTools] {name} {row['status']} ({row['durationSeconds']:.1f}s)", flush=True)


def readPodSpec(doc):
    """Return a controller/Pod's container spec, or an empty mapping."""
    if doc.get("kind") == "Pod":
        return doc.get("spec", {})
    return doc.get("spec", {}).get("template", {}).get("spec", {})


def createRuntimeManifest(config):
    """Render images and fabric in one pass; retain the compiler source unchanged."""
    values, options, deploy = readOptions(config)
    root = Path(values["outputDir"]) / "k8stools"
    root.mkdir(exist_ok=True)
    source = Path(values["manifest"])
    if values["networkBackend"] in {"kube-ovn", "ovn"} and source.name != "k8s.kube-ovn.yaml":
        converted = root / "network.yaml"
        manifestTools.renderKubeOvnManifest(str(source), converted,
            attached_cni_type=values["attachedCniType"], cni_master_interface=values["cniMasterInterface"])
        source = converted
    docs = loadDocuments(source)
    mappings = {}
    plan = []
    for item in manifestTools.load_images(values["imagesYaml"]):
        logical = item["name"]
        repo, tag = manifestTools.split_repo_tag(logical)
        target = values["registryPrefix"] + "/" + manifestTools.strip_prefix(logical, values["imageRegistryPrefix"])
        mappings[logical] = target
        mappings[repo + ":" + tag] = target
        context = Path(item["context"])
        if context.is_absolute():
            context = context.resolve().relative_to(Path(values["outputDir"]).resolve())
        if ".." in context.parts:
            raise ValueError("Image contexts must stay inside the compiler output")
        plan.append(dict(name=target, context=str(context)))
    targets = {item["name"] for item in plan}
    for doc in docs:
        spec = readPodSpec(doc)
        for container in spec.get("containers", []) + spec.get("initContainers", []):
            container["image"] = mappings.get(container["image"], container["image"])
            if container["image"] in targets and options["imageBuildMode"] == "fast":
                # The exact image was imported on every possible destination.
                container["imagePullPolicy"] = "IfNotPresent"
        if doc.get("kind") == "NetworkAttachmentDefinition" and values["networkBackend"] not in {"kube-ovn", "ovn"}:
            meta = doc.get("metadata", {})
            cni = json.loads(doc["spec"]["config"])
            if cni.get("type") == "macvlan":
                base = manifestTools.resolveMacvlanParent(meta, values["cniMasterInterface"],
                                                         json.loads(values["cniVlanParents"]))
                cni["master"] = manifestTools.macvlanMasterForVlan(base, manifestTools.readNadVlanId(meta))
                cni["mtu"] = int(values["cniMtu"])
                if manifestTools.readNadVlanId(meta) is not None:
                    annotations = meta.setdefault("annotations", {})
                    annotations[manifestTools.VLAN_BASE_ANNOTATION] = base
                    annotations[manifestTools.VLAN_MASTER_ANNOTATION] = cni["master"]
                doc["spec"]["config"] = json.dumps(cni)
    runtime = root / "runtime.yaml"
    writeDocuments(runtime, docs)
    (root / "image-plan.json").write_text(json.dumps(plan, indent=2))
    return values, options, deploy, root, runtime, docs, plan


def createNodeImageLists(root, docs, plan, nodes):
    """Generate preload lists using effective nodeName/hostname placement."""
    assigned = {node["name"]: set() for node in nodes}
    built = {item["name"] for item in plan}
    directory = root / "node-images"
    directory.mkdir(exist_ok=True)
    for doc in docs:
        spec = readPodSpec(doc)
        node = spec.get("nodeName") or spec.get("nodeSelector", {}).get("kubernetes.io/hostname")
        if node and node not in assigned:
            raise ValueError(f"Workload targets an unknown node: {node}")
        images = {c["image"] for c in spec.get("containers", []) + spec.get("initContainers", [])} & built
        for destination in ([node] if node else assigned):
            assigned[destination].update(images)
    for node, images in assigned.items():
        (directory / f"images_{node}.txt").write_text("\n".join(sorted(images)) + ("\n" if images else ""))
    return directory, assigned


def createAccessCommand(node):
    """Return local shell/SSH argv for an explicit setup node access record."""
    if node["connection"] == "local":
        return []
    return ["ssh", "-i", node["sshKey"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR", f"{node['sshUser']}@{node['ip']}"]


def executeNode(node, args, **kwargs):
    """Execute argv args as root on node with optional subprocess kwargs."""
    access = createAccessCommand(node)
    command = [*access, shlex.join(["sudo", "-n", *args])] if access else ["sudo", "-n", *args]
    return subprocess.run(command, check=True, **kwargs)


def buildWorkloadImages(config):
    """Build shared bases/archives and preload the exact target-node image sets."""
    values, options, deploy, root, runtime, docs, plan = createRuntimeManifest(config)
    nodes = stages.nodeAccessRecords(config)
    lists, assignments = createNodeImageLists(root, docs, plan, nodes)
    builder = dict(name="builder", ip=values["registryPrefix"].split(":")[0],
        connection=values["masterConnection"], sshUser=values["sshUser"], sshKey=values["sshKey"])
    remote = f"/tmp/seedemu-native-archive-{os.getpid()}-{time.time_ns()}"
    access = createAccessCommand(builder)
    with recordStage(root, "build-image"):
        stages.ensureBuildBaseImages(Path(values["outputDir"]), access or None)
        executeNode(builder, ["mkdir", "-p", remote + "/output", remote + "/running", remote + "/node-images"])
        if access:
            stages.streamTarToRemote(Path(values["outputDir"]), access, f"sudo -n tar -C {shlex.quote(remote+'/output')} -xzf -")
            stages.streamTarToRemote(stages.SCRIPT_DIR, access, f"sudo -n tar -C {shlex.quote(remote+'/running')} -xzf -")
        else:
            stages.copyTreeContents(Path(values["outputDir"]), Path(remote) / "output")
            stages.copyTreeContents(stages.SCRIPT_DIR, Path(remote) / "running")
        if options["imageBuildMode"] == "fast":
            print("[k8sTools] fast archive mode enabled; preserve each FROM base", flush=True)
            executeNode(builder, ["python3", remote + "/running/buildImageArchives.py",
                "--work-dir", remote + "/output", "--image-plan", remote + "/output/k8stools/image-plan.json",
                "--node-image-dir", remote + "/output/k8stools/node-images",
                "--archive-dir", remote + "/archives", "--summary", remote + "/summary.json"],
                timeout=options["imageBuildTimeoutSeconds"])
            summary = executeNode(builder, ["cat", remote + "/summary.json"], capture_output=True, text=True).stdout
            (root / "image-archives.json").write_text(summary)
        else:
            executeNode(builder, ["python3", remote + "/running/BuildRegistryImages.py",
                "--output-dir", remote + "/output", "--registry-prefix", values["registryPrefix"],
                "--image-registry-prefix", values["imageRegistryPrefix"]], timeout=options["imageBuildTimeoutSeconds"])
    with recordStage(root, "preload-image"):
        def preloadNode(node):
            """Stream only node's assigned image archive into its containerd."""
            names = assignments[node["name"]]
            if not names:
                return dict(node=node["name"], images=0)
            with (root / ("preload-" + node["name"] + ".log")).open("w") as log:
                if options["imageBuildMode"] == "fast":
                    archive = remote + "/archives/images_" + node["name"] + ".tar"
                    src = createAccessCommand(builder)
                    argv = [*src, shlex.join(["sudo", "-n", "cat", archive])] if src else ["sudo", "-n", "cat", archive]
                    producer = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=log)
                    try:
                        executeNode(node, ["k3s", "ctr", "images", "import", "-"],
                            stdin=producer.stdout, stdout=log, stderr=log, timeout=1800)
                    finally:
                        producer.stdout.close()
                        try:
                            result = producer.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            producer.terminate()
                            result = producer.wait(timeout=10)
                    if result:
                        raise RuntimeError(f"Archive stream failed for {node['name']}: {result}")
                else:
                    for name in sorted(names):
                        executeNode(node, ["k3s", "ctr", "images", "pull", "--plain-http", name],
                            stdout=log, stderr=log, timeout=300)
                actual = executeNode(node, ["k3s", "ctr", "images", "list", "-q"],
                    capture_output=True, text=True, timeout=120).stdout.splitlines()
                missing = names - set(actual)
                if missing:
                    raise RuntimeError(f"Preload missing {len(missing)} images on {node['name']}")
            print(f"[preload] {node['name']}: {len(names)} images verified", flush=True)
            return dict(node=node["name"], images=len(names))
        with ThreadPoolExecutor(max_workers=options["preloadNodeConcurrency"]) as pool:
            results = list(pool.map(preloadNode, nodes))
        # Archives are staging data. Repeated runs must not fill the builder's
        # disk; a failed build/import retains its unique directory for diagnosis.
        executeNode(builder, ["rm", "-rf", "--", remote], timeout=120)
        (root / "preload-summary.json").write_text(json.dumps(dict(status="PASS", nodes=results), indent=2))


def executeKubectl(values, *args):
    """Run finite API requests through values' explicit kubeconfig."""
    return subprocess.check_output(["kubectl", "--kubeconfig", values["kubeconfig"],
        "--request-timeout=60s", *args], text=True, timeout=120)


def waitSubnetsReady(values, docs):
    """Wait for this manifest's OVN subnets before starting dependent Pods."""
    expected = {d["metadata"]["name"] for d in docs if d.get("kind") == "Subnet"}
    if not expected:
        return
    deadline = time.monotonic() + int(values["rolloutTimeoutSeconds"])
    while time.monotonic() < deadline:
        subnets = json.loads(executeKubectl(values, "get", "subnet.kubeovn.io", "-o", "json"))["items"]
        ready = set()
        for subnet in subnets:
            name = subnet["metadata"]["name"]
            if name not in expected:
                continue
            conditions = {c["type"]: c["status"] for c in subnet.get("status", {}).get("conditions", [])}
            if conditions.get("Error") == "True":
                raise RuntimeError(f"Kube-OVN subnet reported Error: {name}")
            if conditions.get("Ready") == "True":
                ready.add(name)
        if expected <= ready:
            return
        time.sleep(5)
    raise TimeoutError("Kube-OVN subnets did not become Ready")


def waitControllerBatch(values, namespace, documents):
    """Gate scheduler-managed Deployment batches on actual startup completion."""
    expected = {d["metadata"]["name"]: d.get("spec", {}).get("replicas", 1)
                for d in documents if d.get("kind") == "Deployment"}
    deadline = time.monotonic() + int(values["rolloutTimeoutSeconds"])
    while expected and time.monotonic() < deadline:
        live = json.loads(executeKubectl(values, "get", "deployments", "-n", namespace, "-o", "json"))["items"]
        ready = {d["metadata"]["name"] for d in live
            if d["metadata"]["name"] in expected and d.get("status", {}).get("readyReplicas", 0)
            == expected[d["metadata"]["name"]]}
        if set(expected) <= ready:
            return
        time.sleep(5)
    if expected:
        raise TimeoutError("Controller batch startup timed out")


def waitWorkloadReady(config):
    """Check the full expected Deployment and Pod set with one shared poll."""
    values, options, deploy, root, runtime, docs, plan = createRuntimeManifest(config)
    expected = {d["metadata"]["name"]: int(d.get("spec", {}).get("replicas", 1))
                for d in docs if d.get("kind") == "Deployment"}
    namespace = stages.namespaceForManifest(str(runtime))
    deadline = time.monotonic() + int(values["rolloutTimeoutSeconds"])
    with recordStage(root, "wait-ready"):
        while time.monotonic() < deadline:
            deployments = json.loads(executeKubectl(values, "get", "deployments", "-n", namespace, "-o", "json"))["items"]
            ready = {d["metadata"]["name"] for d in deployments
                if d["metadata"]["name"] in expected
                and d.get("status", {}).get("observedGeneration", 0) >= d["metadata"].get("generation", 1)
                and d.get("status", {}).get("readyReplicas", 0) == expected[d["metadata"]["name"]]}
            pods = json.loads(executeKubectl(values, "get", "pods", "-n", namespace, "-o", "json"))["items"]
            good = [p for p in pods if not p["metadata"].get("deletionTimestamp")
                and any(c.get("type") == "Ready" and c.get("status") == "True" for c in p.get("status", {}).get("conditions", []))]
            print(f"[ready] deployments={len(ready)}/{len(expected)} pods={len(good)}/{sum(expected.values())}", flush=True)
            if set(expected) <= ready and len(good) >= sum(expected.values()) and len(pods) == len(good):
                (root / "readiness.json").write_text(json.dumps(dict(status="PASS", deployments=len(ready),
                    pods=len(good), restarts=sum(c.get("restartCount", 0) for p in pods
                    for c in p.get("status", {}).get("containerStatuses", []))), indent=2))
                return
            time.sleep(5)
        raise TimeoutError("Workload readiness timed out; retain namespace and k8stools artifacts")


def deployWorkload(config):
    """Prepare VLANs, create static batches, then submit bounded worker queues."""
    values, options, deploy, root, runtime, docs, plan = createRuntimeManifest(config)
    namespace = stages.namespaceForManifest(str(runtime))
    existing = json.loads(executeKubectl(values, "get", "deployments,pods", "-n", namespace, "-o", "json"))["items"]
    if existing:
        raise ValueError(f"Namespace {namespace} already has workloads; clean before up")
    stages.ensureNamespace(values["kubeconfig"], namespace)
    with recordStage(root, "prepare-vlan"):
        stages.prepareMacvlanVlanInterfaces(config, {**values, "manifest": str(runtime)})
    controllers = [d for d in docs if d.get("kind") in CONTROLLERS]
    with recordStage(root, "deploy-pod"):
        static = [d for d in docs if d.get("kind") not in CONTROLLERS | {"Namespace"}]
        for offset in range(0, len(static), deploy["subnetBatchSize"]):
            batch = root / f"static-{offset:05d}.yaml"
            writeDocuments(batch, static[offset:offset+deploy["subnetBatchSize"]])
            executeKubectl(values, "apply", "-f", str(batch))
            print(f"[static] {min(offset+deploy['subnetBatchSize'], len(static))}/{len(static)}", flush=True)
        waitSubnetsReady(values, docs)
        direct = all(d.get("kind") == "Deployment" and readPodSpec(d).get("nodeName")
                     and d.get("spec", {}).get("replicas", 1) == 1 for d in controllers)
        if direct and controllers and deploy["controllerApplyMode"] == "worker-queue":
            queueDir = root / ("worker-queue-" + str(time.time_ns()))
            tuning = root / "deploy.yaml"
            tuning.write_text(yaml.safe_dump(dict(deploy=deploy)))
            dispatchQueues(runtime, tuning, namespace, [n["name"] for n in stages.nodeAccessRecords(config)],
                queueDir, values["kubeconfig"])
        else:
            for offset in range(0, len(controllers), deploy["batchSize"]):
                batch = root / f"controllers-{offset:05d}.yaml"
                writeDocuments(batch, controllers[offset:offset+deploy["batchSize"]])
                executeKubectl(values, "apply", "-f", str(batch))
                waitControllerBatch(values, namespace, controllers[offset:offset+deploy["batchSize"]])
    waitWorkloadReady(config)
