from mcp.server.fastmcp import FastMCP
import json
import sys
import os


# Add parent directory to path to import seedemu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from seedemu.layers import Routing, Ospf, Ibgp, Ebgp, Mpls, Evpn
from seedemu.services import WebService, DomainNameService, BotnetService, BotnetClientService


from runtime import runtime


def _create_mcp() -> FastMCP:
    # When launched via serve_http.py, enable Streamable-HTTP auth settings at construction time.
    # This avoids mutating private FastMCP internals after import.
    if (os.environ.get("SEED_MCP_HTTP") or "").strip() == "1":
        from mcp.server.transport_security import TransportSecuritySettings

        from seedops.auth import StaticTokenVerifier, build_auth_settings
        from seedops.config import load_config

        cfg = load_config(require_token=True)
        auth = build_auth_settings(cfg.public_url)
        verifier = StaticTokenVerifier(cfg.token or "")
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=cfg.dns_rebinding_protection,
            allowed_hosts=cfg.allowed_hosts,
            allowed_origins=cfg.allowed_origins,
        )

        return FastMCP(
            "seed-emulator-mcp",
            host=cfg.host,
            port=cfg.port,
            streamable_http_path=cfg.streamable_http_path,
            auth=auth,
            token_verifier=verifier,
            transport_security=transport_security,
        )

    return FastMCP("seed-emulator-mcp")


mcp = _create_mcp()

# Register SeedOps (Phase 1) operational tools (workspace/inventory/batch ops).
# This keeps existing tools intact and adds new ones for attaching to and operating
# on already-running simulations.
try:
    from seedops import register_tools as _register_seedops_tools

    _register_seedops_tools(mcp)
except Exception as _e:
    # Keep server importable even if SeedOps dependencies are missing in a minimal env.
    pass

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
# Routing Tools (Routing, OSPF, BGP, MPLS, EVPN)
# ==============================================================================

@mcp.tool()
def enable_mpls_on_as(asn: int) -> str:
    """Enable MPLS layer for a specific Autonomous System.
    
    This enables MPLS, OSPF, and LDP on the AS.
    
    Args:
        asn: The AS number to enable MPLS on.
    """
    emulator = runtime.get_emulator()
    try:
        from seedemu.layers import Mpls
        
        # Check if MPLS layer exists
        mpls_layer = None
        for l in emulator.getLayers():
            if isinstance(l, Mpls):
                mpls_layer = l
                break
        
        if not mpls_layer:
            mpls_layer = Mpls()
            emulator.addLayer(mpls_layer)
            runtime.log_code("mpls_layer = Mpls()")
            runtime.log_code("emulator.addLayer(mpls_layer)")
        
        mpls_layer.enableOn(asn)
        runtime.log_code(f"mpls_layer.enableOn({asn})")
        
        return f"Enabled MPLS on AS {asn}."
    except Exception as e:
        return f"Error enabling MPLS on AS {asn}: {str(e)}"

@mcp.tool()
def mark_mpls_edge(asn: int, node_name: str) -> str:
    """Mark a router as an MPLS Provider Edge (PE) router.
    
    By default, only routers with IX connections or host-heavy networks are PE.
    Use this to manually designate a router as PE.
    
    Args:
        asn: The AS number.
        node_name: The name of the router node.
    """
    emulator = runtime.get_emulator()
    try:
        from seedemu.layers import Mpls
        
        mpls_layer = None
        for l in emulator.getLayers():
            if isinstance(l, Mpls):
                mpls_layer = l
                break
        
        if not mpls_layer:
            return "Error: MPLS layer not enabled. Use enable_routing_layers(['mpls']) or enable_mpls_on_as() first."

        mpls_layer.markAsEdge(asn, node_name)
        runtime.log_code(f"mpls_layer.markAsEdge({asn}, '{node_name}')")
        
        return f"Marked {node_name} as MPLS Edge router in AS {asn}."
    except Exception as e:
        return f"Error marking MPLS edge: {str(e)}"

@mcp.tool()
def create_evpn_customer(provider_asn: int, customer_asn: int, vni: int, pe_router: str, customer_net: str) -> str:
    """Create an EVPN customer attachment.
    
    Connects a customer AS network to a Provider Edge (PE) router via EVPN (VXLAN).
    
    Args:
        provider_asn: The provider AS number (must have EVPN enabled).
        customer_asn: The customer AS number.
        vni: VXLAN Network Identifier (unique ID).
        pe_router: Name of the Provider Edge router in the provider AS.
        customer_net: Name of the network in the customer AS to connect.
    """
    emulator = runtime.get_emulator()
    try:
        from seedemu.layers import Evpn
        
        evpn_layer = None
        for l in emulator.getLayers():
            if isinstance(l, Evpn):
                evpn_layer = l
                break
        
        if not evpn_layer:
            evpn_layer = Evpn()
            emulator.addLayer(evpn_layer)
            runtime.log_code("evpn_layer = Evpn()")
            runtime.log_code("emulator.addLayer(evpn_layer)")
            
        # Ensure provider is configured as EVPN provider
        if provider_asn not in evpn_layer.getEvpnProviders():
            evpn_layer.configureAsEvpnProvider(provider_asn)
            runtime.log_code(f"evpn_layer.configureAsEvpnProvider({provider_asn})")
            
        evpn_layer.addCustomer(provider_asn, customer_asn, customer_net, pe_router, vni)
        runtime.log_code(f"evpn_layer.addCustomer({provider_asn}, {customer_asn}, '{customer_net}', '{pe_router}', {vni})")
        
        return f"Created EVPN customer connection (Provider AS{provider_asn} <-> Customer AS{customer_asn} VNI {vni})."
    except Exception as e:
        return f"Error creating EVPN customer: {str(e)}"


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
        'mpls': Mpls,
        'evpn': Evpn
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
# Granular Node Control Tools (File, Command Injection)
# ==============================================================================

