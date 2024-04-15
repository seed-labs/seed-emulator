#!/usr/bin/env python3

import argparse
import json
import re
import os
import subprocess
import requests
import docker
from faucetconfrpc.faucetconfrpc_client_lib import FaucetConfRpcClient
from graphviz import Digraph


class GraphDovesnapException(Exception):
    pass


class GraphDovesnap:

    DOVESNAP_NAME = 'dovesnap-plugin'
    OFP_LOCAL = 4294967294
    DOCKER_URL = 'unix://var/run/docker.sock'
    VM_PREFIX = 'vnet'
    MIRROR_PREFIX = 'odsmir'
    DOVESNAP_MIRROR = '99'

    def __init__(self, args):
        self.args = args

    def _get_named_container(self, client, name, strict=True):
        for container in client.containers(filters={'name': name}):
            if not strict:
                return container
            for container_name in container['Names']:
                if name in container_name:
                    return container
        return None

    def _get_named_container_hi(self, client_hi, name, strict=True):
        for container in client_hi.containers.list(filters={'name': name}):
            if not strict:
                return container
            if container.name == name:
                return container
        return None

    def _scrape_container_cmd(self, name, cmd, strict=True):
        client_hi = docker.DockerClient(base_url=self.DOCKER_URL)
        container = self._get_named_container_hi(client_hi, name, strict=strict)
        if container:
            try:
                (dump_exit, output) = container.exec_run(cmd)
                if dump_exit == 0:
                    return output.decode('utf-8').splitlines()
            except subprocess.CalledProcessError:
                pass
        return None

    def _scrape_cmd(self, cmd):
        try:
            output = subprocess.check_output(cmd)
            return output.decode('utf-8').splitlines()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _get_vm_options(self, faucet_conf, network, ofport):
        vm_options = []
        interfaces = faucet_conf['dps'][network]['interfaces']
        interface = interfaces[ofport]
        acls_in = interface.get('acls_in', None)
        if acls_in:
            vm_options.append('portacl: %s' % ','.join(acls_in))
        mirror_interface = interfaces.get(self.DOVESNAP_MIRROR, None)
        if mirror_interface:
            mirrored_ports = mirror_interface.get('mirror', [])
            if ofport in mirrored_ports:
                vm_options.append('mirror: true')
        return '\n'.join(vm_options)

    def _network_lookup(self, name):
        output = self._scrape_cmd(['nslookup', name])
        if output:
            hostname, address = output[4:-1]
            hostname = hostname.split('\t')[1]
            address = address.split(': ')[1]
            return hostname, address
        return None, None

    def _scrape_vm_iface(self, name):
        desc = ['', 'Virtual Machine', name]
        output = self._scrape_cmd(['virsh', 'list'])
        if output:
            vm_names = output[2:-1]
            for vm_list in vm_names:
                vm_name = vm_list.split()[1]
                vm_iflist = self._scrape_cmd(['virsh', 'domiflist', vm_name])
                ifaces = vm_iflist[2:-1]
                iface_macs = {iface.split()[0]: iface.split()[4] for iface in ifaces}
                mac = iface_macs.get(name, None)
                if mac is not None:
                    desc.append(mac)
                    hostname, address = self._network_lookup(vm_name)
                    if hostname is not None:
                        desc.insert(0, hostname)
                        desc.append(f'{address}/24')
                    break
        return '\n'.join(desc)

    def _get_matching_lines(self, lines, re_str):
        match_re = re.compile(re_str)
        matching_lines = []
        for line in lines:
            match = match_re.match(line)
            if match:
                matching_lines.append(match)
        return matching_lines

    def _get_container_args(self, container_inspect):
        args = {}
        for arg_str in container_inspect['Config']['Cmd']:
            arg_str = arg_str.lstrip('-')
            arg_l = arg_str.split('=')
            if len(arg_l) > 1:
                args[arg_l[0]] = arg_l[1]
            else:
                args[arg_l[0]] = ""
        return args

    def output_graph(self, nodes, edges):
        dot = Digraph()
        for node, node_labels in nodes.items():
            dot.node(node, '\n'.join(node_labels))
        for edge_a, edge_b, edge_ports in edges:
            edge_label = ' : '.join([str(port) for port in edge_ports])
            dot.edge(edge_a, edge_b, edge_label)
        dot.format = 'png'
        dot.render(self.args.output)
        # leave only PNG
        os.remove(self.args.output)

    def _format_labels(self, labels):
        return ['%s: %s' % (label.split('.')[-1], labelval) for label, labelval in labels.items()]

    def _scrape_network_options(self, client, network_id):
        network_inspect = client.inspect_network(network_id)
        return self._format_labels(network_inspect['Options'])

    def build_graph(self):
        networks_json = {}
        for status_addr in self.args.status_addrs.split(','):
            status_url = 'http://%s/networks' % status_addr
            resp = requests.get(status_url)
            networks_json.update(json.loads(resp.text))
        client = docker.APIClient(base_url=self.DOCKER_URL)
        if not client.ping():
            raise GraphDovesnapException('cannot connect to docker')
        dovesnap = self._get_named_container(client, self.DOVESNAP_NAME)
        if not dovesnap:
            raise GraphDovesnapException('cannot find dovesnap container')
        faucetconfrpc_client = FaucetConfRpcClient(
            self.args.key, self.args.cert, self.args.ca, ':'.join([self.args.server, self.args.port]))
        if not faucetconfrpc_client:
            raise GraphDovesnapException('cannot connect to faucetconfrpc')
        faucet_conf = faucetconfrpc_client.get_config_file()
        dovesnap_args = self._get_container_args(client.inspect_container(dovesnap['Id']))
        nodes = {}
        edges = []
        network_name_id = {}

        for network_id, network in networks_json.items():
            network_name = network['NetworkName']
            bridgename = network['BridgeName']
            mode = network['Mode']
            try:
                options = self._scrape_network_options(client, network_id + 'x')
            except docker.errors.NotFound:
                # TODO: assume remote docker, fall back to TCP URL
                options = []
            nodes[network_id] = [network_name, bridgename] + options
            dynamic_state = network['DynamicNetworkStates']
            engine_id = dynamic_state['ShortEngineId']
            network_name_id[network_name] = network_id
            for container in dynamic_state['Containers'].values():
                container_id = container['Id']
                container_name = container['Name']
                labels = container['Labels']
                ifname = container['IfName']
                macaddress = container['MacAddress']
                ofport = container['OFPort']
                ip = container.get('HostIP', None)
                host_label = [container_name, '', 'Container', ifname, macaddress]
                if ip:
                    host_label.append(ip)
                host_label.extend(self._format_labels(labels))
                nodes[container_id] = host_label
                edges.append((network_id, container_id, [ofport]))
            for extifname, extif in dynamic_state['ExternalPorts'].items():
                extifname = ' '.join((engine_id, extifname))
                ofport = extif['OFPort']
                if ofport == self.OFP_LOCAL:
                    if mode == 'nat':
                        edges.append((network_id, 'NAT', [self.OFP_LOCAL]))
                else:
                    # TODO: Move VM inspection inside dovesnap so can work across hosts.
                    if extifname.startswith(self.VM_PREFIX):
                        vm_desc = self._scrape_vm_iface(extifname)
                        vm_options = self._get_vm_options(
                            faucet_conf, network['Name'], ofport)
                        nodes[extifname] = ['', vm_desc, vm_options]
                    else:
                        macaddress = extif['MacAddress']
                        nodes[extifname] = '\n'.join((extifname, '', 'External Interface', macaddress))
                    edges.append((network_id, extifname, [ofport]))
            for otherbrif in dynamic_state['OtherBridgePorts'].values():
                ofport = otherbrif['OFPort']
                peer_ofport = otherbrif['PeerOFPort']
                peer_bridgename = otherbrif['PeerBridgeName']
                edges.append((network_id, peer_bridgename, [ofport, peer_ofport]))
                if peer_bridgename.startswith(self.MIRROR_PREFIX) and peer_bridgename not in nodes:
                    nodes[peer_bridgename] = ['mirror bridge', peer_bridgename]
                    mirror_in = dovesnap_args.get('mirror_bridge_in', None)
                    mirror_out = dovesnap_args.get('mirror_bridge_out', None)
                    if mirror_in:
                        edges.append((' '.join((engine_id, mirror_in)), peer_bridgename, [mirror_in]))
                    if mirror_out:
                        edges.append((peer_bridgename, ' '.join((engine_id, mirror_out)), [mirror_out]))
            if faucet_conf:
                stack_links = set()
                for dp, dp_conf in faucet_conf.get('dps', {}).items():
                    network_id = network_name_id.get(dp, None)
                    if network_id:
                        continue
                    for interface, interface_conf in dp_conf.get('interfaces', {}).items():
                        stack_conf = interface_conf.get('stack', None)
                        if stack_conf:
                            stack_dp = stack_conf['dp']
                            stack_port = stack_conf['port']
                            peer_network_id = network_name_id.get(stack_dp, stack_dp)
                            if peer_network_id in nodes:
                                continue
                            stack_key = tuple(sorted([str(i) for i in (interface, stack_port, dp, peer_network_id)]))
                            if stack_key in stack_links:
                                continue
                            stack_links.add(stack_key)
                            edges.append((dp, peer_network_id, [interface, stack_port]))

        self.output_graph(nodes, edges)


def main():
    parser = argparse.ArgumentParser(
        description='Dovesnap Graph - A dot file output graph of VMs, containers, and networks controlled by Dovesnap')
    parser.add_argument('--ca', '-a', default='/opt/faucetconfrpc/faucetconfrpc-ca.crt',
                        help='FaucetConfRPC server certificate authority file')
    parser.add_argument('--cert', '-c', default='/opt/faucetconfrpc/faucetconfrpc.crt',
                        help='FaucetConfRPC server cert file')
    parser.add_argument('--key', '-k', default='/opt/faucetconfrpc/faucetconfrpc.key',
                        help='FaucetConfRPC server key file')
    parser.add_argument('--port', '-p', default='59999',
                        help='FaucetConfRPC server port')
    parser.add_argument('--server', '-s', default='faucetconfrpc',
                        help='FaucetConfRPC server name')
    parser.add_argument('--output', '-o', default='dovesnapviz',
                        help='Output basename of image to write')
    parser.add_argument('--status_addrs', '-u', default='localhost:9401',
                        help='Command separated list of dovesnap status URLs to scrape')
    args = parser.parse_args()
    g = GraphDovesnap(args)
    g.build_graph()


if __name__ == "__main__":
    main()
