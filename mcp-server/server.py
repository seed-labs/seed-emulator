from mcp.server.fastmcp import FastMCP
import json
import sys
import os

# Add parent directory to path to import seedemu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runtime import runtime

mcp = FastMCP("seed-emulator-mcp")

# ==============================================================================
# Infrastructure Tools (Base Layer)
# ==============================================================================

@mcp.tool()
def create_as(asn: int) -> str:
    """Create an Autonomous System (AS).
    
    Args:
        asn: The Autonomous System Number (e.g., 100).
    """
    base = runtime.get_base()
    try:
        if asn in base.getAsns():
             return f"AS {asn} already exists."
             
        as_obj = base.createAutonomousSystem(asn)
        runtime.register_object(f"as{asn}", as_obj)
        runtime.log_code(f"as{asn} = base.createAutonomousSystem({asn})")
        return f"Created AS {asn}."
    except Exception as e:
        return f"Error creating AS {asn}: {str(e)}"

@mcp.tool()
def create_ix(asn: int, name: str) -> str:
    """Create an Internet Exchange (IX).
    
    Args:
        asn: The ASN for the IX.
        name: The name of the IX (e.g., 'ix100').
    """
    base = runtime.get_base()
    try:
        if asn in base.getInternetExchangeIds():
             return f"IX {asn} already exists."

        ix_obj = base.createInternetExchange(asn)
        runtime.register_object(name, ix_obj)
        runtime.log_code(f"{name} = base.createInternetExchange({asn})")
        return f"Created IX {name} (ASN {asn})."
    except Exception as e:
        return f"Error creating IX {asn}: {str(e)}"

@mcp.tool()
def create_node(name: str, asn: int, role: str) -> str:
    """Create a node (Router or Host) in an AS.
    
    Args:
        name: The unique name of the node (e.g., 'router1').
        asn: The ASN of the AS to create the node in.
        role: The role of the node. Must be 'router' or 'host'.
    """
    base = runtime.get_base()
    role = role.lower()
    
    try:
        if asn not in base.getAsns():
            return f"Error: AS {asn} does not exist. Please create it first using create_as."
            
        as_obj = base.getAutonomousSystem(asn)
        
        if role == 'router':
            node_obj = as_obj.createRouter(name)
            func_call = "createRouter"
        elif role == 'host':
            node_obj = as_obj.createHost(name)
            func_call = "createHost"
        else:
            return f"Error: Invalid role '{role}'. Must be 'router' or 'host'."
            
        runtime.register_object(name, node_obj)
        runtime.log_code(f"{name} = as{asn}.{func_call}('{name}')")
        return f"Created {role} '{name}' in AS {asn}."
    except Exception as e:
        return f"Error creating node '{name}': {str(e)}"

