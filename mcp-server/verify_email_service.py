#!/usr/bin/env python3
"""
LLM Integration Test for Email Service
Tests that an LLM can correctly use the email service tool.
"""

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import (
    create_as, create_node, connect_nodes,
    enable_routing_layers, render_simulation,
    install_email_service, list_email_providers
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

# Tool definitions including email service
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
            "name": "connect_nodes",
            "description": "Connect two nodes together.",
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
            "name": "install_email_service",
            "description": "Install an email server for a domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Email domain like example.com"},
                    "asn": {"type": "integer"},
                    "ip": {"type": "string", "description": "IP address for email server"},
                    "gateway": {"type": "string", "description": "Default gateway IP"}
                },
                "required": ["domain", "asn", "ip", "gateway"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_email_providers",
            "description": "List all registered email providers.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enable_routing_layers",
            "description": "Enable routing layers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layers": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["layers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "render_simulation",
            "description": "Render the simulation.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

tool_map = {
    "create_as": create_as,
    "create_node": create_node,
    "connect_nodes": connect_nodes,
    "install_email_service": install_email_service,
    "list_email_providers": list_email_providers,
    "enable_routing_layers": enable_routing_layers,
    "render_simulation": render_simulation
}

def run_email_test():
    print("=" * 60)
    print("LLM Email Service Integration Test")
    print("=" * 60)
    
    runtime.reset()
    if hasattr(runtime, 'email_service'):
        delattr(runtime, 'email_service')
    
    messages = [
        {"role": "system", "content": "You are a network simulation assistant. Use the provided tools."},
        {"role": "user", "content": """
Create a simple email network:
1. Create AS100 with a router 'r1' and a host 'mailserver'
2. Connect the host to the router
3. Install an email service for domain 'company.com' on the mailserver with IP 10.100.0.10 and gateway 10.100.0.254
4. List the email providers to confirm
5. Enable routing and render the simulation
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
                    result = tool_map[fn_name](**fn_args)
                else:
                    result = f"Unknown tool: {fn_name}"
                
                print(f"     Result: {result[:100]}..." if len(result) > 100 else f"     Result: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
        else:
            break
    
    # Verify
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    success = True
    
    # Check AS created
    try:
        base = runtime.get_base()
        as100 = base.getAutonomousSystem(100)
        print("✅ AS100 created")
    except:
        print("❌ AS100 not found")
        success = False
    
    # Check email service registered
    if hasattr(runtime, 'email_service'):
        providers = runtime.email_service.get_providers()
        if any(p['domain'] == 'company.com' for p in providers):
            print("✅ Email service for company.com registered")
        else:
            print("❌ Email service for company.com not found")
            success = False
    else:
        print("❌ No email service registered")
        success = False
    
    if success:
        print("\n✅ LLM Email Service Test PASSED")
    else:
        print("\n❌ LLM Email Service Test FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(run_email_test())
