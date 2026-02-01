
import sys
import os
import asyncio
import inspect

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import mcp

print("MCP Object Type:", type(mcp))
print("Dir(mcp):", dir(mcp))

# Try to find tools
if hasattr(mcp, 'tools'):
    print("mcp.tools:", mcp.tools)
elif hasattr(mcp, '_tools'):
    print("mcp._tools:", mcp._tools) # Often private
    
# Check if we can list tools
async def inspect_mcp_tools():
    tools = await mcp.list_tools()
    print(f"Found {len(tools)} tools:")
    for t in tools:
        print(f"- {t.name}: {t.description[:50]}...")
        # print parameters keys
        if t.inputSchema:
            keys = t.inputSchema.get("properties", {}).keys()
            print(f"  Args: {list(keys)}")

if __name__ == "__main__":
    try:
        asyncio.run(inspect_mcp_tools())
    except Exception as e:
        print("mcp.list_tools() failed:", e)