@mcp.tool()
def connect_nodes(node1_name: str, node2_name: str) -> str:
    """Connect two nodes with a direct link.
    
    - If nodes are in the same AS, creates a direct network in that AS.
    - If nodes are in different ASes, creates a cross-connect (peering).
    
    Args:
        node1_name: Name of the first node.
        node2_name: Name of the second node.
    """
    node1 = runtime.find_node_by_name(node1_name)
    node2 = runtime.find_node_by_name(node2_name)
    
    if not node1:
        return f"Error: Node '{node1_name}' not found."
    if not node2:
        return f"Error: Node '{node2_name}' not found."
        
    try:
        asn1 = node1.getAsn()
        asn2 = node2.getAsn()
        
        # Scenario 1: Intra-AS connection
        if asn1 == asn2:
            base = runtime.get_base()
            as_obj = base.getAutonomousSystem(asn1)
            
            # Create a unique network name for this link
            net_name = f"link_{node1_name}_{node2_name}"
            # Check if net exists, if not create it
            if net_name not in as_obj.getNetworks():
                 # Handle "auto" prefix limitation for AS > 255
                 # If we don't assume a prefix, we should give one.
                 # Simple hack: if asn > 255, we must provide a prefix.
                 prefix = "auto"
                 if asn1 > 255:
                     # Generate a "random" prefix or just use 192.168.x.x
                     # For link-{node1}-{node2}, we can hash something?
                     # Let's use 10.x.y.0/24
                     import random
                     o2 = random.randint(100, 200)
                     o3 = random.randint(0, 255)
                     prefix = f"10.{o2}.{o3}.0/24"
                 
                 as_obj.createNetwork(net_name, prefix=prefix)
                 runtime.log_code(f"as{asn1}.createNetwork('{net_name}', prefix='{prefix}')")
            
            node1.joinNetwork(net_name)
            node2.joinNetwork(net_name)
            
            runtime.log_code(f"{node1_name}.joinNetwork('{net_name}')")
            runtime.log_code(f"{node2_name}.joinNetwork('{net_name}')")
            
            return f"Connected {node1_name} and {node2_name} via {net_name} (AS {asn1})."

        # Scenario 2: Inter-AS connection (Cross Connect)
        else:
            # We need to assign IPs for cross connect. 
            # A simple strategy: Use a shared private block like 192.168.x.x or 10.x.x.x 
            # SEED Emulator usually requires manual IP for XC or it errors.
            # Let's generate a deterministic subnetwork based on ASNs to avoid collision? 
            # Or just use a specific range. e.g. 172.16.X.Y
            
            # A simple hash to get a unique /24 or /30
            # This is a bit hacky for a general tool, but good for MVP.
            # Let's say 10.{min_asn}.{max_asn}.0/24 is too risky if ans overlap?
            # Let's try to use 10.254.x.x for XC
            
            # For simplicity in this iteration, let's pick 10.99.99.1/30 and .2/30 for now
            # In a real tool we might want an IPAM manager.
            
            # Better: The user probably didn't supply IPs.
            # Let's check if we can assume "auto" works for XC?
            # Node.crossConnect signature: (peername, peerasn, address, ...)
            # address is NOT optional.
            
            # Strategy: Generate a random /30 subnet in 10.x.x.x space
            import random
            octet2 = random.randint(200, 250)
            octet3 = random.randint(0, 255)
            
            ip1 = f"10.{octet2}.{octet3}.1/24"
            ip2 = f"10.{octet2}.{octet3}.2/24"
            
            node1.crossConnect(asn2, node2_name, ip1)
            node2.crossConnect(asn1, node1_name, ip2)
            
            runtime.log_code(f"{node1_name}.crossConnect({asn2}, '{node2_name}', '{ip1}')")
            runtime.log_code(f"{node2_name}.crossConnect({asn1}, '{node1_name}', '{ip2}')")
            
            return f"Cross-connected {node1_name} (AS {asn1}) and {node2_name} (AS {asn2})."
            
    except Exception as e:
        return f"Error connecting nodes: {str(e)}"

# ==============================================================================
# Routing Tools (Routing, OSPF, BGP)
# ==============================================================================

@mcp.tool()
def enable_routing_layers(layers: list[str]) -> str:
    """Enable specific routing layers for the simulation.
    
    Args:
        layers: List of layers to enable. Supported: 'routing', 'ospf', 'ibgp', 'ebgp', 'mpls'.
                Dependencies are automatically handled (e.g., OSPF depends on Routing).
    """
    emulator = runtime.get_emulator()
    enabled = []
    
    # Map input strings to class names/objects
    # We use strings to avoid importing everything at top level if possible, 
    # but runtime needs to know about classes.
    # In runtime.py code buffer, we imported them.
    
    from seedemu.layers import Routing, Ospf, Ibgp, Ebgp, Mpls

    LAYER_MAP = {
        'routing': Routing,
        'ospf': Ospf,
        'ibgp': Ibgp,
        'ebgp': Ebgp,
        'mpls': Mpls
    }
    
    try:
        for layer_name in layers:
            lname = layer_name.lower()
            if lname not in LAYER_MAP:
                return f"Error: Unknown layer '{layer_name}'. Supported: {list(LAYER_MAP.keys())}"
                
            layer_class = LAYER_MAP[lname]
            layer_instance = layer_class()
            
            # Check if already added?
            # emulator.getLayer(name) might throw if not found? 
            # Or we can check layers db.
            # But SEED Emulator allows adding layer object.
            # If we add duplicate layer name, it asserts error.
            
            # Simple check:
            # We need to conform to layer names. 
            # Routing -> "Routing"
            # Ospf -> "Ospf"
            real_name = layer_instance.getName()
            
            # Check if layer exists in emulator to avoid crash
            # Emulator doesn't expose "hasLayer" easily, but getLayers() returns list.
            existing_names = [l.getName() for l in emulator.getLayers()]
            
            if real_name in existing_names:
                continue

            emulator.addLayer(layer_instance)
            enabled.append(real_name)
            
            # Log code
            # We assume imports are there.
            runtime.log_code(f"emulator.addLayer({layer_class.__name__}())")
            
        if not enabled:
            return "No new layers enabled."
            
        return f"Enabled layers: {', '.join(enabled)}"
        
    except Exception as e:
        return f"Error enabling layers: {str(e)}"

