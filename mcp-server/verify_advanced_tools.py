#!/usr/bin/env python3
# verify_advanced_tools.py

import os
import sys
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

# Add parent directory to path to find mcp_server modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration
SERVER_SCRIPT = "/home/parallels/seed-email-service/mcp-server/server.py"

async def run_verification():
    print("Starting Advanced Tools Verification...")
    
    server_params = StdioServerParameters(
        command="python3",
        args=[SERVER_SCRIPT],
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Helper to call tool and print result
            async def call(tool_name, **kwargs):
                print(f"\n[CALLing] {tool_name} with {kwargs}")
                try:
                    result: CallToolResult = await session.call_tool(tool_name, arguments=kwargs)
                    output = result.content[0].text
                    print(f"[RESULT] {output}")
                    return output
                except Exception as e:
                    print(f"[ERROR] {str(e)}")
                    return str(e)

            # 1. Setup Base Topology (AS 100 Provider, AS 200 Customer)
            await call("create_as", asn=100)
            await call("create_as", asn=200)
            
            await call("create_node", name="router100", asn=100, role="router")
            await call("create_node", name="router200", asn=200, role="router")
            
            # Connect them so they have interfaces (required for Routing layer)
            await call("connect_nodes", node1_name="router100", node2_name="router200")
            
            # 2. Test MPLS Tools
            print("\n--- Verifying MPLS Tools ---")
            await call("enable_routing_layers", layers=["routing", "mpls"])
            await call("enable_mpls_on_as", asn=100)
            await call("mark_mpls_edge", asn=100, node_name="router100")
            
            # 3. Test EVPN Tools
            print("\n--- Verifying EVPN Tools ---")
            await call("enable_routing_layers", layers=["evpn"])
            await call("create_evpn_customer", 
                       provider_asn=100, 
                       customer_asn=200, 
                       vni=1001, 
                       pe_router="router100", 
                       customer_net="net0") # net0 will be created implicitly by some tools or should exist? let's see errors
            
            # 4. Test Service Configuration Tools
            print("\n--- Verifying Service Tools (Web, DNS, Botnet) ---")
            await call("create_node", name="web_server", asn=200, role="host")
            await call("configure_web_server", 
                       node_name="web_server", 
                       url="www.secure-bank.com", 
                       index_html="<h1>Welcome to Secure Bank</h1>")
            
            await call("create_node", name="dns_server", asn=200, role="host")
            await call("configure_dns_zone", 
                       zone_name="secure-bank.com", 
                       records=["www A 10.0.0.1", "mail A 10.0.0.2"])
            
            await call("create_node", name="botnet_c2", asn=100, role="host")
            await call("install_botnet_c2", node_name="botnet_c2", port=8080)
            
            await call("create_node", name="bot_client", asn=200, role="host")
            await call("install_botnet_bot", node_name="bot_client", c2_node_name="botnet_c2")
            
            # Connect hosts to routers so they have interfaces
            await call("connect_nodes", node1_name="web_server", node2_name="router200")
            await call("connect_nodes", node1_name="dns_server", node2_name="router200")
            await call("connect_nodes", node1_name="bot_client", node2_name="router200")
            await call("connect_nodes", node1_name="botnet_c2", node2_name="router100")
            
            # 5. Test Node Control Tools
            print("\n--- Verifying Node Control Tools ---")
            await call("add_node_file", 
                       node_name="web_server", 
                       file_path="/etc/custom_config.conf", 
                       content="debug=true\nlog_level=verbose")
            
            await call("add_node_start_command", 
                       node_name="web_server", 
                       command="echo 'Custom Start Command executed' >> /tmp/startup.log")
            
            await call("add_node_build_command", 
                       node_name="web_server", 
                       command="RUN apt-get update && apt-get install -y vim")

            # 6. Render to verify internal consistency
            print("\n--- Verifying Render --")
            await call("render_simulation")
            
            print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
