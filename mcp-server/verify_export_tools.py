#!/usr/bin/env python3
"""
LLM Integration Test for Export Tools
Tests that an LLM can correctly use the export topology tools and Python script export.
"""

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import (
    create_as, create_node, connect_nodes,
    get_topology_summary, export_topology, export_python_script
)
from runtime import runtime

load_dotenv()

api_key = os.environ.get("MIMO_API_KEY")
if not api_key:
    # Use a dummy key if not present for local testing without API (mock mode would be needed)
    # But for this environment, we expect it.
    print("Skipping LLM test: MIMO_API_KEY not found.")
    sys.exit(0)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.xiaomimimo.com/v1"
)

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_as",
            "description": "Create an Autonomous System.",
            "parameters": {
                "type": "object",
                "properties": {"asn": {"type": "integer"}},
                "required": ["asn"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_node",
            "description": "Create a router or host in an AS.",
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
            "name": "get_topology_summary",
            "description": "Get a human-readable summary of the current topology.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_topology",
            "description": "Export the current topology in various formats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["json", "mermaid", "graphviz"]}
                },
                "required": ["format"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_python_script",
            "description": "Export the logged API calls as a Python script.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"}
                }
            }
        }
    }
]

tool_map = {
    "create_as": create_as,
    "create_node": create_node,
    "get_topology_summary": get_topology_summary,
    "export_topology": export_topology,
    "export_python_script": export_python_script
}

def run_export_test():
    print("=" * 60)
    print("LLM Export Tools Integration Test")
    print("=" * 60)
    
    runtime.reset()
    
    messages = [
        {"role": "system", "content": "You are a network simulation assistant. Use the provided tools."},
        {"role": "user", "content": """
1. Create AS200 with router 'r1'
2. Get the topology summary to confirm
3. Export the topology as a Mermaid graph
4. Export the python script to 'reproduce_topology.py'
"""}
    ]
    
    for turn in range(10):
        response = client.chat.completions.create(
            model="mimo-v2-flash",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        
        msg = response.choices[0].message
        print(f"\n[Turn {turn+1}] {msg.content or '(Tool calls)'}")
        
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                print(f"  -> {fn_name}({fn_args})")
                
                if fn_name in tool_map:
                    try:
                        result = tool_map[fn_name](**fn_args)
                    except Exception as e:
                        result = str(e)
                else:
                    result = f"Unknown tool: {fn_name}"
                
                # Truncate long results for display
                print(f"     Result: {result[:100]}..." if len(str(result)) > 100 else f"     Result: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })
        else:
            break
    
    # Verify
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    success = True
    
    # Check creation
    try:
        base = runtime.get_base()
        as200 = base.getAutonomousSystem(200)
        print("✅ AS200 created")
    except:
        print("❌ AS200 not found")
        success = False
        
    # Check file export
    if os.path.exists("reproduce_topology.py"):
        print("✅ reproduce_topology.py created")
        with open("reproduce_topology.py", 'r') as f:
            content = f.read()
            if "createAutonomousSystem(200)" in content:
                print("✅ Script content verified")
            else:
                print("❌ Script content missing expected calls")
                success = False
        # Clean up
        os.remove("reproduce_topology.py")
    else:
        print("❌ reproduce_topology.py not found")
        success = False
    
    if success:
        print("\n✅ LLM Export Tools Test PASSED")
    else:
        print("\n❌ LLM Export Tools Test FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(run_export_test())