@mcp.tool()
def configure_ebgp_peering(asn1: int, asn2: int, relationship: str) -> str:
    """Configure eBGP peering between two ASes.
    
    This handles both Direct (Cross-Connect) peering and IX peering automatically based on connectivity.
    
    Args:
        asn1: First AS.
        asn2: Second AS.
        relationship: 'peer' (default) or 'provider' (asn1 provides for asn2). 
                      Note: SEED API usually takes 'Peer' or 'Provider'.
                      If 'provider', ASN1 is Provider for ASN2.
    """
    emulator = runtime.get_emulator()
    registry = emulator.getRegistry()
    
    # We need the Ebgp layer instance
    # It must be added to emulator first.
    # We can try to get it, or auto-add it? 
    # Let's demand user to enable it first, or auto-add.
    
    from seedemu.layers import Ebgp, PeerRelationship
    
    # Try find Ebgp layer
    ebgp_layer = None
    existing_layers = emulator.getLayers()
    for l in existing_layers:
        if isinstance(l, Ebgp):
            ebgp_layer = l
            break
            
    if not ebgp_layer:
        return "Error: Ebgp layer not enabled. Please use enable_routing_layers(['ebgp']) first."
        
@mcp.tool()
def connect_to_ix(node_name: str, ix_asn: int) -> str:
    """Connect a router to an Internet Exchange (IX).
    
    Args:
        node_name: The name of the router.
        ix_asn: The ASN of the Internet Exchange.
    """
    node = runtime.find_node_by_name(node_name)
    base = runtime.get_base()
    
    if not node:
        return f"Error: Node '{node_name}' not found."
        
    try:
        # Check if IX exists
        if ix_asn not in base.getInternetExchangeIds():
            return f"Error: IX {ix_asn} not found."
            
        ix = base.getInternetExchange(ix_asn)
        net_name = ix.getNetwork().getName()
        
        # Determine address. Usually IX assigns IP automatically based on 'mapIxAddress' logic in Network.py
        # node.joinNetwork(net, address="auto") is default.
        
        node.joinNetwork(net_name)
        
        runtime.log_code(f"{node_name}.joinNetwork('{net_name}')")
        return f"Connected {node_name} to IX {ix_asn}."
        
    except Exception as e:
        return f"Error connecting to IX: {str(e)}"

@mcp.tool()
def configure_ix_peering(ix_asn: int, asn1: int, asn2: int, relationship: str) -> str:
    """Configure eBGP peering between two ASes at a specific Internet Exchange (IX).
    
    Args:
        ix_asn: The ASN of the IX to peer at.
        asn1: First AS.
        asn2: Second AS.
        relationship: 'peer' (default) or 'provider'.
    """
    emulator = runtime.get_emulator()
    from seedemu.layers import Ebgp, PeerRelationship
    
    ebgp_layer = None
    existing_layers = emulator.getLayers()
    for l in existing_layers:
        if isinstance(l, Ebgp):
            ebgp_layer = l
            break
            
    if not ebgp_layer:
        return "Error: Ebgp layer not enabled."

    rel_map = {
        'peer': PeerRelationship.Peer,
        'provider': PeerRelationship.Provider,
    }
    r_str = relationship.lower()
    
    if r_str == 'customer':
        temp = asn1
        asn1 = asn2
        asn2 = temp
        rel_enum = PeerRelationship.Provider
    elif r_str in rel_map:
        rel_enum = rel_map[r_str]
    else:
        return f"Error: Invalid relationship '{relationship}'."

    try:
        ebgp_layer.addPrivatePeering(ix_asn, asn1, asn2, rel_enum)
        runtime.log_code(f"ebgp.addPrivatePeering({ix_asn}, {asn1}, {asn2}, PeerRelationship.{rel_enum.name})")
        return f"Configured Private Peering at IX {ix_asn} between AS {asn1} and AS {asn2} ({rel_enum.name})."
    except Exception as e:
        return f"Error configuring IX peering: {str(e)}"

