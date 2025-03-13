import os
import json
import yaml
import sys
from seedemu.core.enums import NodeRole

class ScionOutputChecker:

    def __init__(self, out_dir='.'):
        """!
            initialisation
            @param out_dir  path to SEED compiler output
              which is to be checked (dir that contains docker-compose.yml)
        """
        self._dir = out_dir
        # the actual truth and reference
        compose = parse_docker_compose_yaml(out_dir)
        self._services = compose['services']
        self._networks = compose['networks']

        self._as_topology = {}  # dict of dicts - topology.json for each encountered AS

    def check_brdnode(self, node_name, curr_node_json_data ):

        local_ia = curr_node_json_data['isd_as']
        local_asn=local_ia.split('-')[1]
        folder = f'brdnode_{local_asn}_{node_name}'
        # also the service name of the node in docker-compose.yml
        assert folder in self._services, 'SEED output naming scheme violation'

        brd = curr_node_json_data['border_routers'][node_name]
        internal_addr = brd['internal_addr']
        interfaces = brd['interfaces']

        brd_service = self._services[folder]
        brd_nets = brd_service['networks'] # networks joined by this service

        for i, (id, intf) in enumerate(interfaces.items()):
            underlay = intf['underlay']
            remote_ia = intf['isd_as']
            remote_asn = remote_ia.split('-')[1]
            assert remote_asn != local_asn, f'SCION topology must not have self loops: check {local_ia}'
            local_key = 'local' if 'local' in underlay else 'public'
            local_ip = underlay[local_key].split(':')[0] #.rstrip(':50000')
            remote_ip = underlay['remote'].split(':')[0]

            for  (name, net) in brd_nets.items():
                if name.endswith('net0'): # local network within AS
                        ip = net['ipv4_address']
                        #net_name = name.lstrip('net_').rstrip('_net0')
                        net_name = name.split('_')[1]
                        assert net_name == local_asn, f'border router must belong to a single AS only: {net_name} {local_asn} [{name}]'
                        router_internal_ip = internal_addr.split(':')[0] #.rstrip(':30042')
                        is_loopback= 'org.seedsecuritylabs.seedemu.meta.loopback_addr' in brd_service['labels']
                        assert ip==router_internal_ip or is_loopback, f'contradiction between topology.json and docker-compose.yml detected for BR({node_name}) internal address: {name} AS {local_asn} expected: {router_internal_ip} actual: {ip}'
                if name.startswith('net_ix'):
                        ip = net['ipv4_address']
                        net_name = name.split('_')[-1].lstrip('ix')
                        assert ip == local_ip, f'contradiction between topology.json and docker-compose.yml detected: {name} net: {net_name} docker: {ip} topo.json: {local_ip}'
                        # check that remote-border-router has 'name' under 'networks'
                        # and within this network in fact has assigned the IP 'remote_ip'
                        remote_router_name = f'brdnode_{remote_asn}_router{net_name}'
                        remote_router = self._services[remote_router_name]
                        assert name in (remote_nets:=remote_router['networks']) , f'remote border router unreachable - IX: {net_name} from: {local_ia} to: {remote_ia}'
                        remote_net = remote_nets[name]
                        assert remote_net['ipv4_address'] == remote_ip  , f'contradiction between topology.json and docker-compose.yml detected for remote BR: {name} AS {remote_asn} router{net_name}'
                        pass
                pass
            pass


    def do_checks(self):
        """!
          Function to recursively find all 'topology.json' files,
          parse and validate their content against docker-compose.yml
        """

         # Iterate over the directory structure recursively
        for root, dirs, files in os.walk(self._dir):

            for file in files:

                if file == '552f01f4bf3d252f6a6c2af55d8d5bf2': # 'topology.json'

                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath( full_path, start=self._dir)
                    folder = os.path.dirname(relative_path)

                    node_role = None
                    node_name ='' # i.e. 'routerXYZ'
                    if '_' in folder:
                        match prefix:=folder.split('_')[0]:
                            case 'brdnode': node_role = NodeRole.BorderRouter
                            case 'rnode':  node_role = NodeRole.Router
                            case 'hnode':  node_role = NodeRole.Host
                            case 'rsnode': node_role =  NodeRole.RouteServer
                            case 'csnode': node_role = NodeRole.Host
                            case _:
                                print( f'directory with unknown node role: {prefix}')
                                continue # better raise exception here ?!
                    else:
                        # this directory can't be part of generated SEED output
                        #  but still contains a 'topology.json' file by coincidence
                        continue
                    node_name = folder.split('_')[-1]

                    try:
                        with open(full_path, 'r') as f:
                            curr_node_json_data = json.load(f)

                            local_ia=curr_node_json_data['isd_as']
                            local_asn=local_ia.split('-')[1]

                            assert (dir_asn:=folder.split('_')[1])==local_asn, f'misplaced topology.json file - expected: {dir_asn} actual: {local_asn}'

                            local_topo, seen = (self._as_topology[local_ia], True ) if local_ia in self._as_topology else ({ "border_routers": {}, "isd_as": local_ia }, False)

                            json_routers = curr_node_json_data['border_routers']

                            if not seen: # then update the list of this AS's BRs, so we can check that all nodes of the AS have the same list
                                local_topo['border_routers'] = json_routers
                                self._as_topology[local_ia] = local_topo
                            else:
                                # assert that all nodes of an AS have the same 'topology.json' file

                                # for now check that deepdiff of 'routers' and local_topo['border_routers'] is zero
                                assert local_topo['border_routers'] == json_routers , f'deviating topology.json files detected: {local_ia}'

                            if node_role == NodeRole.BorderRouter:
                                self.check_brdnode(node_name, curr_node_json_data )

                    except Exception as e:
                       print(f"Error reading topology.json {full_path}: {e}")
        print('No errors detected')


def parse_docker_compose_yaml(dir='.',file_path='docker-compose.yml'):
    full_path = os.path.join(dir, file_path)
    if os.path.exists(full_path):

        try:
            with open(full_path, 'r') as file:
                yaml_content = yaml.safe_load(file)
                return yaml_content

        except yaml.YAMLError as e:
            print(f"Error decoding YAML from {file_path}: {e}")
        except Exception as e:
            print(f"Error reading docker-compose.yml {file_path}: {e}")
    else:
        print(f"{file_path} does not exist.")



if __name__ == "__main__":

    sn = ScionOutputChecker(out_dir=sys.argv[1])

    sn.do_checks()