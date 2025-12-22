from seedemu import *
import os, sys
import json
from seedemu.compiler.Proxmox import Proxmox

# Load configuration from machine_config.json
def load_config(config_path='config.json'):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

# Load configuration
config = load_config()

# Read Proxmox configuration from JSON
proxmox_config = config.get('proxmox', {})
BRIDGE_NAME = proxmox_config.get('bridge_name', 'vmbr3')
TEMPLATE_ID = proxmox_config.get('template_id', 152)
GATEWAY = proxmox_config.get('gateway', '192.168.105.1')
USERNAME = proxmox_config.get('username', 'seed')
PASSWORD = proxmox_config.get('password', 'dees')
DNS_SERVERS = proxmox_config.get('dns_servers', '10.10.0.21,8.8.8.8')
FIREWALL_ENABLED = proxmox_config.get('firewall_enabled', False)
BRIDGE_CIDR = proxmox_config.get('bridge_cidr', 24)
STORAGE = proxmox_config.get('storage', 'local-lvm')
FULL_CLONE = proxmox_config.get('full_clone', False)
VM_NETWORK_MODEL = proxmox_config.get('vm_network_model', 'virtio')

HOSTS_PER_AS = 10

###############################################################################
# Set the platform information
script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

emu   = Emulator()
ebgp  = Ebgp()
base  = Base()
ovpn  = OpenVpnRemoteAccessProvider()

###############################################################################
# Create internet exchanges
ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix102 = base.createInternetExchange(102)
ix103 = base.createInternetExchange(103)
ix104 = base.createInternetExchange(104)
ix105 = base.createInternetExchange(105)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('NYC-100')
ix101.getPeeringLan().setDisplayName('San Jose-101')
ix102.getPeeringLan().setDisplayName('Chicago-102')
ix103.getPeeringLan().setDisplayName('Miami-103')
ix104.getPeeringLan().setDisplayName('Boston-104')
ix105.getPeeringLan().setDisplayName('Huston-105')


###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
Makers.makeTransitAs(base, 2, [100, 101, 102, 105], 
        [(100, 101), (101, 102), (100, 105)] 
)

Makers.makeTransitAs(base, 3, [100, 103, 104, 105], 
        [(100, 103), (100, 105), (103, 105), (103, 104)]
)

Makers.makeTransitAs(base, 4, [100, 102, 104], 
        [(100, 104), (102, 104)]
)

## Tier 2 ASes
Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])


###############################################################################
# Create single-homed stub ASes. 
Makers.makeStubAsWithHosts(emu, base, 150, 100, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 151, 100, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 152, 101, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 153, 101, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 154, 102, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 160, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 161, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 162, 103, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 163, 104, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 164, 104, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 170, 105, HOSTS_PER_AS)
Makers.makeStubAsWithHosts(emu, base, 171, 105, HOSTS_PER_AS)

###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
# which means each AS will only export its customers and their own prefixes. 
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others. 

ebgp.addRsPeers(100, [2, 3, 4])
ebgp.addRsPeers(102, [2, 4])
ebgp.addRsPeers(104, [3, 4])
ebgp.addRsPeers(105, [2, 3])

# To buy transit services from another autonomous system, 
# we will use private peering  

ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)

ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)

ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)


###############################################################################
# Add layers to the emulator

emu.addLayer(base)
emu.addLayer(Routing())
emu.addLayer(ebgp) 
emu.addLayer(Ibgp())
emu.addLayer(Ospf())

dhcp = DHCPService()

# Default DhcpIpRange : x.x.x.101 ~ x.x.x.120
# Set DhcpIpRange : x.x.x.125 ~ x.x.x.140
dhcp.install('dhcp-01').setIpRange(125, 140)
dhcp.install('dhcp-02')


# Customize the display name (for visualization purpose)
emu.getVirtualNode('dhcp-01').setDisplayName('DHCP Server 1')
emu.getVirtualNode('dhcp-02').setDisplayName('DHCP Server 2')


# Create new hosts in AS-151 and AS-161, use them to host the DHCP servers.
# We can also host it on an existing node.
as151 = base.getAutonomousSystem(151)
as151.createHost('dhcp-server-01').joinNetwork('net0')

as161 = base.getAutonomousSystem(161)
as161.createHost('dhcp-server-02').joinNetwork('net0')

# Bind the DHCP virtual node to the physical node.
emu.addBinding(Binding('dhcp-01', filter = Filter(asn=151, nodeName='dhcp-server-01')))
emu.addBinding(Binding('dhcp-02', filter = Filter(asn=161, nodeName='dhcp-server-02')))


# Create new hosts in AS-151 and AS-161
# Make them to use dhcp instead of static ip
as151.createHost('dhcp-client-01').joinNetwork('net0', address = "dhcp")
as151.createHost('dhcp-client-02').joinNetwork('net0', address = "dhcp")

as161.createHost('dhcp-client-03').joinNetwork('net0', address = "dhcp")
as161.createHost('dhcp-client-04').joinNetwork('net0', address = "dhcp")

# Add the dhcp layer
emu.addLayer(dhcp)

# Render the emulation
emu.render()

###############################################################################
# Create Proxmox VMs and OVS Bridge
# Use machine configuration from loaded config
machines = config['machines']
vm_ips = [machine['ip'] for machine in machines]
num_vms = len(machines)

print("\n" + "="*70)
print("Creating Proxmox VMs and OVS Bridge")
print("="*70)
print(f"Number of VMs to create: {num_vms}")
print(f"Bridge name: {BRIDGE_NAME}")
print(f"Template ID: {TEMPLATE_ID}")
print(f"Gateway: {GATEWAY}")
print(f"VM IPs: {vm_ips}")

# Initialize Proxmox client
pm = Proxmox()