@mcp.tool()
def add_node_file(node_name: str, file_path: str, content: str) -> str:
    """Inject a file into a node's filesystem.
    
    Args:
        node_name: Name of the node.
        file_path: Absolute path inside the container (e.g., '/etc/myconfig.conf').
        content: Text content of the file.
    """
    node = runtime.find_node_by_name(node_name)
    if not node: return f"Error: Node {node_name} not found."
    
    try:
        node.setFile(file_path, content)
        runtime.log_code(f"find_node('{node_name}').setFile('{file_path}', '...content...')")
        return f"Added file {file_path} to {node_name}."
    except Exception as e:
        return f"Error adding file: {str(e)}"

@mcp.tool()
def add_node_start_command(node_name: str, command: str) -> str:
    """Add a shell command to run when the node starts.
    
    Args:
        node_name: Name of the node.
        command: Shell command string (e.g., 'service nginx restart').
    """
    node = runtime.find_node_by_name(node_name)
    if not node: return f"Error: Node {node_name} not found."
    
    try:
        node.appendStartCommand(command)
        runtime.log_code(f"find_node('{node_name}').appendStartCommand('{command}')")
        return f"Added start command to {node_name}."
    except Exception as e:
        return f"Error adding start command: {str(e)}"

@mcp.tool()
def add_node_build_command(node_name: str, command: str) -> str:
    """Add a Dockerfile build command (e.g., RUN ...).
    
    Use this to install software or modify the image during build.
    
    Args:
        node_name: Name of the node.
        command: Build command (e.g., 'apt-get install -y nmap').
    """
    node = runtime.find_node_by_name(node_name)
    if not node: return f"Error: Node {node_name} not found."
    
    try:
        node.addBuildCommand(command)
        runtime.log_code(f"find_node('{node_name}').addBuildCommand('{command}')")
        return f"Added build command to {node_name}."
    except Exception as e:
        return f"Error adding build command: {str(e)}"

# ==============================================================================
# Service Tools (Web, DNS, Email, Botnet)
# ==============================================================================

@mcp.tool()
def configure_web_server(node_name: str, url: str = "www.example.com", index_html: str = "<h1>Hello</h1>", enable_https: bool = False) -> str:
    """Configure a Web Server with specific content and settings.
    
    Args:
        node_name: Name of the node to host the web server.
        url: The domain name/URL to serve (e.g., "www.bank.com").
        index_html: The HTML content for the index page.
        enable_https: Whether to enable HTTPS (requires PKI, not fully auto-configured here yet).
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node:
            return f"Error: Node '{node_name}' not found."

        from seedemu.services import WebService
        from seedemu.core import Binding, Filter
        
        emulator = runtime.get_emulator()
        
        # Ensure WebService layer
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
            
        # Auto-bind
        emulator.addBinding(Binding(node_name, filter=Filter(nodeName=node.getName(), asn=node.getAsn())))
        runtime.log_code(f"emulator.addBinding(Binding('{node_name}', filter=Filter(nodeName='{node.getName()}', asn={node.getAsn()})))")

        server = web_layer.install(node_name)
        server.setServerNames([url])
        server.setIndexContent(index_html)
        
        runtime.log_code(f"server = web_layer.install('{node_name}')")
        runtime.log_code(f"server.setServerNames(['{url}'])")
        # Don't log full HTML if huge
        runtime.log_code(f"server.setIndexContent('...html content...')")
        
        return f"Configured WebServer on {node_name} serving {url}."
    except Exception as e:
        return f"Error configuring web server: {str(e)}"

@mcp.tool()
def configure_dns_zone(zone_name: str, records: list[str], glue_records: list[tuple[str,str]] = []) -> str:
    """Configure a DNS Zone.
    
    Args:
        zone_name: The name of the zone (e.g., "example.com").
        records: List of resource records (e.g., ["www A 10.0.0.1", "mail A 10.0.0.2"]).
        glue_records: List of glue records for subdomains (tuple of fqdn, ip).
    """
    try:
        from seedemu.services import DomainNameService
        emulator = runtime.get_emulator()
        
        dns_layer = None
        for l in emulator.getLayers():
            if isinstance(l, DomainNameService):
                dns_layer = l
                break
        if not dns_layer:
            dns_layer = DomainNameService()
            emulator.addLayer(dns_layer)
            runtime.log_code("dns_layer = DomainNameService()")
            runtime.log_code("emulator.addLayer(dns_layer)")
            
        zone = dns_layer.getZone(zone_name)
        
        for rec in records:
            zone.addRecord(rec)
            runtime.log_code(f"dns_layer.getZone('{zone_name}').addRecord('{rec}')")
            
        for fqdn, ip in glue_records:
            zone.addGuleRecord(fqdn, ip)
            runtime.log_code(f"dns_layer.getZone('{zone_name}').addGuleRecord('{fqdn}', '{ip}')")
            
        return f"Configured DNS Zone {zone_name} with {len(records)} records."
    except Exception as e:
        return f"Error configuring DNS zone: {str(e)}"

@mcp.tool()
def install_botnet_c2(node_name: str, port: int = 445) -> str:
    """Install a Botnet Command & Control (C2) server.
    
    Uses BYOB (Build Your Own Botnet) framework.
    
    Args:
        node_name: The node to host the C2 server.
        port: The primary port for the C2 server.
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node: return f"Error: Node {node_name} not found."
        
        from seedemu.services import BotnetService
        from seedemu.core import Binding, Filter
        emulator = runtime.get_emulator()
        
        c2_layer = None
        for l in emulator.getLayers():
            if isinstance(l, BotnetService):
                c2_layer = l
                break
        if not c2_layer:
            c2_layer = BotnetService()
            emulator.addLayer(c2_layer)
            runtime.log_code("c2_layer = BotnetService()")
            runtime.log_code("emulator.addLayer(c2_layer)")
            
        emulator.addBinding(Binding(node_name, filter=Filter(nodeName=node.getName(), asn=node.getAsn())))
        
        server = c2_layer.install(node_name)
        server.setPort(port)
        runtime.log_code(f"c2_layer.install('{node_name}').setPort({port})")
        
        return f"Installed Botnet C2 on {node_name} port {port}."
    except Exception as e:
        return f"Error install botnet C2: {str(e)}"
        
