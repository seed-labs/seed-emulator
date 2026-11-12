#!/usr/bin/env python3
"""Submit single-replica, nodeName-bound Deployments through independent queues.

Inputs: manifest, assignment YAML, allowed nodes and kubectl's current context.
Creates only the supplied Deployments in the specified namespace; never binds
through the scheduler or changes nodes. Writes submissions, API receipts and a
gate journal below a new output directory. Invoked by deploy.sh after image,
VLAN and namespace preparation. A shared Pod observation reduces API traffic;
each worker's admission decision uses only its own outstanding startup work.
"""
import argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import time

import yaml


def readQueues(manifest, nodes, namespace):
    """Read manifest's direct-bound, unique one-replica Deployments for nodes."""
    queues = defaultdict(deque)
    names = set()
    for doc in yaml.load_all(manifest.read_text(), Loader=yaml.CSafeLoader):
        if not doc:
            continue
        if doc.get('kind') in {'Pod', 'Job', 'DaemonSet', 'StatefulSet'}:
            raise ValueError('worker-queue requires single-replica Deployments')
        if doc.get('kind') != 'Deployment':
            continue
        meta, template = doc['metadata'], doc['spec']['template']
        name, spec = meta['name'], template['spec']
        node = spec.get('nodeName')
        if (node not in nodes or spec.get('nodeSelector') or
                doc['spec'].get('replicas', 1) != 1 or
                meta.get('namespace', namespace) != namespace or name in names or
                template['metadata'].get('labels', {}).get('app') != name or
                doc['spec']['selector'].get('matchLabels', {}).get('app') != name):
            raise ValueError('Invalid direct-bound deployment: ' + name)
        names.add(name)
        queues[node].append(doc)
    if not names:
        raise ValueError('No directly bound Deployments in manifest')
    return dict(queues)


def readTuning(assignment):
    """Validate assignment's worker-only gates; global batch limits do not apply."""
    config = yaml.safe_load(assignment.read_text()).get('deploy', {})
    result = {}
    for key, default in [('workerMaxInFlight', 4), ('workerConcurrencyCeiling', 64), ('workerPollSeconds', 2),
                         ('workerStartupTimeoutSeconds', 600)]:
        value = config.get(key, default)
        if type(value) is not int or value <= 0:
            raise ValueError('deploy.' + key + ' must be a positive integer')
        result[key] = value
    result['workerConcurrencyMode'] = config.get('workerConcurrencyMode', 'fixed')
    if result['workerConcurrencyMode'] not in {'fixed', 'resource'}:
        raise ValueError('deploy.workerConcurrencyMode must be fixed or resource')
    for key, default in [('workerCpuPerStartup', 0.5), ('workerMemoryGiBPerStartup', 1),
                         ('workerReservedCpu', 1), ('workerReservedMemoryGiB', 2)]:
        value = config.get(key, default)
        if isinstance(value, bool):
            raise ValueError('deploy.' + key + ' must be numeric')
        try:
            number = Fraction(str(value))
        except (ValueError, ZeroDivisionError) as error:
            raise ValueError('deploy.' + key + ' must be finite numeric') from error
        if number < 0 or ('PerStartup' in key and number == 0):
            raise ValueError('deploy.' + key + ' is outside its allowed range')
        result[key] = value
    return result


def parseQuantity(value):
    """Parse Node allocatable CPU/memory SI quantities without floating rounding."""
    match = re.fullmatch(r'([+]?(?:\d+(?:\.\d*)?|\.\d+))(Ki|Mi|Gi|Ti|Pi|Ei|n|u|m|k|K|M|G|T|P|E|[eE][+-]?\d+)?', str(value))
    if not match:
        raise ValueError('Invalid nonnegative allocatable quantity: ' + str(value))
    suffix = match[2] or ''
    decimal = {'':0, 'n':-9, 'u':-6, 'm':-3, 'k':3, 'K':3, 'M':6, 'G':9, 'T':12, 'P':15, 'E':18}
    binary = {'Ki':10, 'Mi':20, 'Gi':30, 'Ti':40, 'Pi':50, 'Ei':60}
    factor = (Fraction(10)**decimal[suffix] if suffix in decimal else
              Fraction(2)**binary[suffix] if suffix in binary else Fraction(10)**int(suffix[1:]))
    return Fraction(match[1]) * factor


