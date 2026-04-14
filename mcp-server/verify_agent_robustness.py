#!/usr/bin/env python3
"""Verification script for Robust SEED Agent (LangGraph Version)."""

import os
import sys
import io
from contextlib import redirect_stdout

# Add agent path to sys.path
sys.path.insert(0, "/home/parallels/seed-agent")
from demo_real_agent import run_agent_with_auto_confirm

def run_test_case(name: str, prompt: str) -> bool:
    print(f"\n{'='*50}")
    print(f"TEST: {name}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*50}\n")
    
    try:
        # Capture output to check for internal logic traces
        f = io.StringIO()
        with redirect_stdout(f):
            final_state = run_agent_with_auto_confirm(prompt)
        
        output = f.getvalue()
        print(output)
        
        if final_state.get("error_message"):
            print(f"❌ Test '{name}' Failed with error: {final_state['error_message']}")
            return False
        
        # Check if debugging happened if expected
        if "Debug" in output or "Retrying" in output or "Debugging:" in str(final_state.get("messages", [])):
            print(f"ℹ️  Test '{name}' triggered debugging/self-correction as expected.")
            
        print(f"✅ Test '{name}' Passed")
        return True
        
    except Exception as e:
        print(f"❌ Test '{name}' Crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Starting LangGraph Agent Robustness Verification...")
    
    # 1. Parameter Error Test
    # Ask to create a node with invalid role. Agent should fix it via Debugger.
    if not run_test_case(
        "Bad Parameter Test",
        "Create an AS 100. Then create a node 'bad_node' in AS 100 with role 'SUPERMAN'. If that fails, make it a host."
    ):
        sys.exit(1)
        
    # 2. Dependency Test
    # Ask to connect nodes that don't exist. Agent should create them.
    if not run_test_case(
        "Dependency Test",
        "Connect 'ghost_router1' and 'ghost_router2' in AS 300. You need to enable MPLS on AS 300 too."
    ):
        sys.exit(1)
        
    print("\n✅ All Robustness Tests Passed!")

if __name__ == "__main__":
    main()