@mcp.tool()
def install_botnet_bot(node_name: str, c2_node_name: str) -> str:
    """Install a Botnet Client (Bot) connecting to a C2 server.
    
    Args:
        node_name: The victim node to install the bot on.
        c2_node_name: The name of the C2 server node (virtual node name used in install_botnet_c2).
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node: return f"Error: Node {node_name} not found."
        
        from seedemu.services import BotnetClientService
        from seedemu.core import Binding, Filter
        emulator = runtime.get_emulator()
        
        bot_layer = None
        for l in emulator.getLayers():
            if isinstance(l, BotnetClientService):
                bot_layer = l
                break
        if not bot_layer:
            bot_layer = BotnetClientService()
            emulator.addLayer(bot_layer)
            runtime.log_code("bot_layer = BotnetClientService()")
            runtime.log_code("emulator.addLayer(bot_layer)")
            
        # Bind the bot service to physical node
        # We use a unique name for the bot service instance on this node
        bot_vnode_name = f"bot_{node_name}"
        emulator.addBinding(Binding(bot_vnode_name, filter=Filter(nodeName=node.getName(), asn=node.getAsn())))
        
        client = bot_layer.install(bot_vnode_name)
        client.setServer(c2_node_name)
        runtime.log_code(f"bot_layer.install('{bot_vnode_name}').setServer('{c2_node_name}')")
        
        return f"Installed Botnet Bot on {node_name} connecting to {c2_node_name}."
    except Exception as e:
        return f"Error installing botnet bot: {str(e)}"

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
# Email Service Tools
# ==============================================================================

@mcp.tool()
def install_email_service(
    domain: str,
    asn: int,
    ip: str,
    gateway: str,
    mode: str = "dns",
    hostname: str = "mail",
    dns_server: str = "",
    network_name: str = "net0"
) -> str:
    """Install an email server (Postfix/Dovecot based) for a domain.
    
    Args:
        domain: Email domain (e.g., "example.com")
        asn: AS number where the mail server resides
        ip: IP address for the mail server
        gateway: Default gateway IP for routing
        mode: "dns" (uses DNS for routing) or "transport" (explicit transport maps)
        hostname: Hostname prefix (default "mail", results in mail.example.com)
        dns_server: Optional DNS server IP for DNS mode
        network_name: Name of the network to attach to (default "net0")
    
    Example:
        install_email_service("example.com", 100, "10.100.0.10", "10.100.0.254")
    """
    from seedemu.services.EmailService import EmailService
    
    try:
        # Get or create EmailService instance in runtime
        if not hasattr(runtime, 'email_service'):
            runtime.email_service = EmailService(mode=mode, dns_nameserver=dns_server or None)
        
        email_svc = runtime.email_service
        
        # Add provider
        email_svc.add_provider(
            domain=domain,
            asn=asn,
            ip=ip,
            gateway=gateway,
            hostname=hostname,
            dns=dns_server or None,
            net=network_name
        )
        
        runtime.log_code(f"# Email Service")
        runtime.log_code(f"email_svc = EmailService(mode='{mode}')")
        runtime.log_code(f"email_svc.add_provider(domain='{domain}', asn={asn}, ip='{ip}', gateway='{gateway}')")
        
        return f"Email service registered for {hostname}.{domain} (IP: {ip}, AS{asn}). Will be attached during Docker compilation."
    except Exception as e:
        return f"Error installing email service: {str(e)}"


@mcp.tool()
def list_email_providers() -> str:
    """List all registered email providers."""
    if not hasattr(runtime, 'email_service'):
        return "No email services registered."
    
    providers = runtime.email_service.get_providers()
    if not providers:
        return "No email providers registered."
    
    result = []
    for p in providers:
        result.append({
            "domain": p["domain"],
            "hostname": f"{p['hostname']}.{p['domain']}",
            "ip": p["ip"],
            "asn": p["asn"]
        })
    
    import json
    return json.dumps(result, indent=2)

# ==============================================================================
# Network Configuration Tools
# ==============================================================================

@mcp.tool()
def configure_link_properties(
    node_name: str,
    interface_index: int = 0,
    latency_ms: int = 0,
    bandwidth_bps: int = 0,
    packet_loss: float = 0.0
) -> str:
    """Configure link properties (latency, bandwidth, packet loss) for a node's interface.
    
    Args:
        node_name: Name of the node
        interface_index: Index of the interface (0 for first interface)
        latency_ms: Latency to add in milliseconds (default 0)
        bandwidth_bps: Egress bandwidth limit in bits per second (0 = unlimited)
        packet_loss: Packet drop percentage 0-100 (default 0)
    
    Example:
        configure_link_properties("r1", 0, latency_ms=50, bandwidth_bps=1000000)
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node:
            return f"Error: Node '{node_name}' not found."
        
        ifaces = node.getInterfaces()
        if interface_index >= len(ifaces):
            return f"Error: Interface index {interface_index} out of range. Node has {len(ifaces)} interfaces."
        
        iface = ifaces[interface_index]
        iface.setLinkProperties(
            latency=latency_ms,
            bandwidth=bandwidth_bps,
            packetDrop=packet_loss
        )
        
        runtime.log_code(f"# Configure link properties for {node_name}")
        runtime.log_code(f"node.getInterfaces()[{interface_index}].setLinkProperties(latency={latency_ms}, bandwidth={bandwidth_bps}, packetDrop={packet_loss})")
        
        props = []
        if latency_ms > 0:
            props.append(f"latency={latency_ms}ms")
        if bandwidth_bps > 0:
            props.append(f"bandwidth={bandwidth_bps}bps")
        if packet_loss > 0:
            props.append(f"loss={packet_loss}%")
        
        return f"Configured {node_name} interface {interface_index}: {', '.join(props) if props else 'default properties'}"
    except Exception as e:
        return f"Error configuring link properties: {str(e)}"


