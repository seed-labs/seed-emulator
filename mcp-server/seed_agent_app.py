#!/usr/bin/env python3
# seed_agent_app.py

import os
import sys
import json
import asyncio
import traceback
from typing import Dict, Any, List

# Add path to find server and seedemu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from openai import OpenAI

# Import the MCP server object directly
from server import mcp, runtime

load_dotenv()

# ==============================================================================
# 1. Dynamic Tool Discovery
# ==============================================================================

async def get_tools_schema() -> List[Dict[str, Any]]:
    """Extract tools from FastMCP server and convert to OpenAI format."""
    print("[Agent] Discovering tools from MCP server...")
    
    # FastMCP.list_tools() returns a list of Tool objects
    # We need to await it
    mcp_tools = await mcp.list_tools()
    
    openai_tools = []
    
    for tool in mcp_tools:
        # tool is likely a pydantic model or similar structure from mcp library
        # Structure: name, description, inputSchema
        
        # Convert JSON schema to OpenAI format
        # OpenAI expects "parameters": { ... } which IS the inputSchema usually
        
        function_def = {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema
        }
        
        openai_tools.append({
            "type": "function",
            "function": function_def
        })
        
    print(f"[Agent] Found {len(openai_tools)} tools.")
    return openai_tools

# ==============================================================================
# 2. Tool Execution Logic
# ==============================================================================

async def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """Execute a tool using the FastMCP server instance."""
    print(f"[Agent] Executing: {tool_name}({json.dumps(args)})")
    
    try:
        # FastMCP.call_tool() is async
        result = await mcp.call_tool(tool_name, arguments=args)
        
        # result is a CallToolResult list[TextContent|ImageContent|...]
        # We assume text content for now
        output_text = []
        for content in result.content:
            if content.type == 'text':
                output_text.append(content.text)
            elif content.type == 'image':
                output_text.append("[Image Content]")
                
        full_output = "\n".join(output_text)
        print(f"[Agent] Result: {full_output[:200]}..." if len(full_output) > 200 else f"[Agent] Result: {full_output}")
        return full_output
        
    except Exception as e:
        error_msg = f"Error executing tool {tool_name}: {str(e)}\n{traceback.format_exc()}"
        print(f"[Agent] EXECUTION FAULT: {error_msg}")
        return f"SYSTEM_ERROR: {str(e)}"

# ==============================================================================
# 3. Robust Agent Loop
# ==============================================================================

SYSTEM_PROMPT = """
You are a Senior Network Reliability Engineer (NRE) operating a SEED Emulator environment.
Your goal is to build, manage, and verify network topologies.

ROBUSTNESS PROTOCOL:
1.  **Safety First**: Never execute destructive commands on the system root (rm -rf /).
2.  **Tool Verification**: If you need to use a tool, make sure it exists. If you are unsure, check your available tools.
3.  **Error Handling**: 
    - If a tool fails with "Node not found", ask yourself: "Did I create it?". If not, create it.
    - If a tool fails with "Layer not enabled", use `enable_routing_layers` to fix it.
    - If a parameter is invalid, correct it and retry.
4.  **Self-Correction**: do not give up on the first error. Try at least 1 alternative approach.
5.  **Final Verification**: After completing a task, verify the state (e.g., check BGP status, ping).

You are interacting with a simulated network. Real-world consequences are limited to the simulation, but treat it seriously.
"""

async def run_agent(task_prompt: str):
    client = OpenAI(
        api_key=os.environ.get("MIMO_API_KEY"),
        base_url="https://api.xiaomimimo.com/v1"
    )
    
    tools = await get_tools_schema()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt}
    ]
    
    MAX_TURNS = 20
    
    print("\n" + "="*60)
    print(f"Task: {task_prompt}")
    print("="*60 + "\n")
    
    for turn in range(MAX_TURNS):
        print(f"\n--- Turn {turn+1}/{MAX_TURNS} ---")
        
        try:
            response = client.chat.completions.create(
                model="mimo-v2-flash",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            msg = response.choices[0].message
            print(f"Assistant: {msg.content}")
            
            messages.append(msg)
            
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        result = "Error: Invalid JSON arguments."
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                        continue

                    # Execute
                    result = await execute_tool(func_name, args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # No tool calls, maybe done?
                if "DONE" in str(msg.content) or "task complete" in str(msg.content).lower():
                    print("Agent indicates completion.")
                    break
                    
        except Exception as e:
            print(f"LLM Error: {e}")
            break
            
    print("\n[Agent] Session Ended.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed_agent_app.py 'Your task here'")
        sys.exit(1)
        
    task = sys.argv[1]
    asyncio.run(run_agent(task))
