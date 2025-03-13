import os
import json
import yaml
from typing import Optional
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
        local_asn = local_ia.split('-')[1]
        folder = f'brdnode_{local_asn}_{node_name}'
        # also the service name of the node in docker-compose.yml
        assert folder in self._services, f'SEED output naming scheme violation: {folder}'

        brd = curr_node_json_data['border_routers'][node_name]
        internal_addr = brd['internal_addr'] # address on local network 'net0'
        interfaces = brd['interfaces']

        brd_service = self._services[folder]
        brd_nets = brd_service['networks'] # networks joined by this service
        hits = {} # map interfaces from .json to networks from .yml
        for i, (id, intf) in enumerate(interfaces.items()):
            underlay = intf['underlay']
            remote_ia = intf['isd_as']
            remote_asn = remote_ia.split('-')[1]
            assert remote_asn != local_asn, f'SCION topology must not have self loops: check {local_ia}'
            local_key = 'local' if 'local' in underlay else 'public'
            local_ip = underlay[local_key].split(':')[0] #.rstrip(':50000')
            remote_ip = underlay['remote'].split(':')[0]
            found_net = False
            # find the net for the given interface
            for  (name, net) in brd_nets.items():
                ip = net['ipv4_address']
                # TODO: account for more than one local net i.e. 'net1'
                if name.endswith('net0'): # local network within AS

                        #net_name = name.lstrip('net_').rstrip('_net0')
                        asn_name = name.split('_')[1]
                        assert asn_name == local_asn, f'border router must belong to a single AS only: {asn_name} {local_asn} [{name}]'
                        router_internal_ip = internal_addr.split(':')[0] #.rstrip(':30042')
                        is_loopback= 'org.seedsecuritylabs.seedemu.meta.loopback_addr' in brd_service['labels']
                        if ip==router_internal_ip or is_loopback:
                            hits[id] = name
                            # in this case there is no remote BR to check
                            found_net = True
                            break
                elif name.startswith('net_ix'): # internet exchange network

                        net_name = name.split('_')[-1].lstrip('ix')
                        if ip == local_ip:
                            hits[id] = name
                            found_net = True
                            # check that remote-border-router has 'name' under 'networks'
                            # and within this network in fact has assigned the IP 'remote_ip'
                            if not self._search_br(name, remote_ip):
                                raise AssertionError(f'remote BR of BR {folder} on IF {id} ({name}) doesn\'t exitst in docker-compose.yml (probably wrong remote address in topology.json)')


                            break
                elif name.startswith('net_xc'): # cross connect network
                    if ip == local_ip:
                        hits[id] = name
                        found_net = True
                        # assert that there exists a node who has the 'remote' address on one of its networks,
                        # and the name of this network is 'name' (as expected)

                        if not self._search_br(name, remote_ip):
                            raise AssertionError( f'remote BR of BR {folder} on IF {id} ({name}) doesn\'t exitst in docker-compose.yml (probably wrong remote address in topology.json)')


                        break
                else: # must be service network 000_svc
                    # but service network doesn't show up in topology.json
                    pass
            assert found_net, f'no network in docker-compose.yml for BR {node_name} IF {id} in topology.json file'

        assert len(hits) == len(interfaces), 'mismatch between topology.json and docker-compose.yml'

    def _search_br(self, name: str, remote_ip ) -> Optional[str]:
        """
        @brief looks up a router in the docker-compose.yml file,
            with the given IP on the given network
        @param name name of the network
        @param remote_ip IP address on the given network of the router in question
        """
        # nodes that are also on the the same network
        remote_br_candidates = [ (sname, svc)  for sname, svc in self._services.items() if 'networks' in svc and name in svc['networks'] ]

        remote_br = [ sname for (sname, svc) in remote_br_candidates if svc['networks'][name]['ipv4_address'] == remote_ip]
        assert len(remote_br) <= 1, 'there canno\'t be more than one router on the same net ({name}) with the same address {remote_ip}'
        return remote_br[0] if len(remote_br) > 0 else None

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
        raise FileNotFoundError(f"{full_path} does not exist.")



if __name__ == "__main__":

    sn = ScionOutputChecker('/home/lucas/repos/seed-emulator/output')

    sn.do_checks()