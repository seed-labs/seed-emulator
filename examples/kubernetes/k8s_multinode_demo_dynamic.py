import time
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy
from seedemu.core import Emulator, Binding, Filter
from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService

# Create the emulator
emu = Emulator()
base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()

# Add layers
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

# Define a simple topology:
# AS150 (Web Service) <-> AS2 (Transit) <-> AS151 (Web Service)
# All connected via IX100, IX101

# Create ASes
as150 = base.createAutonomousSystem(150)
as151 = base.createAutonomousSystem(151)
as2 = base.createAutonomousSystem(2)

# Create Networks
net100 = base.createInternetExchange(100) # IX connecting AS150 and AS2
net101 = base.createInternetExchange(101) # IX connecting AS151 and AS2

# AS150 Setup
as150.createNetwork("net0")
r150 = as150.createRouter("router0")
web150 = as150.createHost("web150")
r150.joinNetwork("net0").joinNetwork("ix100")
web150.joinNetwork("net0")
web.install('web150')

# AS151 Setup
as151.createNetwork("net0")
r151 = as151.createRouter("router0")
web151 = as151.createHost("web151")
r151.joinNetwork("net0").joinNetwork("ix101")
web151.joinNetwork("net0")
web.install('web151')

# AS2 Transit Setup
as2.createNetwork("net0")
# 3 routers in full mesh
r1 = as2.createRouter("r1")
r2 = as2.createRouter("r2")
r3 = as2.createRouter("r3")
r1.joinNetwork("net0").joinNetwork("ix100")
r2.joinNetwork("net0")
r3.joinNetwork("net0").joinNetwork("ix101")

# Manual Scheduling Labels (Simulating Teacher's "Operator" logic client-side)
# We want:
# AS150 -> Node 1 (seedemu-worker)
# AS151 -> Node 2 (seedemu-worker2)
# AS2   -> Node 3 (seedemu-control-plane)
node_labels = {
    "150": {"kubernetes.io/hostname": "seedemu-worker"},
    "151": {"kubernetes.io/hostname": "seedemu-worker2"},
    "2":   {"kubernetes.io/hostname": "seedemu-control-plane"}
}

# Compilation
if __name__ == "__main__":
    # NO REGISTRY prefix -> local images
    REGISTRY_IP = ""
    
    # Create Kubernetes compiler with multi-node features
    k8s = KubernetesCompiler(
        registry_prefix=REGISTRY_IP,  # Empty for local tags
        namespace="seedemu",
        use_multus=True,
        internetMapEnabled=False,
        
        # Multi-node scheduling: pods with same AS go to same node
        scheduling_strategy=SchedulingStrategy.BY_AS,
        node_labels=node_labels,
        
        # Resource management
        default_resources={
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"}
        },
        
        # Connectivity
        cni_type="bridge",
        
        # Service Discovery
        generate_services=True,
        
        # Image Pull Policy for local images
        image_pull_policy="IfNotPresent"
    )
    
    # Add bindings for WebService virtual nodes
    emu.addBinding(Binding('web150', filter=Filter(nodeName='web150', asn=150)))
    emu.addBinding(Binding('web151', filter=Filter(nodeName='web151', asn=151)))
    
    emu.render()
    emu.compile(k8s, "./output_multinode_bridge", override=True)
    
    print("\n" + "="*80)
    print("Multi-Node Kubernetes Deployment Generated (Local Load Mode)!")
    print("="*80)
    print("REMINDER: Run 'kind load docker-image <image_name> --name seedemu' for all images")
