from mcp.server.fastmcp import FastMCP
import json
import sys
import os

# Add parent directory to path to import seedemu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runtime import runtime

mcp = FastMCP("seed-emulator-mcp")

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