def calculateWorkerLimits(nodes, tuning, inventory):
    """Compute nodes' static startup windows from tuning and live Node inventory.

    Resource weights describe deployment pacing, not Pod requests or measured
    startup demand. Allocatable minus explicit reserves is a capacity heuristic;
    this does not subtract dynamically consumed memory or guarantee no OOM.
    Reject capacity below one slot instead of silently exceeding that budget.
    """
    if tuning['workerConcurrencyMode'] == 'fixed':
        return {n: dict(limit=tuning['workerMaxInFlight'], mode='fixed') for n in nodes}
    records = {n['metadata']['name']: n for n in inventory['items']}
    result = {}
    for name in nodes:
        node = records[name]
        if (node.get('spec', {}).get('unschedulable') or not any(
                c['type'] == 'Ready' and c['status'] == 'True' for c in node['status']['conditions'])):
            raise ValueError('Resource gate requires a Ready schedulable worker: ' + name)
        alloc = node['status']['allocatable']
        cpu = parseQuantity(alloc['cpu'])
        memoryGiB = parseQuantity(alloc['memory']) / 2**30
        cpuSlots = int((cpu - Fraction(str(tuning['workerReservedCpu']))) // Fraction(str(tuning['workerCpuPerStartup'])))
        memorySlots = int((memoryGiB - Fraction(str(tuning['workerReservedMemoryGiB']))) // Fraction(str(tuning['workerMemoryGiBPerStartup'])))
        limit = min(cpuSlots, memorySlots, tuning['workerConcurrencyCeiling'])
        if limit < 1:
            raise ValueError('Insufficient capacity for one startup slot: ' + name)
        result[name] = dict(mode='resource', limit=limit, allocatable=alloc,
            allocatableCpu=str(cpu), allocatableMemoryGiB=str(memoryGiB),
            cpuSlots=cpuSlots, memorySlots=memorySlots)
    return result


def checkStarted(pod):
    """Count pod as started only after every regular container is running."""
    status = pod.get('status', {})
    states = status.get('containerStatuses', [])
    return (not pod['metadata'].get('deletionTimestamp') and
            status.get('phase') == 'Running' and
            len(states) == len(pod['spec'].get('containers', [])) > 0 and
            all('running' in s.get('state', {}) for s in states))


@dataclass
class WorkerQueue:
    """Own one node's queue and reservations, including Pods not yet created."""
    node: str
    queue: deque
    submitted: dict = field(default_factory=dict)
    future: object = None
    error: str = ''
    maxReserved: int = 0

    def inspectPressure(self, pods, now, timeout):
        """Read only this worker's submitted apps in pods at now; enforce timeout."""
        active, started, unobserved = [], [], []
        for name, submittedAt in self.submitted.items():
            matches = pods.get(name, [])
            if len(matches) > 1:
                raise ValueError('Multiple Pods for one reserved deployment: ' + name)
            if matches:
                pod = matches[0]
                if pod['spec'].get('nodeName') != self.node:
                    raise ValueError('Pod does not match direct placement: ' + name)
                if pod.get('status', {}).get('phase') in {'Failed', 'Succeeded'}:
                    raise RuntimeError('Unexpected terminal Pod: ' + name)
                if checkStarted(pod):
                    started.append(name)
                    continue
            else:
                unobserved.append(name)
            active.append(name)
            if now - submittedAt > timeout:
                raise TimeoutError('Startup reservation timed out: ' + name)
        return dict(active=active, started=started, unobserved=unobserved)

    def reserveWork(self, active, limit, now):
        """Reserve up to limit minus active slots before submitting any API request."""
        selected = []
        while self.queue and len(active) + len(selected) < limit:
            doc = self.queue.popleft()
            name = doc['metadata']['name']
            self.submitted[name] = now
            selected.append(doc)
        self.maxReserved = max(self.maxReserved, len(active) + len(selected))
        return selected


def executeKubectl(prefix, args, output, timeout=90):
    """Execute bounded API args; preserve stdout, stderr and actual exit at output."""
    argv = prefix + args
    receipt = dict(argv=argv, started=time.time())
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        stdout, stderr = result.stdout, result.stderr
        receipt.update(returnCode=result.returncode, timedOut=False)
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b''
        stderr = error.stderr or b''
        stdout = stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
        receipt.update(returnCode=None, timedOut=True)
    receipt['finished'] = time.time()
    output.with_suffix('.stdout').write_text(stdout)
    output.with_suffix('.stderr').write_text(stderr)
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2))
    if receipt['returnCode'] != 0:
        raise RuntimeError('API operation failed; retained ' + str(output))
    return stdout