@mcp.tool()
def configure_direct_peering(asn1: int, asn2: int, relationship: str) -> str:
    """Configure direct eBGP peering (Cross Connect) between two ASes.
    
    Args:
        asn1: First AS.
        asn2: Second AS.
        relationship: 'peer' (default) or 'provider'.
    """
    emulator = runtime.get_emulator()
    from seedemu.layers import Ebgp, PeerRelationship
    
    ebgp_layer = None
    existing_layers = emulator.getLayers()
    for l in existing_layers:
        if isinstance(l, Ebgp):
            ebgp_layer = l
            break
            
    if not ebgp_layer:
        return "Error: Ebgp layer not enabled."

    rel_map = {
        'peer': PeerRelationship.Peer,
        'provider': PeerRelationship.Provider,
    }
    r_str = relationship.lower()
    
    if r_str == 'customer':
        temp = asn1
        asn1 = asn2
        asn2 = temp
        rel_enum = PeerRelationship.Provider
    elif r_str in rel_map:
        rel_enum = rel_map[r_str]
    else:
        return f"Error: Invalid relationship '{relationship}'."

    try:
        ebgp_layer.addCrossConnectPeering(asn1, asn2, rel_enum)
        runtime.log_code(f"ebgp.addCrossConnectPeering({asn1}, {asn2}, PeerRelationship.{rel_enum.name})")
        return f"Configured Cross-Connect peering between AS {asn1} and AS {asn2} ({rel_enum.name})."
    except Exception as e:
        return f"Error configuring Direct peering: {str(e)}"

# ==============================================================================
# Service Tools (Web, DNS, etc.)
# ==============================================================================

@mcp.tool()
def install_service(node_name: str, service_type: str, params: str) -> str:
    """Install a service on a node.
    
    Args:
        node_name: The name of the node where the service will be installed.
        service_type: The type of service logic. Supported: 'WebService', 'DomainNameService'.
        params: A JSON string containing configuration parameters.
    """
    # In SEED Emulator, Services are Layers.
    # We install a service ON a node by asking the Service Layer to 'install' it on that vnode.
    # Then we configure the returned Server object.
    
    node = runtime.find_node_by_name(node_name)
    if not node:
        # Note: Service layer actually works on vnode names, so strict existence check 
        # isn't strictly required by SEED, but good for MCP to fail early.
        return f"Error: Node '{node_name}' not found."
    
    # Auto-binding: Bind the vnode (node_name) to the physical node found
    from seedemu.core import Binding, Filter
    emulator = runtime.get_emulator()
    
    # Check if binding already exists? SEED allows multiple bindings but best to overlap?
    # We create a 1-to-1 binding for this service installation.
    # We use node_name as vnode name.
    # Filter matches target node properties.
    emulator.addBinding(Binding(node_name, filter=Filter(nodeName=node.getName(), asn=node.getAsn())))
    runtime.log_code(f"emulator.addBinding(Binding('{node_name}', filter=Filter(nodeName='{node.getName()}', asn={node.getAsn()})))")
        
    try:
        parameters = json.loads(params)
    except json.JSONDecodeError:
        return "Error: params must be a valid JSON string."
    
    try:
        if service_type == 'WebService':
            from seedemu.services import WebService
            
            # Check if WebService layer already exists? 
            # Usually we want one WebService layer managing all web servers?
            # Or one per server? SEED supports multiple.
            # Let's create a new one for this request to be safe/simple, 
            # or try to reuse? Reusing is better for generated graph/structure.
            
            web_layer = None
            for l in emulator.getLayers():
                if isinstance(l, WebService):
                    web_layer = l
                    break
            
            if not web_layer:
                web_layer = WebService()
                emulator.addLayer(web_layer)
                runtime.log_code("web_layer = WebService()")
                runtime.log_code("emulator.addLayer(web_layer)")
            else:
                runtime.log_code("# reusing existing WebService layer")

            # Install on node (returns WebServer object)
            server = web_layer.install(node_name)
            
            # Param: url (optional string or list)
            url = parameters.get('url')
            if url:
                if isinstance(url, str):
                    server.setServerNames([url])
                    runtime.log_code(f"web_layer.install('{node_name}').setServerNames(['{url}'])")
                elif isinstance(url, list):
                    server.setServerNames(url)
                    runtime.log_code(f"web_layer.install('{node_name}').setServerNames({url})")
            
            # Param: index_html
            content = parameters.get('index_html')
            if content:
                server.setIndexContent(content)
                
            return f"Installed WebService on {node_name}."
            
        elif service_type == 'DomainNameService':
            from seedemu.services import DomainNameService
            
            dns_layer = None
            for l in emulator.getLayers():
                if isinstance(l, DomainNameService):
                    dns_layer = l
                    break
            
            if not dns_layer:
                # autoNameServer usually True by default
                dns_layer = DomainNameService()
                emulator.addLayer(dns_layer)
                runtime.log_code("dns_layer = DomainNameService()")
                runtime.log_code("emulator.addLayer(dns_layer)")

            # DomainNameService.getZone returns a Zone object (global registry of zones)
            # DomainNameService.install(node) returns a DomainNameServer object running on that node
            
            # 1. Configure Zones (Model update)
            zones = parameters.get('zones', [])
            for zone_conf in zones:
                z_name = zone_conf.get('name')
                records = zone_conf.get('records', [])
                
                # Get or create zone
                zone = dns_layer.getZone(z_name)
                
                for rec in records:
                    r_name = rec.get('name')
                    r_type = rec.get('type')
                    r_val = rec.get('value')
                    
                    # Try to resolve r_val to a node
                    target_node = runtime.find_node_by_name(r_val)
                    if target_node and r_type == 'A':
                         # Use resolveToVnode for A records pointing to nodes (names)
                         # resolveToVnode(record_name, vnode_name)
                         # We use node name as vnode name here.
                         zone.resolveToVnode(r_name, r_val)
                    else:
                         # Add raw record
                         zone.addRecord(f"{r_name} {r_type} {r_val}")

            # 2. Host Zones on Server (Deployment)
            # We need to tell the server which zones it hosts
            server = dns_layer.install(node_name)
            
            for zone_conf in zones:
                z_name = zone_conf.get('name')
                server.addZone(z_name)
                
            return f"Installed DomainNameService on {node_name} hosting {len(zones)} zones."
            
        else:
            return f"Error: Unknown service type '{service_type}'."
            
    except Exception as e:
        return f"Error installing service: {str(e)}"

