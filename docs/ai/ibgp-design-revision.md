# Design: IBGP with Autonomous System

## Goal

Revise the current design of the ibgp layer and the `AutonomousSystem` class 


## Design Principles 

- Clearly separate the duties of `AutonomousSystem` class (AS) and the ibgp layers. Deciding the ibgp mode withing the AS and roles of routers should be done in the AS, not in the ibgp layer. 
- Although IBGP might have many modes, we would like to stick to this principle: simple default model, clean extension points, minimal built-in special cases. 
- Avoid adding special cases to core layers unless they represent major research or operational patterns.
- Every new API should have a small example and a test.


## Required Behavior


- Inside the Autonomous System class, set the following (use the first option as the default)
```
ibgp_mode = "full-mesh" | "route-reflector"
bgp_scope = "all-routers" | "edge-only"
core_forwarding = "plain-ip" | "mpls" | "sr" | "tunnel" | "redistribute"
```
- all-routers + full-mesh: All routers participate in ibgp using full-mesh peering
- all-routers + route-reflector: All routers participate in ibgp using route reflectors
- edge-only + full-mesh: Only edge routers participate in ibgp using full-mesh peerin; core routers do not participate in ibgp 
- edge-only + route-reflector: Only edge routers participate in ibgp using route reflector; core routers do not participate in ibgp
