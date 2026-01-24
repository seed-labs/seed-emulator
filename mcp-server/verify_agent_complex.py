import os
import sys
import json
import inspect
from dotenv import load_dotenv
from openai import OpenAI

# Add current directory to path (mcp-server)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Add parent directory to path (seed-email-service) for runtime imports if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import (
    create_as, create_ix, create_node, connect_nodes, connect_to_ix,
    enable_routing_layers, configure_direct_peering, configure_ix_peering,
    install_service, render_simulation
)
from runtime import runtime

load_dotenv()

api_key = os.environ.get("MIMO_API_KEY")
if not api_key:
    print("Skipping LLM test: MIMO_API_KEY not found.")
    sys.exit(0)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.xiaomimimo.com/v1"
)

# 1. Define Tools Schema manually (Simplified for this test script)
# Ideally we extract this from the functions automatically.
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_as",
            "description": "Create an Autonomous System (AS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "asn": {"type": "integer", "description": "The ASN (e.g. 100)"}
                },
                "required": ["asn"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_node",
            "description": "Create a node (Router/Host) in an AS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "asn": {"type": "integer"},
                    "role": {"type": "string", "enum": ["router", "host"]}
                },
                "required": ["name", "asn", "role"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "connect_nodes",
            "description": "Connect two nodes with a direct link (P2P or Cross-Connect).",
            "parameters": {
                "type": "object",
                "properties": {
                    "node1_name": {"type": "string"},
                    "node2_name": {"type": "string"}
                },
                "required": ["node1_name", "node2_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_service",
            "description": "Install a service on a node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_name": {"type": "string"},
                    "service_type": {"type": "string", "enum": ["WebService", "DomainNameService"]},
                    "params": {"type": "string", "description": "JSON string of params"}
                },
                "required": ["node_name", "service_type", "params"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enable_routing_layers",
            "description": "Enable specific routing layers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layers": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["routing", "ospf", "ibgp", "ebgp", "mpls"]}
                    }
                },
                "required": ["layers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "render_simulation",
            "description": "Finalize and render the simulation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Map names to functions
tool_map = {
    "create_as": create_as,
    "create_node": create_node,
    "connect_nodes": connect_nodes,
    "install_service": install_service,
    "enable_routing_layers": enable_routing_layers,
    "render_simulation": render_simulation
}

def run_conversation():
    print("Starting Agentic Verification...")
    runtime.reset()
    
    messages = [
        {"role": "system", "content": "You are a network simulation assistant. Use the tools provided to build the requested topology."},
        {"role": "user", "content": "Create a network with two ASes: AS100 and AS200. Create a router 'r1' in AS100 and a router 'r2' in AS200. Connect 'r1' and 'r2' directly. Create a host 'web1' in AS100 and connect it to 'r1'. Install a WebService on 'web1' with url 'www.test.com'. Enable necessary routing layers (including 'routing') and then render the simulation."}
    ]
    
    # Max turns
    for _ in range(10):
        response = client.chat.completions.create(
            model="mimo-v2-flash",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        
        msg = response.choices[0].message
        print(f"\nAssistant: {msg.content or '(Tool Call)'}")
        
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f" > Call: {func_name}({args})")
                
                if func_name in tool_map:
                    # Call the actual local function 
                    # Note: These functions might be decorated by FastMCP, returning the result directly?
                    # or need special handling. 
                    # FastMCP decorator usually wraps the function but returns original result if called directly.
                    try:
                        result = tool_map[func_name](**args)
                    except Exception as e:
                        result = f"Error: {e}"
                        
                    print(f" < Result: {result}")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                else:
                    print(f"Error: Tool {func_name} not found in map")
        else:
            messages.append(msg)
            if "render" in msg.content.lower() or "done" in msg.content.lower():
                break
                
    # Final Verification
    print("\n--- Verification ---")
    base = runtime.get_base()
    as100 = base.getAutonomousSystem(100)
    as200 = base.getAutonomousSystem(200)
    
    if as100 and as200:
        print("PASS: AS100 and AS200 created.")
    else:
        print("FAIL: ASes not created.")
        
    if as100.getRouter('r1') and as200.getRouter('r2'):
        print("PASS: Routers created.")
    else:
        print("FAIL: Routers not created.")
        
    web1 = as100.getHost('web1')
    if web1:
        print("PASS: Host web1 created.")
        services = web1.getAttribute('services', {})
        if 'WebService' in services:
             print("PASS: WebService installed.")
        else:
             print("FAIL: WebService not found on web1.")
    else:
        print("FAIL: Host web1 not created.")
        
    if runtime.get_emulator().rendered():
        print("PASS: Simulation rendered.")
    else:
        print("FAIL: Simulation not rendered.")

if __name__ == '__main__':
    run_conversation()
