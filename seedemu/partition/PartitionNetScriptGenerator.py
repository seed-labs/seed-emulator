from __future__ import annotations
from typing import List
import os
import sys
from seedemu.core import Emulator


# Shell script template for network configuration
NET_SCRIPT_TEMPLATE = """#!/bin/bash
set -e

# Auto-detect physical network interface (default: ens18)
detect_physical_interface() {{
    if ip link show ens18 >/dev/null 2>&1; then
        echo "ens18"
    else
        # Find first non-loopback physical interface
        ip link show | grep -E "^[0-9]+: (eth|en|ens)" | grep -v "lo:" | head -1 | cut -d: -f2 | tr -d ' ' | head -1
    fi
}}

PHYSICAL_IFACE=$(detect_physical_interface)
if [ -z "$PHYSICAL_IFACE" ]; then
    echo "Error: Cannot detect physical network interface" >&2
    exit 1
fi

echo "Using physical interface: $PHYSICAL_IFACE"

# Function: Find bridge for IXP network
find_bridge_for_ixp() {{
    local ixp_id=$1
    local expected_ip="10.${{ixp_id}}.0.1"
    
    # Use ip -br ad to find bridge containing this IP
    # Format: br-xxx    UP    10.100.0.1/24 ...
    local bridge_name=$(ip -br ad | grep "$expected_ip" | awk '{{print $1}}' | grep -E '^br-')
    
    if [ -z "$bridge_name" ]; then
        echo "Warning: Cannot find bridge for IX${{ixp_id}} (expected IP: ${{expected_ip}})" >&2
        return 1
    fi
    
    echo "$bridge_name"
}}

# Configure network for each IXP
configure_ixp() {{
    local ixp_id=$1
    local vlan_iface="${{PHYSICAL_IFACE}}.${{ixp_id}}"
    
    echo "Configuring IX${{ixp_id}}..."
    
    # Find bridge
    local bridge=$(find_bridge_for_ixp $ixp_id)
    if [ -z "$bridge" ]; then
        echo "  Skipping IX${{ixp_id}} (bridge not found)"
        return 1
    fi
    
    # Create VLAN interface (if not exists)
    if ! ip link show "$vlan_iface" >/dev/null 2>&1; then
        sudo ip link add link "$PHYSICAL_IFACE" name "$vlan_iface" type vlan id $ixp_id
        echo "  Created VLAN interface: $vlan_iface"
    else
        echo "  VLAN interface $vlan_iface already exists"
    fi
    
    # Bring up VLAN interface
    sudo ip link set dev "$vlan_iface" up
    echo "  Brought up VLAN interface: $vlan_iface"
    
    # Add VLAN interface to bridge (if not already added)
    if ! brctl show "$bridge" | grep -q "$vlan_iface"; then
        sudo brctl addif "$bridge" "$vlan_iface"
        echo "  Added $vlan_iface to bridge $bridge"
    else
        echo "  $vlan_iface already in bridge $bridge"
    fi
    
    echo "  IX${{ixp_id}} configured: VLAN $vlan_iface -> Bridge $bridge"
}}

# Configure network for each IXP
{configure_calls}

echo ""
echo "Network configuration completed!"
"""


class PartitionNetScriptGenerator:
    """!
    @brief Generate net.sh script for network configuration after partition.
    
    This class generates a shell script that configures VLAN interfaces
    and connects them to Docker bridges for multi-machine deployment.
    """
    
    def __init__(self, emulator: Emulator):
        """!
        @brief Initialize the net script generator.
        
        @param emulator Rendered Emulator object.
        """
        assert emulator.rendered(), "emulator is not rendered."
        self.__emulator = emulator
        self.__registry = emulator.getRegistry()
    
    def generate(self, output_dir: str) -> bool:
        """!
        @brief Generate net.sh script for the given output directory.
        
        @param output_dir Output directory path.
        @return True if script generated successfully, False otherwise.
        """
        # Collect all IXP information
        ixps = self._extract_ixps()
        
        if not ixps:
            return False
        
        # Generate script content
        script_content = self._generate_script_content(ixps)
        
        # Write to file
        script_path = os.path.join(output_dir, 'net.sh')
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)  # Add execute permission
            return True
        except Exception as e:
            print(f"  Error generating net.sh: {e}", file=sys.stderr)
            return False
    
    def _extract_ixps(self) -> List[int]:
        """!
        @brief Extract IXP IDs from registry.
        
        @return List of IXP IDs.
        """
        ixps = []
        for (scope, type, name), obj in self.__registry.getAll().items():
            if scope == 'ix' and type == 'net':
                # Extract IX ID from name (e.g., 'ix100' -> 100)
                if name.startswith('ix'):
                    try:
                        ix_id = int(name[2:])  # Remove 'ix' prefix
                        ixps.append(ix_id)
                    except ValueError:
                        continue
        return sorted(ixps)
    
    def _generate_script_content(self, ixps: List[int]) -> str:
        """!
        @brief Generate shell script content.
        
        @param ixps List of IXP IDs.
        @return Shell script content.
        """
        # Generate configure_ixp call list
        configure_calls = '\n'.join([f"configure_ixp {ixp_id}" for ixp_id in ixps])
        
        # Format template with configure calls
        return NET_SCRIPT_TEMPLATE.format(configure_calls=configure_calls)
