#!/usr/bin/env python3
"""Verification script for Dynamic Operational Tools."""

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
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            final_state = run_agent_with_auto_confirm(prompt)
        
        output = f.getvalue()
        print(output)
        
        # Check for error
        if final_state.get("error_message"):
            print(f"❌ Test '{name}' Failed with error: {final_state['error_message']}")
            return False
            
        # Check if the tool was actually called
        # We look for the tool name in the output log or tool_calls
        tool_calls = final_state.get("tool_calls", [])
        called_tools = [tc.tool_name for tc in tool_calls]
        
        print(f"Tools called: {called_tools}")
        
        if "start_attack_scenario" in called_tools or "inject_fault" in called_tools:
             print(f"✅ Test '{name}' Passed - Dynamic tool called successfully.")
             return True
        else:
             print(f"❌ Test '{name}' Failed - Dynamic tool NOT called.")
             return False

    except Exception as e:
        print(f"❌ Test '{name}' Crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Starting Dynamic Operations Verification...")
    
    # 1. Attack Scenario Test
    # This tool 'start_attack_scenario' does NOT exist in the static map.
    # If the agent calls it, it proves dynamic discovery works.
    if not run_test_case(
        "BGP Hijack Test",
        "Start a BGP hijack attack. The attacker is 'attacker_container' targeting prefix '10.0.0.0/24'. Scenario name is 'hijack1'."
    ):
        sys.exit(1)
        
    print("\n✅ Dynamic Operations Verified!")

if __name__ == "__main__":
    main()