@mcp.tool()
def render_simulation() -> str:
    """Render the simulation to generate all configurations.
    
    This validates the topology and services. It does NOT generate Docker files yet (compile step).
    Useful for checking consistency.
    """
    emulator = runtime.get_emulator()
    try:
        emulator.render()
        runtime.rendered = True
        return "Simulation rendered successfully. Configuration files generated in memory."
    except Exception as e:
        return f"Error rendering simulation: {str(e)}"

# ==============================================================================
# Helper Resources
# ==============================================================================
@mcp.resource("seed://topology/summary")
def get_topology_summary() -> str:
    """Get a JSON summary of the current topology (ASes, Nodes, Links)"""
    base = runtime.get_base()
    summary = {
        "ases": [],
        "ixs": []
    }
    for asn in base.getAsns():
        as_obj = base.getAutonomousSystem(asn)
        as_data = {
            "asn": asn,
            "routers": list(as_obj.getRouters()),
            "hosts": list(as_obj.getHosts()),
            "networks": list(as_obj.getNetworks())
        }
        summary["ases"].append(as_data)
        
    for ix_id in base.getInternetExchangeIds():
        ix = base.getInternetExchange(ix_id)
        summary["ixs"].append({"asn": ix_id, "name": ix.getName()})

    return json.dumps(summary, indent=2)
@mcp.resource("seed://topology/graph")
def get_topology_graph() -> str:
    """Get a Graphviz DOT description of the topology (Requires Render)"""
    emulator = runtime.get_emulator()
    base = runtime.get_base()
    
    if not emulator.rendered():
         return "digraph G { label=\"Not Rendered Yet\"; }"
    
    try:
        base.createGraphs(emulator)
        graph = base.getGraph('Layer 2 Connections')
        return graph.toGraphviz()
    except Exception as e:
        return f"digraph G {{ label=\"Error generating graph: {str(e)}\"; }}"

@mcp.resource("seed://node/{node_name}/info")
def get_node_info(node_name: str) -> str:
    """Get information about a specific node"""
    base = runtime.get_base()
    
    # Search for the node in all ASes
    found_node = None
    for asn in base.getAsns():
        as_obj = base.getAutonomousSystem(asn)
        # Check Hosts
        if node_name in as_obj.getHosts():
             found_node = as_obj.getHost(node_name)
             break
        # Check Routers
        if node_name in as_obj.getRouters():
             found_node = as_obj.getRouter(node_name)
             break
             
    if not found_node:
        return json.dumps({"error": f"Node '{node_name}' not found"}, indent=2)
        
    info = {
        "name": found_node.getName(),
        "asn": found_node.getAsn(),
        "role": str(found_node.getRole()),
        "interfaces": []
    }
    
    try:
        for iface in found_node.getInterfaces():
            info["interfaces"].append({
                "net": iface.getNet().getName(),
                "ip": str(iface.getAddress())
            })
    except Exception:
        pass # Interfaces might not be ready
        
    return json.dumps(info, indent=2)

if __name__ == "__main__":
    mcp.run()