@mcp.tool()
def add_static_route(
    node_name: str,
    destination: str,
    next_hop: str
) -> str:
    """Add a static route to a node.
    
    Args:
        node_name: Name of the node
        destination: Destination network in CIDR format (e.g., "10.0.0.0/8")
        next_hop: Next hop IP address
    
    Example:
        add_static_route("host1", "0.0.0.0/0", "10.100.0.254")
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node:
            return f"Error: Node '{node_name}' not found."
        
        # Add static route command to node startup
        route_cmd = f"ip route add {destination} via {next_hop} || true"
        node.appendStartCommand(route_cmd)
        
        runtime.log_code(f"# Add static route to {node_name}")
        runtime.log_code(f"node.appendStartCommand('{route_cmd}')")
        
        return f"Added static route on {node_name}: {destination} via {next_hop}"
    except Exception as e:
        return f"Error adding static route: {str(e)}"


@mcp.tool()
def get_node_interfaces(node_name: str) -> str:
    """Get information about a node's network interfaces.
    
    Args:
        node_name: Name of the node
    """
    try:
        node = runtime.find_node_by_name(node_name)
        if not node:
            return f"Error: Node '{node_name}' not found."
        
        ifaces = node.getInterfaces()
        result = []
        for i, iface in enumerate(ifaces):
            info = {
                "index": i,
                "address": str(iface.getAddress()) if iface.getAddress() else "not assigned",
                "network": iface.getNet().getName() if iface.getNet() else "unknown"
            }
            result.append(info)
        
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting interfaces: {str(e)}"

# ==============================================================================
# Topology Export Tools
# ==============================================================================

@mcp.tool()
def get_topology_summary() -> str:
    """Get a human-readable summary of the current topology.
    
    Returns information about all ASes, IXes, nodes, and their connections.
    """
    base = runtime.get_base()
    
    summary = {
        "autonomous_systems": [],
        "internet_exchanges": [],
        "total_routers": 0,
        "total_hosts": 0
    }
    
    # Get all ASes
    for asn in base.getAsns():
        asys = base.getAutonomousSystem(asn)
        routers = asys.getRouters()
        hosts = asys.getHosts()
        networks = asys.getNetworks()
        
        summary["autonomous_systems"].append({
            "asn": asn,
            "routers": routers,
            "hosts": hosts,
            "networks": networks
        })
        summary["total_routers"] += len(routers)
        summary["total_hosts"] += len(hosts)
    
    # Get all IXes
    for ix_id in base.getInternetExchangeIds():
        ix = base.getInternetExchange(ix_id)
        summary["internet_exchanges"].append({
            "id": ix_id,
            "name": ix.getDisplayName() if hasattr(ix, 'getDisplayName') else f"IX{ix_id}"
        })
    
    import json
    return json.dumps(summary, indent=2)


@mcp.tool()
def export_topology(format: str = "json") -> str:
    """Export the current topology in various formats.
    
    Args:
        format: Output format - "json", "mermaid", or "graphviz"
    
    Returns:
        Topology representation in the requested format
    """
    base = runtime.get_base()
    
    if format == "json":
        return get_topology_summary()
    
    elif format == "mermaid":
        lines = ["graph LR"]
        
        # Add ASes as subgraphs
        for asn in base.getAsns():
            asys = base.getAutonomousSystem(asn)
            lines.append(f"    subgraph AS{asn}")
            
            for r_name in asys.getRouters():
                lines.append(f"        {r_name}[({r_name})]")
            for h_name in asys.getHosts():
                lines.append(f"        {h_name}[{h_name}]")
            
            lines.append("    end")
        
        # Add IXes
        for ix_id in base.getInternetExchangeIds():
            lines.append(f"    IX{ix_id}{{IX{ix_id}}}")
        
        return "\n".join(lines)
    
    elif format == "graphviz":
        lines = ["digraph Topology {"]
        lines.append("    rankdir=LR;")
        
        # Add ASes
        for asn in base.getAsns():
            asys = base.getAutonomousSystem(asn)
            lines.append(f"    subgraph cluster_AS{asn} {{")
            lines.append(f'        label="AS{asn}";')
            
            for r_name in asys.getRouters():
                lines.append(f'        {r_name} [shape=ellipse];')
            for h_name in asys.getHosts():
                lines.append(f'        {h_name} [shape=box];')
            
            lines.append("    }")
        
        lines.append("}")
        return "\n".join(lines)
    
    else:
        return f"Error: Unknown format '{format}'. Supported: json, mermaid, graphviz"


@mcp.tool()
def export_python_script(filepath: str = "") -> str:
    """Export the logged API calls as a Python script.
    
    Args:
        filepath: Optional file path to save the script. If empty, returns the script content.
    
    Returns:
        The Python script content or confirmation of file save.
    """
    code_log = runtime.get_code_log()
    
    script_lines = [
        "#!/usr/bin/env python3",
        "\"\"\"Auto-generated SEED Emulator script.\"\"\"",
        "",
        "from seedemu.core import Emulator",
        "from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf",
        "from seedemu.compiler import Docker",
        "from seedemu.services import WebService, DomainNameService",
        "",
        "# Create emulator and layers",
        "emulator = Emulator()",
        "base = Base()",
        "emulator.addLayer(base)",
        "",
        "# Generated API calls",
    ]
    
    script_lines.extend(code_log)
    
    script_lines.extend([
        "",
        "# Render and compile",
        "emulator.render()",
        "# docker = Docker()",
        "# docker.compile(emulator, './output')",
    ])
    
    script_content = "\n".join(script_lines)
    
    if filepath:
        try:
            with open(filepath, 'w') as f:
                f.write(script_content)
            return f"Python script saved to {filepath}"
        except Exception as e:
            return f"Error saving script: {str(e)}"
    else:
        return script_content

# ==============================================================================
# Docker Tools (Build & Deploy)
# ==============================================================================

def _get_docker_compose_cmd():
    """Return the correct docker compose command for this system."""
    import subprocess
    # Try docker compose (v2) first
    try:
        result = subprocess.run(["docker", "compose", "version"], 
                                capture_output=True, timeout=5)
        if result.returncode == 0:
            return ["docker", "compose"]
    except:
        pass
    # Fall back to docker-compose (v1)
    return ["docker-compose"]

@mcp.tool()
def compile_simulation(output_dir: str) -> str:
    """Compile the rendered simulation to Docker Compose files.
    
    Args:
        output_dir: Path to the output directory for Docker files.
    """
    emulator = runtime.get_emulator()
    
    if not emulator.rendered():
        return "Error: Simulation not rendered. Call render_simulation first."
    
    import os
    from seedemu.compiler import Docker
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Compile to Docker
        docker_compiler = Docker()
        
        # Attach EmailService if registered
        if hasattr(runtime, 'email_service'):
            runtime.email_service.attach_to_docker(docker_compiler)
            runtime.log_code(f"email_svc.attach_to_docker(docker)")
        
        docker_compiler.compile(emulator, output_dir, override=True)
        
        # Run output callbacks for email wrapper Dockerfiles
        if hasattr(runtime, 'email_service'):
            import os as os_module
            prev_cwd = os_module.getcwd()
            os_module.chdir(output_dir)
            for cb in runtime.email_service.get_output_callbacks():
                try:
                    cb(docker_compiler)
                except:
                    pass  # Ignore callback errors
            os_module.chdir(prev_cwd)
        
        runtime.output_dir = os.path.abspath(output_dir)
        runtime.log_code(f"docker = Docker()")
        runtime.log_code(f"docker.compile(emulator, '{output_dir}')")
        
        return f"Compiled simulation to Docker files in '{output_dir}'."
    except Exception as e:
        return f"Error compiling simulation: {str(e)}"

@mcp.tool()
def build_images() -> str:
    """Build Docker images for the simulation.
    
    Must be called after compile_simulation.
    """
    if not runtime.output_dir:
        return "Error: No output directory set. Call compile_simulation first."
    
    import subprocess
    
    try:
        result = subprocess.run(
            _get_docker_compose_cmd() + ["build"],
            cwd=runtime.output_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode != 0:
            return f"Error building images: {result.stderr}"
        
        return "Docker images built successfully."
    except subprocess.TimeoutExpired:
        return "Error: Build timed out after 10 minutes."
    except Exception as e:
        return f"Error building images: {str(e)}"

@mcp.tool()
def start_simulation() -> str:
    """Start the simulation (docker compose up).
    
    Must be called after build_images.
    """
    if not runtime.output_dir:
        return "Error: No output directory set. Call compile_simulation first."
    
    import subprocess
    
    try:
        result = subprocess.run(
            _get_docker_compose_cmd() + ["up", "-d"],
            cwd=runtime.output_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return f"Error starting simulation: {result.stderr}"
        
        return "Simulation started. Containers are running."
    except Exception as e:
        return f"Error starting simulation: {str(e)}"

@mcp.tool()
def stop_simulation() -> str:
    """Stop the simulation (docker compose down)."""
    if not runtime.output_dir:
        return "Error: No output directory set."
    
    import subprocess
    
    try:
        result = subprocess.run(
            _get_docker_compose_cmd() + ["down"],
            cwd=runtime.output_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return f"Error stopping simulation: {result.stderr}"
        
        return "Simulation stopped. Containers removed."
    except Exception as e:
        return f"Error stopping simulation: {str(e)}"

@mcp.tool()
def list_containers() -> str:
    """List all running containers in the simulation."""
    try:
        docker_client = runtime.get_docker_client()
        containers = docker_client.containers.list()
        
        result = []
        for c in containers:
            result.append({
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else "unknown"
            })
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error listing containers: {str(e)}"

# ==============================================================================
# Dynamic Runtime Tools (Container Interaction)
# ==============================================================================

@mcp.tool()
def exec_command(container_name: str, command: str) -> str:
    """Execute a command inside a running container.
    
    Args:
        container_name: Name of the container.
        command: Command to execute (e.g., 'ip route').
    """
    try:
        docker_client = runtime.get_docker_client()
        container = docker_client.containers.get(container_name)
        
        result = container.exec_run(command, demux=False)
        output = result.output.decode('utf-8', errors='replace')
        
        return f"Exit code: {result.exit_code}\n{output}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

@mcp.tool()
def get_logs(container_name: str, tail: int = 50) -> str:
    """Get logs from a container.
    
    Args:
        container_name: Name of the container.
        tail: Number of lines to return (default 50).
    """
    try:
        docker_client = runtime.get_docker_client()
        container = docker_client.containers.get(container_name)
        
        logs = container.logs(tail=tail).decode('utf-8', errors='replace')
        return logs
    except Exception as e:
        return f"Error getting logs: {str(e)}"

@mcp.tool()
def ping_test(src_container: str, dst_ip: str, count: int = 4) -> str:
    """Test network connectivity using ping.
    
    Args:
        src_container: Name of the source container.
        dst_ip: Destination IP address or hostname.
        count: Number of ping packets (default 4).
    """
    return exec_command(src_container, f"ping -c {count} {dst_ip}")

@mcp.tool()
def get_routing_table(container_name: str) -> str:
    """Get the routing table from a container.
    
    Args:
        container_name: Name of the container.
    """
    return exec_command(container_name, "ip route")

@mcp.tool()
def get_bgp_status(container_name: str) -> str:
    """Get BGP protocol status from a router container.
    
    Args:
        container_name: Name of the router container.
    """
    # SEED uses BIRD for routing
    return exec_command(container_name, "birdc show protocol")

@mcp.tool()
def traceroute(src_container: str, dst_ip: str) -> str:
    """Trace the path to a destination IP.
    
    Args:
        src_container: Name of the source container.
        dst_ip: Destination IP address.
    """
    # Try different traceroute commands
    cmd = f"sh -c 'traceroute -n {dst_ip} || tracepath -n {dst_ip}'"
    return exec_command(src_container, cmd)

@mcp.tool()
def capture_traffic(
    container_name: str,
    interface: str = "eth0",
    duration: int = 10,
    filter: str = ""
) -> str:
    """Capture network traffic on a container interface.
    
    Args:
        container_name: Name of the container.
        interface: Network interface (default eth0).
        duration: Capture duration in seconds (default 10).
        filter: Tcpdump filter expression (e.g., "port 80").
    """
    # Use timeout to stop tcpdump after duration
    cmd = f"timeout {duration} tcpdump -i {interface} -n {filter}"
    return exec_command(container_name, cmd)

@mcp.tool()
def get_interface_stats(container_name: str) -> str:
    """Get network interface statistics (bytes/packets).
    
    Args:
        container_name: Name of the container.
    """
    return exec_command(container_name, "ip -s -j link show")

# ==============================================================================
# BGP Security Tools
# ==============================================================================

@mcp.tool()
def bgp_announce_prefix(
    router_container: str,
    prefix: str,
    next_hop: str = ""
) -> str:
    """Announce a BGP prefix from a router (for hijacking simulations).
    
    This injects a static route and configures BIRD to redistribute it via BGP.
    WARNING: Use only for security research/education.
    
    Args:
        router_container: Name of the router container (must run BIRD).
        prefix: IP prefix to announce (e.g., "10.100.0.0/24").
        next_hop: Optional next-hop IP (defaults to router's own IP).
    
    Example:
        bgp_announce_prefix("as666brd-attacker", "10.150.0.0/24")
    """
    # Step 1: Add static route to kernel
    route_cmd = f"ip route add {prefix} dev lo 2>/dev/null || true"
    exec_command(router_container, route_cmd)
    
    # Step 2: Configure BIRD to redistribute kernel routes
    # This requires the protocol kernel { } to have export all or similar
    # We add a static route in BIRD directly for more control
    bird_cmd = f'''birdc << EOF
configure soft
protocol static hijack_{prefix.replace('/', '_').replace('.', '_')} {{
    route {prefix} blackhole;
}}
EOF'''
    result = exec_command(router_container, f"sh -c '{bird_cmd}'")
    
    return f"Announced prefix {prefix} from {router_container}. BIRD output: {result[:200]}"

@mcp.tool()
def get_looking_glass(router_container: str, prefix: str = "") -> str:
    """Query BGP routes from a router (looking glass).
    
    Args:
        router_container: Name of the router container.
        prefix: Optional prefix to filter (e.g., "10.100.0.0/24"). If empty, shows all routes.
    
    Example:
        get_looking_glass("as100brd-r100", "10.200.0.0/24")
    """
    if prefix:
        cmd = f"birdc 'show route for {prefix} all'"
    else:
        cmd = "birdc 'show route'"
    return exec_command(router_container, cmd)

# ==============================================================================
# Dynamic Operations Tools (Phase 13)
# ==============================================================================

@mcp.tool()
def inject_fault(
    container_name: str,
    fault_type: str,
    params: str = ""
) -> str:
    """Inject a network fault into a container for testing/debugging.
    
    Supports various fault types for chaos engineering and debugging.
    
    Args:
        container_name: Name of the target container.
        fault_type: Type of fault to inject:
            - "packet_loss": Simulate packet loss (params: percentage, e.g., "10")
            - "latency": Add network latency (params: milliseconds, e.g., "100")
            - "bandwidth": Limit bandwidth (params: rate, e.g., "1mbit")
            - "kill_process": Kill a process (params: process name, e.g., "bird")
            - "disconnect": Disconnect a network interface (params: interface, e.g., "eth0")
            - "reset": Clear all injected faults
        params: Fault-specific parameters.
    
    Examples:
        inject_fault("as150_host", "packet_loss", "20")
        inject_fault("as150_router", "latency", "50")
        inject_fault("as150_router", "kill_process", "bird")
    """
    fault_type = fault_type.lower()
    
    if fault_type == "packet_loss":
        percent = params or "10"
        cmd = f"tc qdisc add dev eth0 root netem loss {percent}%"
        result = exec_command(container_name, cmd)
        return f"Injected {percent}% packet loss on {container_name}: {result}"
    
    elif fault_type == "latency":
        ms = params or "100"
        cmd = f"tc qdisc add dev eth0 root netem delay {ms}ms"
        result = exec_command(container_name, cmd)
        return f"Injected {ms}ms latency on {container_name}: {result}"
    
    elif fault_type == "bandwidth":
        rate = params or "1mbit"
        cmd = f"tc qdisc add dev eth0 root tbf rate {rate} burst 32kbit latency 400ms"
        result = exec_command(container_name, cmd)
        return f"Limited bandwidth to {rate} on {container_name}: {result}"
    
    elif fault_type == "kill_process":
        process = params or "bird"
        cmd = f"pkill -9 {process} 2>/dev/null || echo 'Process not found'"
        result = exec_command(container_name, cmd)
        return f"Killed process '{process}' on {container_name}: {result}"
    
    elif fault_type == "disconnect":
        iface = params or "eth0"
        cmd = f"ip link set {iface} down"
        result = exec_command(container_name, cmd)
        return f"Disconnected interface {iface} on {container_name}: {result}"
    
    elif fault_type == "reset":
        cmd = "tc qdisc del dev eth0 root 2>/dev/null || true"
        result = exec_command(container_name, cmd)
        return f"Cleared all network faults on {container_name}: {result}"
    
    else:
        return f"Error: Unknown fault type '{fault_type}'. Valid types: packet_loss, latency, bandwidth, kill_process, disconnect, reset"


@mcp.tool()
def start_attack_scenario(
    scenario_name: str,
    attacker_container: str,
    target: str,
    params: str = ""
) -> str:
    """Start a predefined attack scenario for security research/education.
    
    WARNING: Use only in controlled lab environments for educational purposes.
    
    Args:
        scenario_name: Attack scenario to execute:
            - "bgp_hijack": Announce target's prefix from attacker's router
            - "bgp_leak": Leak routes from one AS to another
            - "dos_flood": Simple ICMP flood (limited rate)
            - "arp_spoof": ARP spoofing attack
        attacker_container: Container to launch attack from.
        target: Target of the attack (IP, prefix, or container name).
        params: Additional scenario-specific parameters.
    
    Examples:
        start_attack_scenario("bgp_hijack", "as666_router", "10.150.0.0/24")
        start_attack_scenario("dos_flood", "as666_host", "10.150.0.1", "100")
    """
    scenario_name = scenario_name.lower()
    
    if scenario_name == "bgp_hijack":
        # Uses existing bgp_announce_prefix tool
        result = bgp_announce_prefix(attacker_container, target)
        return f"BGP Hijack scenario started:\n{result}\n\nVerify with: get_looking_glass(<victim_router>, \"{target}\")"
    
    elif scenario_name == "bgp_leak":
        # Announce with specific attributes
        result = bgp_announce_prefix(attacker_container, target)
        return f"BGP Leak scenario started:\n{result}"
    
    elif scenario_name == "dos_flood":
        # Rate-limited ping flood
        count = params or "100"
        cmd = f"ping -f -c {count} {target} 2>&1 || echo 'Flood complete'"
        result = exec_command(attacker_container, cmd)
        return f"DoS flood sent ({count} packets) to {target}:\n{result[:500]}"
    
    elif scenario_name == "arp_spoof":
        # Simple ARP poisoning (requires arpspoof tool)
        gateway = params or "10.0.0.1"
        cmd = f"timeout 10 arpspoof -t {target} {gateway} 2>&1 || echo 'ARP spoof attempt complete'"
        result = exec_command(attacker_container, cmd)
        return f"ARP Spoof scenario executed:\n{result[:500]}"
    
    else:
        return f"Error: Unknown scenario '{scenario_name}'. Valid: bgp_hijack, bgp_leak, dos_flood, arp_spoof"


@mcp.tool()
def capture_evidence(
    container_name: str,
    evidence_type: str,
    output_file: str = ""
) -> str:
    """Capture forensic evidence from a container.
    
    Collects system state for analysis and documentation.
    
    Args:
        container_name: Container to collect evidence from.
        evidence_type: Type of evidence to collect:
            - "routing_snapshot": Current routing table and BGP state
            - "network_state": Interfaces, ARP table, connections
            - "process_list": Running processes
            - "logs": System and application logs
            - "pcap": Start packet capture (requires stop_capture later)
            - "full": Collect all of the above
        output_file: Optional output filename (for pcap).
    
    Returns:
        Collected evidence as text or status message.
    """
    evidence_type = evidence_type.lower()
    results = []
    
    if evidence_type in ("routing_snapshot", "full"):
        results.append("=== ROUTING TABLE ===")
        results.append(exec_command(container_name, "ip route"))
        results.append("\n=== BGP STATUS ===")
        results.append(exec_command(container_name, "birdc show protocol 2>/dev/null || echo 'No BIRD'"))
        results.append("\n=== BGP ROUTES ===")
        results.append(exec_command(container_name, "birdc 'show route' 2>/dev/null || echo 'No BIRD'"))
    
    if evidence_type in ("network_state", "full"):
        results.append("\n=== INTERFACES ===")
        results.append(exec_command(container_name, "ip addr"))
        results.append("\n=== ARP TABLE ===")
        results.append(exec_command(container_name, "ip neigh"))
        results.append("\n=== ACTIVE CONNECTIONS ===")
        results.append(exec_command(container_name, "ss -tuln 2>/dev/null || netstat -tuln"))
    
    if evidence_type in ("process_list", "full"):
        results.append("\n=== PROCESSES ===")
        results.append(exec_command(container_name, "ps aux"))
    
    if evidence_type in ("logs", "full"):
        results.append("\n=== SYSLOG (last 50 lines) ===")
        results.append(exec_command(container_name, "tail -50 /var/log/syslog 2>/dev/null || echo 'No syslog'"))
        results.append("\n=== DMESG (last 20 lines) ===")
        results.append(exec_command(container_name, "dmesg | tail -20 2>/dev/null || echo 'No dmesg'"))
    
    if evidence_type == "pcap":
        filename = output_file or f"/tmp/capture_{container_name}.pcap"
        cmd = f"nohup tcpdump -i any -w {filename} &"
        exec_command(container_name, cmd)
        return f"Packet capture started on {container_name}. Output: {filename}\nStop with: exec_command(\"{container_name}\", \"pkill tcpdump\")"
    
    if not results:
        return f"Error: Unknown evidence type '{evidence_type}'. Valid: routing_snapshot, network_state, process_list, logs, pcap, full"
    
    return "\n".join(results)


# ==============================================================================
# Helper Resources
# ==============================================================================

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

# ==============================================================================
# Example Loader Tools (Phase 10)
# ==============================================================================

@mcp.tool()
def list_examples(category: str = "") -> str:
    """List available SEED emulator examples.
    
    Args:
        category: Optional category filter (basic, internet, blockchain, scion, wireless).
                  If empty, lists all categories.
    
    Returns:
        JSON list of available examples with descriptions.
    """
    examples_dir = runtime.examples_dir
    
    if not os.path.exists(examples_dir):
        return json.dumps({"error": f"Examples directory not found: {examples_dir}"})
    
    result = {}
    
    # Get categories
    categories = ["basic", "internet", "blockchain", "scion", "wireless"]
    if category:
        categories = [category] if category in categories else []
    
    for cat in categories:
        cat_dir = os.path.join(examples_dir, cat)
        if not os.path.isdir(cat_dir):
            continue
            
        examples = []
        for item in sorted(os.listdir(cat_dir)):
            item_path = os.path.join(cat_dir, item)
            if os.path.isdir(item_path):
                # Try to find main Python file
                py_files = [f for f in os.listdir(item_path) if f.endswith('.py') and not f.startswith('_')]
                if py_files:
                    examples.append({
                        "name": item,
                        "path": f"{cat}/{item}",
                        "script": py_files[0]
                    })
        
        if examples:
            result[cat] = examples
    
    return json.dumps(result, indent=2)


@mcp.tool()
def load_example(example_path: str) -> str:
    """Load an example into the runtime without compiling.
    
    This runs the example's run() function with dumpfile=True to capture the topology
    into memory without generating Docker files.
    
    Args:
        example_path: Path relative to examples/ (e.g., "basic/A00_simple_as")
    
    Returns:
        Status message with topology summary.
    """
    from runtime import AgentPhase
    
    examples_dir = runtime.examples_dir
    full_path = os.path.join(examples_dir, example_path)
    
    if not os.path.isdir(full_path):
        return f"Error: Example not found: {example_path}"
    
    # Find Python script
    py_files = [f for f in os.listdir(full_path) if f.endswith('.py') and not f.startswith('_')]
    if not py_files:
        return f"Error: No Python script found in {example_path}"
    
    script_path = os.path.join(full_path, py_files[0])
    
    try:
        # Reset runtime for fresh load
        runtime.reset()
        runtime.set_phase(AgentPhase.DESIGNING)
        runtime.current_example = example_path
        
        # Import and run the example module
        import importlib.util
        spec = importlib.util.spec_from_file_location("example_module", script_path)
        module = importlib.util.module_from_spec(spec)
        
        # Add examples parent to path for relative imports
        sys.path.insert(0, examples_dir)
        sys.path.insert(0, full_path)
        
        spec.loader.exec_module(module)
        
        # Check if module has run() function
        if hasattr(module, 'run'):
            # Use dumpfile to capture state without compiling
            dumpfile = os.path.join(full_path, 'output', '_loaded_state.bin')
            os.makedirs(os.path.dirname(dumpfile), exist_ok=True)
            module.run(dumpfile=dumpfile)
            
            # Load the dumped state into our runtime
            runtime.emulator.load(dumpfile)
            runtime.base = runtime.emulator.getLayer('Base')
        else:
            return f"Error: Example {example_path} has no run() function"
        
        # Generate summary
        base = runtime.get_base()
        summary = {
            "example": example_path,
            "status": "loaded",
            "topology": {
                "autonomous_systems": list(base.getAsns()),
                "internet_exchanges": list(base.getInternetExchangeIds())
            }
        }
        
        return json.dumps(summary, indent=2)
        
    except Exception as e:
        import traceback
        return f"Error loading example: {str(e)}\n{traceback.format_exc()}"
    finally:
        # Clean up path
        if examples_dir in sys.path:
            sys.path.remove(examples_dir)
        if full_path in sys.path:
            sys.path.remove(full_path)


@mcp.tool()
def run_example(example_path: str, platform: str = "amd") -> str:
    """Fully run an example: load, compile, build, and start containers.
    
    Args:
        example_path: Path relative to examples/ (e.g., "basic/A00_simple_as")
        platform: Target platform: "amd" or "arm" (default: amd)
    
    Returns:
        Status message with running container info.
    """
    from runtime import AgentPhase
    
    # Step 1: Load example
    load_result = load_example(example_path)
    if "Error" in load_result:
        return load_result
    
    runtime.set_phase(AgentPhase.COMPILING)
    
    # Step 2: Render
    render_result = render_simulation()
    if "Error" in render_result:
        return f"Render failed: {render_result}"
    
    # Step 3: Compile
    output_dir = os.path.join(runtime.examples_dir, example_path, 'output')
    compile_result = compile_simulation(output_dir)
    if "Error" in compile_result:
        return f"Compile failed: {compile_result}"
    
    # Step 4: Build
    build_result = build_images()
    if "Error" in build_result:
        return f"Build failed: {build_result}"
    
    runtime.set_phase(AgentPhase.RUNNING)
    
    # Step 5: Start
    start_result = start_simulation()
    if "Error" in start_result:
        return f"Start failed: {start_result}"
    
    return json.dumps({
        "example": example_path,
        "status": "running",
        "output_dir": output_dir,
        "message": "Simulation started successfully. Use list_containers() to see running nodes."
    }, indent=2)


# ==============================================================================
# Agent State Awareness Tools (Phase 11)
# ==============================================================================

@mcp.tool()
def get_agent_state() -> str:
    """Get current agent state including phase, loaded example, and topology summary.
    
    Returns:
        JSON object with current agent state.
    """
    from runtime import AgentPhase
    
    base = runtime.get_base()
    emulator = runtime.get_emulator()
    
    # Get running containers if any
    running_containers = []
    try:
        docker_client = runtime.get_docker_client()
        containers = docker_client.containers.list()
        running_containers = [c.name for c in containers if 'seed' in c.name.lower() or 'as' in c.name.lower()]
    except:
        pass
    
    state = {
        "phase": runtime.get_phase().value,
        "current_example": runtime.current_example,
        "is_rendered": emulator.rendered(),
        "output_dir": runtime.output_dir,
        "topology": {
            "autonomous_systems": list(base.getAsns()),
            "internet_exchanges": list(base.getInternetExchangeIds()),
            "total_nodes": sum(
                len(base.getAutonomousSystem(asn).getRouters()) + 
                len(base.getAutonomousSystem(asn).getHosts())
                for asn in base.getAsns()
            ) if base.getAsns() else 0
        },
        "running_containers": running_containers[:10]  # Limit to 10
    }
    
    return json.dumps(state, indent=2)


@mcp.tool()
def discover_running_simulation() -> str:
    """Discover any running SEED simulation in the Docker environment.
    
    Scans Docker for containers that appear to be SEED emulator nodes.
    
    Returns:
        JSON object with discovered simulation info.
    """
    try:
        docker_client = runtime.get_docker_client()
        containers = docker_client.containers.list()
        
        # Filter for SEED-like containers (patterns: as*, ix*, *node*, *router*, *host*)
        seed_containers = []
        for c in containers:
            name = c.name.lower()
            if any(pattern in name for pattern in ['as', 'ix', 'node', 'router', 'host', 'brd']):
                seed_containers.append({
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown"
                })
        
        if not seed_containers:
            return json.dumps({
                "found": False,
                "message": "No running SEED simulation detected."
            })
        
        return json.dumps({
            "found": True,
            "container_count": len(seed_containers),
            "containers": seed_containers[:20]  # Limit
        }, indent=2)
        
    except Exception as e:
        return f"Error discovering simulation: {str(e)}"


@mcp.tool()
def attach_to_simulation(output_dir: str) -> str:
    """Attach to an existing running simulation.
    
    Sets the runtime to operate on containers in the specified output directory.
    
    Args:
        output_dir: Path to the output directory containing docker-compose.yml
    
    Returns:
        Status message.
    """
    from runtime import AgentPhase
    
    if not os.path.exists(output_dir):
        return f"Error: Directory not found: {output_dir}"
    
    compose_file = os.path.join(output_dir, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        return f"Error: No docker-compose.yml found in {output_dir}"
    
    runtime.output_dir = os.path.abspath(output_dir)
    runtime.set_phase(AgentPhase.OPERATING)
    
    # Verify containers are running
    discover_result = discover_running_simulation()
    
    return json.dumps({
        "attached": True,
        "output_dir": runtime.output_dir,
        "phase": runtime.get_phase().value,
        "discovery": json.loads(discover_result)
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
