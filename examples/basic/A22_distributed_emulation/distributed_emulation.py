#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter
from seedemu.utilities import Makers
import sys, os, json

def run(dumpfile = None, topology_file = None):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm [topology_file.json]")
                sys.exit(1)
        elif len(sys.argv) == 3:
            platform_arg = sys.argv[1].lower()
            if platform_arg == 'amd':
                platform = Platform.AMD64
            elif platform_arg == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm [topology_file.json]")
                sys.exit(1)
            topology_file = sys.argv[2]
        else:
            print(f"Usage:  {script_name} amd|arm [topology_file.json]")
            sys.exit(1)

    # Load topology from JSON file
    if topology_file is None:
        # Default to topology6_edit.json if not specified
        topology_file = os.path.join(os.path.dirname(__file__), 'topology6_edit.json')
    
    if not os.path.exists(topology_file):
        print(f"Error: Topology file not found: {topology_file}")
        sys.exit(1)
    
    with open(topology_file, 'r') as f:
        topology = json.load(f)
    
    # Extract data from JSON
    as_list = topology.get('as_list', [])
    as_ix_connections = topology.get('as_ix_connections', [])

    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    web     = WebService()

    ###############################################################################
    # Collect all IX IDs from as_ix_connections
    ix_ids = set()
    for conn in as_ix_connections:
        for ix_id in conn.get('ix_list', []):
            ix_ids.add(ix_id)
    
    # Create all Internet Exchanges
    for ix_id in sorted(ix_ids):
        base.createInternetExchange(ix_id)

    ###############################################################################
    # Create a mapping from AS ID to its IX list for quick lookup
    as_to_ix_map = {}
    for conn in as_ix_connections:
        as_id = conn.get('as_id')
        if as_id is not None:
            as_to_ix_map[as_id] = conn.get('ix_list', [])
    
    ###############################################################################
    # Create all Autonomous Systems from as_list
    # Separate transit and stub ASes
    transit_as_list = []
    stub_as_list = []
    
    for as_info in as_list:
        as_id = as_info.get('as_id')
        as_type = as_info.get('as_type', '').lower()
        host_num = as_info.get('host_num', 0)
        
        if as_id is None:
            continue
        
        # Get the IX list for this AS
        as_ix_list = as_to_ix_map.get(as_id, [])
        
        if as_type == 'transit':
            # For transit AS, we need to create intra-IX links
            # Create a chain of links between consecutive IXs
            intra_ix_links = []
            if len(as_ix_list) > 1:
                # Create links between consecutive IXs in the sorted list
                sorted_ix_list = sorted(as_ix_list)
                for i in range(len(sorted_ix_list) - 1):
                    intra_ix_links.append((sorted_ix_list[i], sorted_ix_list[i+1]))
            
            # Create transit AS using Makers
            transit_as = Makers.makeTransitAs(base, as_id, as_ix_list, intra_ix_links)
            transit_as_list.append(as_id)
            
        elif as_type == 'stub':
            # For stub AS, it should connect to a single IX
            # If multiple IXs are specified, use the first one
            if len(as_ix_list) > 0:
                exchange = as_ix_list[0]
                # Create stub AS with hosts using Makers
                Makers.makeStubAsWithHosts(emu, base, as_id, exchange, host_num)
                stub_as_list.append(as_id)
                
                # Install web service on each host (hosts are named host_0, host_1, etc.)
                for i in range(host_num):
                    host_name = f'host_{i}'
                    web_service_name = f'web{as_id}_{i}'
                    web.install(web_service_name)
                    emu.addBinding(Binding(web_service_name, filter=Filter(nodeName=host_name, asn=as_id)))
            else:
                print(f"Warning: Stub AS {as_id} has no IX connection, skipping...")
        else:
            print(f"Warning: Unknown AS type '{as_type}' for AS {as_id}, skipping...")

    ###############################################################################
    # Set up EBGP peering at Internet Exchanges
    # For each IX, find all ASes connected to it and peer them via Route Server
    # Create a set of all created AS IDs for validation
    created_as_ids = set(transit_as_list + stub_as_list)
    
    for ix_id in sorted(ix_ids):
        ases_at_ix = []
        for conn in as_ix_connections:
            as_id = conn.get('as_id')
            if as_id is not None and ix_id in conn.get('ix_list', []):
                # Only add AS if it was actually created
                if as_id in created_as_ids:
                    ases_at_ix.append(as_id)
        
        # Add RS peers for all ASes at this IX (similar to mini_internet.py)
        if len(ases_at_ix) > 0:
            ebgp.addRsPeers(ix_id, ases_at_ix)

    ###############################################################################
    # Rendering 

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(web)

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        # Attach the Internet Map container to the emulator
        docker = Docker(platform=platform) 

        ###############################################################################
        # Compilation
        emu.compile(docker, './output', override=True)

if __name__ == '__main__':
    run()
