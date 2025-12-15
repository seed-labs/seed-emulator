from seedemu.compiler.Proxmox import Proxmox

# 配置参数
BRIDGE_NAME = "vmbr3"
TEMPLATE_ID = 152
GATEWAY = "192.168.105.1"
USERNAME = "seed"
PASSWORD = "dees"
DNS_SERVERS = "10.10.0.21,8.8.8.8"
FIREWALL_ENABLED = False

# VM 配置：IP 地址列表
VM_IPS = [
    "192.168.105.2",
    "192.168.105.3",
    "192.168.105.4"
]

# 初始化 Proxmox 客户端
pm = Proxmox()

# 1. 创建 OVS Bridge 并配置 IP 地址
print("=" * 60)
print("Step 1: Creating OVS Bridge and Configuring IP")
print("=" * 60)
pm.create_ovs_bridge(
    BRIDGE_NAME, 
    comment="Created_by_build_bridge_vm_script",
    bridge_ip=GATEWAY,  # Configure bridge with gateway IP so Proxmox host can communicate with VMs
    bridge_cidr=24
)

# 2. 创建并配置三台 VM
print("\n" + "=" * 60)
print("Step 2: Creating and Configuring VMs")
print("=" * 60)

vmids = []
for idx, ip in enumerate(VM_IPS):
    vm_name = f"VMTEST-{ip.split('.')[-1]}"  # VMTEST-2, VMTEST-3, VMTEST-4
    
    print(f"\n--- Processing VM {idx + 1}/3: {vm_name} (IP: {ip}) ---")
    
    # 克隆 VM（自动分配 VMID）
    success, vmid = pm.deploy_vm(
        template_id=TEMPLATE_ID,
        vmid=None,  # 自动分配
        name=vm_name,
        storage="local-lvm",
        full_clone=False
    )
    
    if not success:
        # VM 已存在，但仍然需要配置
        print(f"    -> VM {vmid} already exists, will update configuration")
    
    vmids.append(vmid)
    print(f"    -> VMID: {vmid}")
    
    # 配置网络（连接到 vmbr3，禁用防火墙）
    pm.config_network(
        vmid=vmid,
        bridge=BRIDGE_NAME,
        firewall=FIREWALL_ENABLED,
        model="virtio"
    )
    
    # 配置 Cloud-Init（IP、网关、用户名、密码、DNS）
    pm.config_cloudinit(
        vmid=vmid,
        ip=ip,
        gw=GATEWAY,
        user=USERNAME,
        password=PASSWORD,
        nameserver=DNS_SERVERS
    )
    
    # 启动 VM
    pm.start_vm(vmid)
    
    print(f"    -> VM {vmid} ({vm_name}) configured and started successfully")

# 3. 总结
print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print(f"Bridge: {BRIDGE_NAME}")
print(f"Created VMs:")
for idx, (vmid, ip) in enumerate(zip(vmids, VM_IPS), 1):
    print(f"  {idx}. VMID {vmid}: VMTEST-{ip.split('.')[-1]} ({ip})")
print("=" * 60)
