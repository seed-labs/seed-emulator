#!/usr/bin/env python3
"""Read-only comparison of a native deployment with a frozen reference run.

Inputs: --output-dir, --config-k3s, --kubeconfig, --reference-run and --report.
Reads workload/node APIs, worker VLAN links and BIRD process state over SSH;
writes JSON evidence and a comparison report. Does not start routing, change
interfaces, alter Pods, or import executable code from the reference directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess

import ManageK8sManifest as manifestTools
import manageWorkload as workloadTools


NODE_AUDIT = r'''
import hashlib,json,subprocess,sys
from pathlib import Path
value=json.load(sys.stdin)
links=json.loads(subprocess.check_output(['ip','-j','-d','link','show'],text=True))
by_name={link['ifname']:link for link in links}
failures=[]
for row in value['vlans']:
    iface,base,vlan=row
    link=by_name.get(iface,{})
    data=link.get('linkinfo',{}).get('info_data',{})
    if data.get('id')!=int(vlan) or 'UP' not in link.get('flags',[]):
        failures.append(dict(interface=iface,reason='missing, wrong VLAN or down'))
    parent_matches = (link['link']==base if 'link' in link else
                      link.get('link_index')==by_name.get(base,{}).get('ifindex'))
    if not parent_matches:
        failures.append(dict(interface=iface,reason='wrong parent'))
birds={}
for proc in Path('/proc').glob('[0-9]*'):
    try:
        if (proc/'comm').read_text().strip()=='bird':
            raw=(proc/'cgroup').read_text()
            for row in value['containers']:
                if row['cid'] in raw:birds[row['app']]=int(proc.name)
    except (FileNotFoundError,ProcessLookupError):pass
binary=None
if value['containers']:
    row=value['containers'][0]
    pid=Path('/run/k3s/containerd/io.containerd.runtime.v2.task/k8s.io',row['cid'],'init.pid').read_text().strip()
    root=Path('/proc',pid,'root')
    binary=hashlib.sha256((root/'usr/sbin/bird').read_bytes()).hexdigest()
    version=subprocess.check_output(['nsenter','-t',pid,'-m','-u','-i','-n','-p','--','/usr/sbin/bird','--version'],stderr=subprocess.STDOUT,text=True).strip()
else:version=None
print(json.dumps(dict(load1=float(Path('/proc/loadavg').read_text().split()[0]),expectedVlans=len(value['vlans']),vlanFailures=failures,birdProcesses=birds,binarySha256=binary,binaryVersion=version)))
'''


def readWorkerSuffix(name: str) -> str:
    """Normalize a reference/current node name to its worker number."""
    match = re.search(r"worker(\d+)$", name)
    return match[1] if match else name


def validateDeployment(output: Path, setup: Path, kubeconfig: Path, reference: Path, report: Path) -> dict:
    """Compare output's live workload with reference using setup/kubeconfig; write report."""
    report.parent.mkdir(parents=True, exist_ok=True)
    state = manifestTools.load_yaml(str(setup))
    docs = workloadTools.loadDocuments(output/"k8stools/runtime.yaml")
    expected = {doc['metadata']['name']: doc['spec']['template']['spec']
                for doc in docs if doc.get('kind') == 'Deployment'}
    expected_annotations = {doc['metadata']['name']:doc['spec']['template'].get('metadata',{}).get('annotations',{})
                            for doc in docs if doc.get('kind') == 'Deployment'}
    namespace = next(doc['metadata']['namespace'] for doc in docs if doc.get('kind') == 'Deployment')
    raw = subprocess.check_output(['kubectl','--kubeconfig',str(kubeconfig),'--request-timeout=120s',
        '-n',namespace,'get','pods','-o','json'],text=True,timeout=150)
    (report.parent/'pods.json').write_text(raw)
    pods = json.loads(raw)['items']
    by_app = {}
    errors = []
    for pod in pods:
        app = pod['metadata'].get('labels',{}).get('app')
        if app not in expected or app in by_app:
            errors.append(f'foreign or duplicate Pod: {app}')
            continue
        by_app[app] = pod
        statuses = pod.get('status',{}).get('containerStatuses',[])
        if not statuses or any(not c.get('ready') or c.get('restartCount',0) for c in statuses):
            errors.append(f'not Ready or restarted: {app}')
        if pod['spec'].get('nodeName') != expected[app].get('nodeName'):
            errors.append(f'wrong node: {app}')
        annotations = pod['metadata'].get('annotations',{})
        requested = json.loads(expected_annotations[app].get('k8s.v1.cni.cncf.io/networks','[]'))
        attached = json.loads(annotations.get('k8s.v1.cni.cncf.io/network-status','[]'))
        actual_networks = {network['name'].rsplit('/',1)[-1]:set(network.get('ips',[]))
                           for network in attached if network.get('name')}
        for network in requested:
            name = network['name'].rsplit('/',1)[-1]
            addresses = {address.split('/',1)[0] for address in network.get('ips',[])}
            if name not in actual_networks or addresses != actual_networks[name]:
                errors.append(f'Multus attachment/IP differs: {app}/{name}')
        for field in ('image','resources','command'):
            if pod['spec']['containers'][0].get(field) != expected[app]['containers'][0].get(field):
                errors.append(f'container {field} differs: {app}')
    errors.extend('missing Pod: '+app for app in set(expected)-set(by_app))
    old = json.loads((reference/'partitionResult.json').read_text())['mapping']
    mapping_diff = [app for app,spec in expected.items()
                    if readWorkerSuffix(spec['nodeName']) != readWorkerSuffix(old.get(app,''))]
    rows = io.StringIO()
    with redirect_stdout(rows):
        manifestTools.macvlan_vlan_interfaces_by_node(argparse.Namespace(
            manifest=str(output/'k8stools/runtime.yaml'),cni_master_interface='ens3',
            nodes=[node['name'] for node in state['nodes']]))
    vlan_rows = {}
    for line in rows.getvalue().splitlines():
        node,iface,base,vlan,*_ = line.split('\t')
        vlan_rows.setdefault(node,[]).append([iface,base,vlan])
    access = {row['name']:row for row in manifestTools.resolvedSetupNodes(state)}
    def auditNode(node):
        """Read only node's planned VLAN interfaces, owned BIRD processes and binary."""
        name = node['name']
        containers = [dict(app=app,cid=pod['status']['containerStatuses'][0]['containerID'].split('://',1)[1])
                      for app,pod in by_app.items() if pod['spec']['nodeName']==name]
        target = access[name]
        command = workloadTools.createAccessCommand(target)
        remote = shlex.join(['sudo','-n','python3','-c',NODE_AUDIT])
        argv = [*command,remote] if command else ['sudo','-n','python3','-c',NODE_AUDIT]
        result = subprocess.run(argv,input=json.dumps(dict(containers=containers,vlans=vlan_rows.get(name,[]))),
            text=True,capture_output=True,check=True,timeout=180)
        value = json.loads(result.stdout)
        (report.parent/(name+'.json')).write_text(json.dumps(value,indent=2))
        return dict(node=name,**value)
    with ThreadPoolExecutor(max_workers=9) as pool:
        workers = list(pool.map(auditNode,state['nodes']))
    errors.extend(f"VLAN mismatch: {row['node']}" for row in workers if row['vlanFailures'])
    policy_path = reference/'runtimeImagePolicy.json'
    if policy_path.is_file():
        policy = json.loads(policy_path.read_text())['binaryPolicy']
        for row in workers:
            if row['binarySha256'] is not None and (row['binarySha256'] != policy['binaries']['bird']
                    or row['binaryVersion'] != policy['version']):
                errors.append(f"BIRD binary differs: {row['node']}")
    bird_count = sum(len(row['birdProcesses']) for row in workers)
    result = dict(deploymentPassed=not errors and not mapping_diff,workloads=len(expected),pods=len(pods),
        counts=dict(Counter(pod['spec']['nodeName'] for pod in pods)),errors=errors,
        referenceMappingMatches=not mapping_diff,mappingDifferences=len(mapping_diff),
        networkAttachmentsChecked=sum(len(json.loads(pod['metadata'].get('annotations',{}).get(
            'k8s.v1.cni.cncf.io/networks','[]'))) for pod in pods),
        vlanParents=sum(row['expectedVlans'] for row in workers),workerAudits=workers,
        birdProcesses=bird_count,routingStarted=bird_count==len(expected),
        routingEquivalentToCompletedB63=False if bird_count<len(expected) else None,
        routingValidationScope='Owned BIRD processes and sampled binaries only; protocols, FIB and traffic are not verified.',
        note='Native up ends at Pod readiness. Frozen B63 entrypoints defer BIRD until explicit start/kernel stages. Running processes alone cannot prove routing equivalence.')
    report.write_text(json.dumps(result,indent=2))
    if errors or mapping_diff:
        raise ValueError(f'Deployment differs; see {report}')
    return result


def main() -> int:
    """Parse explicit file paths and execute the read-only deployment comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['output-dir','config-k3s','kubeconfig','reference-run','report']:
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    result = validateDeployment(args.output_dir,args.config_k3s,args.kubeconfig,args.reference_run,args.report)
    print(json.dumps({key:result[key] for key in ['deploymentPassed','workloads','pods','referenceMappingMatches','vlanParents','birdProcesses','routingStarted']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