# 1. Create OVS Bridge and configure IP address
print("\n" + "-"*70)
print("Step 1: Creating OVS Bridge and Configuring IP")
print("-"*70)
pm.create_ovs_bridge(
    BRIDGE_NAME,
    comment="Created_by_distributed_emulation_script",
    bridge_ip=GATEWAY,
    bridge_cidr=BRIDGE_CIDR
)

# 2. Create and configure VMs
print("\n" + "-"*70)
print("Step 2: Creating and Configuring VMs")
print("-"*70)

vmids = []
for idx, machine in enumerate(machines):
    ip = machine['ip']
    vm_name = machine.get('name', f"VM-{ip.split('.')[-1]}")
    
    print(f"\n--- Processing VM {idx + 1}/{num_vms}: {vm_name} (IP: {ip}) ---")
    
    # Clone VM (auto-allocate VMID)
    success, vmid = pm.deploy_vm(
        template_id=TEMPLATE_ID,
        vmid=None,  # Auto-allocate
        name=vm_name,
        storage=STORAGE,
        full_clone=FULL_CLONE
    )
    
    if not success:
        # VM already exists, but still need to configure
        print(f"    -> VM {vmid} already exists, will update configuration")
    
    vmids.append(vmid)
    print(f"    -> VMID: {vmid}")
    
    # Configure network (connect to bridge, firewall setting)
    pm.config_network(
        vmid=vmid,
        bridge=BRIDGE_NAME,
        firewall=FIREWALL_ENABLED,
        model=VM_NETWORK_MODEL
    )
    
    # Configure Cloud-Init (IP, gateway, username, password, DNS)
    # Use machine-specific credentials if available, otherwise use global defaults
    vm_user = machine.get('user', USERNAME)
    vm_password = machine.get('password', PASSWORD)
    pm.config_cloudinit(
        vmid=vmid,
        ip=ip,
        gw=GATEWAY,
        user=vm_user,
        password=vm_password,
        nameserver=DNS_SERVERS
    )
    
    # Start VM
    pm.start_vm(vmid, wait_for_cloudinit=False)
    
    print(f"    -> VM {vmid} ({vm_name}) configured and started successfully")

# 3. Summary
print("\n" + "-"*70)
print("VM Creation Summary")
print("-"*70)
print(f"Bridge: {BRIDGE_NAME}")
print(f"Created VMs:")
for idx, (vmid, machine) in enumerate(zip(vmids, machines), 1):
    vm_name = machine.get('name', f"VM-{machine['ip'].split('.')[-1]}")
    print(f"  {idx}. VMID {vmid}: {vm_name} ({machine['ip']})")
print("-"*70)

###############################################################################
# Partition the emulator across multiple machines
# Define machine capacities (resource limits for each machine)
machine_capacities = [machine['capacity'] for machine in machines]

# Call partition solver
print("\n" + "="*70)
print("Partitioning emulator across {} machines...".format(len(machine_capacities)))
print("="*70)

partition_result = emu.partEmulator(
    machine_capacities=machine_capacities,
    solver_name='pulp',
    time_limit=180
)

if partition_result:
    print("\n✓ Partition solved successfully!")
    print("\nPartition Result:")
    print("-" * 70)
    for machine_id in sorted(partition_result.keys()):
        machine_data = partition_result[machine_id]
        as_list = machine_data['as_list']
        ixp_list = machine_data['ixp_list']
        
        print(f"\nMachine {machine_id}:")
        print(f"  ASs ({len(as_list)}): {as_list}")
        print(f"  IXPs ({len(ixp_list)}):")
        for ix_id, needs_rs in ixp_list:
            rs_status = "with RS" if needs_rs else "without RS"
            print(f"    - IX{ix_id} ({rs_status})")
    
    print("\n" + "="*70)
    print("Applying partition and creating sub-emulators...")
    print("="*70)
    
    # Apply partition to create sub-emulators
    from seedemu.partition.PartitionApplier import PartitionApplier
    applier = PartitionApplier(emu, partition_result)
    sub_emulators = applier.apply()
    
    print(f"\n✓ Created {len(sub_emulators)} sub-emulators")
    
    # Compile each sub-emulator
    print("\nCompiling sub-emulators...")
    print("-" * 70)
    
    from seedemu.partition.PartitionNetScriptGenerator import PartitionNetScriptGenerator
    from seedemu.compiler.Proxmox import ScriptGenerator
    
    for machine_id, sub_emu in enumerate(sub_emulators):
        # Create a new Docker compiler instance for each sub-emulator
        # This ensures each compilation is independent and avoids state accumulation
        docker = Docker(platform=platform)
        
        output_dir = f'./output_{machine_id}'
        print(f"\nCompiling Machine {machine_id} to {output_dir}...")
        try:
            sub_emu.compile(docker, output_dir, override=True)
            print(f"✓ Machine {machine_id} compiled successfully")
            
            # Generate net.sh script
            script_generator = PartitionNetScriptGenerator(sub_emu)
            if script_generator.generate(output_dir):
                print(f"  Generated net.sh script")
        except Exception as e:
            print(f"✗ Failed to compile Machine {machine_id}: {e}")

    # Generate combined controller script
    try:
        script_generator = ScriptGenerator()
        combined_script = script_generator.generate(script_type='combined')
        with open('deploy.py', 'w') as f:
            f.write(combined_script)
        print(f"✓ Generated combined deployment script: deploy.py")
    except Exception as e:
        print(f"✗ Failed to generate script: {e}")
    
    print("\n" + "="*70)
    print("All sub-emulators compiled!")
    print("="*70)
else:
    print("\n✗ Partition solving failed!")

print("\n" + "="*70)

# # # Attach the Internet Map container to the emulator
# docker = Docker(platform=platform)
# emu.compile(docker, './output', override=True)