def dispatchQueues(manifest, assignment, namespace, nodes, output, kubeconfig=None):
    """Dispatch supplied workloads with independent gates, retaining all evidence."""
    queues = readQueues(manifest, set(nodes), namespace)
    tuning = readTuning(assignment)
    poll, timeout = (tuning[k] for k in ('workerPollSeconds', 'workerStartupTimeoutSeconds'))
    output.mkdir(parents=True, exist_ok=False)
    (output/'tuning.json').write_text(json.dumps(tuning, indent=2))
    prefix = ['kubectl', '--request-timeout=60s']
    if kubeconfig:
        prefix += ['--kubeconfig', str(kubeconfig)]
    prefix += ['-n', namespace]
    workers = {n: WorkerQueue(n, q) for n, q in sorted(queues.items())}
    total = sum(len(w.queue) for w in workers.values())
    began = time.time()
    sequence = 0
    observationIndex = 0
    journal = (output/'gates.jsonl').open('x', buffering=1)

    def recordEvent(kind, **fields):
        """Append timestamped decision fields to this dispatch's journal."""
        journal.write(json.dumps(dict(time=time.time(), event=kind,
                                      observationIndex=observationIndex, **fields)) + '\n')

    try:
        existing = json.loads(executeKubectl(prefix, ['get', 'deployments,pods', '-o', 'json'], output/'initial'))
        if existing['items']:
            raise ValueError('worker-queue requires a fresh workload namespace; no automatic replay')
        inventory = (json.loads(executeKubectl(prefix, ['get', 'nodes', '-o', 'json'], output/'nodes'))
                     if tuning['workerConcurrencyMode'] == 'resource' else None)
        capacity = calculateWorkerLimits(workers, tuning, inventory)
        limits = {n: row['limit'] for n, row in capacity.items()}
        (output/'workerLimits.json').write_text(json.dumps(capacity, indent=2))
        print('[worker-limits]', json.dumps(limits), flush=True)
        latestPods = {}
        nextPoll = 0
        nextReport = 0
        lastSnapshot = None
        with ThreadPoolExecutor(max_workers=len(workers)) as pool:
            while True:
                now = time.time()
                if now >= nextPoll:
                    # One read shared by all workers; failed observations never
                    # mean zero pressure. Keep the last full snapshot and journal
                    # compact per-worker decisions instead of duplicating 5k Pods.
                    raw = executeKubectl(prefix, ['get', 'pods', '-o', 'json'], output/'observation')
                    lastSnapshot = json.loads(raw)
                    observationIndex += 1
                    latestPods = defaultdict(list)
                    for pod in lastSnapshot['items']:
                        name = pod['metadata'].get('labels', {}).get('app')
                        latestPods[name].append(pod)
                    now = time.time()
                    nextPoll = now + poll
                unfinished = 0
                states = {}
                for node, worker in workers.items():
                    limit = limits[node]
                    if worker.future is not None and worker.future.done():
                        try:
                            worker.future.result()
                        except Exception as error:
                            worker.error = repr(error)
                            recordEvent('worker-failed', node=node, error=worker.error)
                        worker.future = None
                    if worker.error:
                        states[node] = dict(error=worker.error)
                        continue
                    try:
                        pressure = worker.inspectPressure(latestPods, now, timeout)
                    except Exception as error:
                        worker.error = repr(error)
                        recordEvent('worker-failed', node=node, error=worker.error)
                        states[node] = dict(error=worker.error)
                        continue
                    active = pressure['active']
                    states[node] = dict(limit=limit, active=len(active), started=len(pressure['started']),
                                        activeBefore=len(active), remainingBefore=len(worker.queue),
                                        remaining=len(worker.queue), unobserved=len(pressure['unobserved']))
                    if worker.queue or active or worker.future is not None:
                        unfinished += 1
                    if worker.future is None:
                        selected = worker.reserveWork(active, limit, now)
                        if selected:
                            sequence += 1
                            stem = output/f'submit-{sequence:05d}-{node}'
                            manifestPath = stem.with_suffix('.json')
                            manifestPath.write_text(json.dumps(dict(apiVersion='v1', kind='List', items=selected)))
                            recordEvent('submit', node=node, activeBefore=active,
                                unobservedBefore=pressure['unobserved'],
                                apps=[d['metadata']['name'] for d in selected],
                                reservedAfter=len(active)+len(selected), limit=limit,
                                receipt=str(stem.with_suffix('.receipt.json')))
                            worker.future = pool.submit(executeKubectl, prefix,
                                ['create', '-f', str(manifestPath)], stem)
                            states[node].update(active=len(active)+len(selected),
                                remaining=len(worker.queue),
                                unobserved=len(pressure['unobserved'])+len(selected))
                if now >= nextReport or unfinished == 0:
                    recordEvent('snapshot', workers=states)
                    print('[worker-queue]', json.dumps(dict(elapsed=round(now-began, 1),
                        submitted=sum(len(w.submitted) for w in workers.values()), total=total,
                        workers=states)), flush=True)
                    nextReport = now + poll
                if unfinished == 0:
                    break
                time.sleep(0.1)
        failures = {n: w.error for n, w in workers.items() if w.error}
        summary = dict(passed=not failures, total=total, workers=len(workers),
            durationSeconds=time.time()-began, failures=failures,
            submitted=sum(len(w.submitted) for w in workers.values()),
            maxReservedByWorker={n:w.maxReserved for n,w in workers.items()},
            limitsByWorker=limits,
            directNodeName=True, globalPressureGate=False, tuning=tuning)
        (output/'summary.json').write_text(json.dumps(summary, indent=2))
        (output/'pods.final.json').write_text(json.dumps(lastSnapshot, indent=2))
        if failures:
            raise RuntimeError('One or more worker queues failed: ' + json.dumps(failures))
        return summary
    except BaseException as error:
        (output/'failure.json').write_text(json.dumps(dict(error=repr(error), time=time.time()), indent=2))
        raise
    finally:
        journal.close()


def executeCli():
    """Read explicit CLI paths; tuning comes exclusively from assignment YAML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--assignment', type=Path, required=True)
    parser.add_argument('--kubeconfig', type=Path)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--nodes', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dispatchQueues(args.manifest, args.assignment, args.namespace, args.nodes, args.output, args.kubeconfig)


if __name__ == '__main__':
    executeCli()
