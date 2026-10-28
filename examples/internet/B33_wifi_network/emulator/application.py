#!/usr/bin/env python3
"""
5G NR Seed-Emulator: Multi-AS topology with standard 3GPP message flows.
Architecture:
  - AS150: 5G Core (AMF, SMF, UPF, EventBus)
  - AS151~155: gNB stubs
  - AS160: UE stubs (island network, no direct Internet)
  - AS2,3,4,11,12: Transit ASes forming the simulated Internet
Data-plane:
  - UE session IPs: 10.60.0.0/24 (allocated by SMF, anchored at UPF)
  - UPF performs N6 NAT (MASQUERADE) for UE outbound traffic
  - gNB does NOT perform NAT; it forwards UE traffic to UPF via policy routing
"""
from pathlib import Path
import sys
import re

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers
from seedemu.core import OptionMode, OptionRegistry

# ========== 用户配置 ==========
NUM_UE = 5
# 每个 AS 包含的 gNB ID 列表 (AS号 -> [gnb_id_list])
AS_GNB_MAP = {
    151: ["gnb-000", "gnb-001", "gnb-002"],
    152: ["gnb-003", "gnb-004"],
    153: ["gnb-005"],
    154: ["gnb-006", "gnb-007"],
    155: ["gnb-008", "gnb-009", "gnb-010"],
}
AS_IX_MAP = {151: 100, 152: 101, 153: 102, 154: 103, 155: 104}
GNB_IDS = [gnb for gnbs in AS_GNB_MAP.values() for gnb in gnbs]
# =============================

SIMULATOR_DIR = Path(__file__).resolve().parent.parent / "simulator"

def fix_dockerfiles(output_dir: Path):
    """修复 seed-emulator 生成的 Dockerfile 中错误的 FROM 指令"""
    # 映射：镜像 ID -> 正确的镜像名
    # 如果出现其他哈希，可以在此添加
    id_to_image = {
        "072d7840db6a44d06e5c5fd4d7ea8a7d": "handsonsecurity/seedemu-router:2.0",
        "ad739b7b201eccafa592110d2bf214a7": "handsonsecurity/seedemu-base:2.0",
    }
    for dockerfile in output_dir.glob("Dockerfile*"):
        content = dockerfile.read_text()
        for img_id, image_name in id_to_image.items():
            content = content.replace(f"FROM {img_id}", f"FROM {image_name}")
        dockerfile.write_text(content)
    print("[+] Fixed Dockerfiles in", output_dir)


def configure_node(node, with_sysctl=True):
    node.addBuildCommand(
        "sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list 2>/dev/null || true; "
        "sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list 2>/dev/null || true; "
        "sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true; "
        "sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true"
    )
    node.addBuildCommand(
        "apt-get update && apt-get install -y python3 python3-pip "
        "iproute2 iptables traceroute iputils-ping tcpdump conntrack"
    )
    # 共享本地 wheels 目录，供无网络节点（如UE）离线安装
    node.addSharedFolder("/wheels", str(SCRIPT_DIR.parent / "wheels"))
    # 优先本地安装，失败则 fallback 到在线（有网节点）
    node.addBuildCommand(
        "pip3 install --break-system-packages --no-index --find-links=/wheels pyzmq docker || "
        "pip3 install --break-system-packages --retries 5 --timeout 120 "
        "-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com "
        "pyzmq docker"
    )
    node.addSharedFolder("/app/simulator", str(SIMULATOR_DIR))
    if with_sysctl:
        node.setOption(OptionRegistry().sysctl_netipv4_conf_rp_filter(
            {"all": False, "default": False, "net0": False},
            mode=OptionMode.RUN_TIME,
        ))
    return node


def build_emulator() -> Emulator:
    emu = Emulator()
    ebgp = Ebgp()
    base = Base()

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    ix100.getPeeringLan().setDisplayName("NYC-100")
    ix101.getPeeringLan().setDisplayName("San Jose-101")
    ix102.getPeeringLan().setDisplayName("Chicago-102")
    ix103.getPeeringLan().setDisplayName("Miami-103")
    ix104.getPeeringLan().setDisplayName("Boston-104")
    ix105.getPeeringLan().setDisplayName("Huston-105")

    Makers.makeTransitAs(base, 2, [100, 101, 102, 105],
                         [(100, 101), (101, 102), (100, 105)])
    Makers.makeTransitAs(base, 3, [100, 103, 104, 105],
                         [(100, 103), (100, 105), (103, 105), (103, 104)])
    Makers.makeTransitAs(base, 4, [100, 102, 104],
                         [(100, 104), (102, 104)])
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])

    # --- 核心网 AS 150 ---
    as_core = base.createAutonomousSystem(150)
    as_core.createNetwork("net0")
    core_router = as_core.createRouter("router0")
    core_router.joinNetwork("net0")
    core_router.joinNetwork(ix100.getPeeringLan().getName())

    # EventBus
    eb = as_core.createHost("eb-server")
    eb.joinNetwork("net0", address="10.150.0.4")
    eb.setDisplayName("EventBus")
    eb.appendStartCommand("ip route add default via 10.150.0.254 || true")
    eb.appendStartCommand("ip route add 10.60.0.0/24 via 10.150.0.5 || true")
    configure_node(eb)
    eb.appendStartCommand("PYTHONUNBUFFERED=1 python3 /app/simulator/event_bus.py")

    # ===== 新增：暴露 EventBus 5555 端口到宿主机 15555 =====
    eb.addPort(15555, 5555, 'tcp')

    # AMF
    amf = as_core.createHost("amf-000")
    amf.joinNetwork("net0", address="10.150.0.2")
    amf.setDisplayName("AMF-000")
    amf.appendStartCommand("ip route add default via 10.150.0.254 || true")
    amf.appendStartCommand("ip route add 10.60.0.0/24 via 10.150.0.5 || true")
    configure_node(amf)
    amf.appendStartCommand("PYTHONUNBUFFERED=1 python3 /app/simulator/amf.py --id amf-000 --bus-host 10.150.0.4")

    # SMF
    smf = as_core.createHost("smf-000")
    smf.joinNetwork("net0", address="10.150.0.3")
    smf.setDisplayName("SMF-000")
    smf.appendStartCommand("ip route add default via 10.150.0.254 || true")
    smf.appendStartCommand("ip route add 10.60.0.0/24 via 10.150.0.5 || true")
    configure_node(smf)
    smf.appendStartCommand("PYTHONUNBUFFERED=1 python3 /app/simulator/smf.py --id smf-000 --bus-host 10.150.0.4")

    # UPF
    upf = as_core.createHost("upf-000")
    upf.joinNetwork("net0", address="10.150.0.5")
    upf.setDisplayName("UPF-000")
    upf.appendStartCommand("ip route add default via 10.150.0.254 || true")
    upf.appendStartCommand("sysctl -w net.ipv4.ip_forward=1")
    # UPF N6 NAT
    upf.appendStartCommand("iptables -t nat -A POSTROUTING -s 10.60.0.0/24 -o net0 -j MASQUERADE")
    configure_node(upf)
    upf.appendStartCommand("PYTHONUNBUFFERED=1 python3 /app/simulator/upf.py --id upf-000 --bus-host 10.150.0.4")

    # --- gNB AS 151~155 ---
    for asn, gnb_ids in AS_GNB_MAP.items():
        ixp = AS_IX_MAP[asn]
        as_gnb = base.createAutonomousSystem(asn)
        as_gnb.createNetwork("net0")
        router = as_gnb.createRouter("router0")
        router.joinNetwork("net0")
        router.joinNetwork(base.getInternetExchange(ixp).getPeeringLan().getName())

        for idx, gnb_id in enumerate(gnb_ids):
            gnb = as_gnb.createHost(gnb_id)
            gnb.joinNetwork("net0", address=f"10.{asn}.0.{2 + idx}")
            gnb.setDisplayName(f"gNB-{gnb_id[-3:]}")
            gnb.appendStartCommand(f"ip route add default via 10.{asn}.0.254 || true")
            gnb.appendStartCommand("sysctl -w net.ipv4.ip_forward=1")
            configure_node(gnb)
            gnb.appendStartCommand(
                "for i in 1 2 3 4 5 6 7 8 9 10; do ping -c1 -W2 10.150.0.4 && break; sleep 2; done"
            )
            gnb.appendStartCommand(
                f"PYTHONUNBUFFERED=1 python3 /app/simulator/gnb.py --id {gnb_id} --bus-host 10.150.0.4"
            )

    # --- UE AS 160 ---
    as_ue = base.createAutonomousSystem(160)
    as_ue.createNetwork("ue-net")
    ue_router = as_ue.createRouter("router0")
    ue_router.joinNetwork("ue-net")

    for i in range(NUM_UE):
        ue = as_ue.createHost(f"ue-{i:03d}")
        ue.joinNetwork("ue-net")
        ue.setDisplayName(f"UE-{i:03d}")
        configure_node(ue, with_sysctl=False)
        ue.appendStartCommand(
            f"PYTHONUNBUFFERED=1 python3 /app/simulator/ue.py --id ue-{i:03d}"
        )

    # --- EBGP ---
    # 基础 RS 对等
    ebgp.addRsPeers(100, [2, 3, 4, 150])
    ebgp.addRsPeers(101, [2, 12])
    ebgp.addRsPeers(102, [2, 4, 11])
    ebgp.addRsPeers(103, [3])
    ebgp.addRsPeers(104, [3, 4, 12])
    ebgp.addRsPeers(105, [2, 3])

    # 为每个 gNB 添加对等
    for asn, ixp in AS_IX_MAP.items():
        ebgp.addRsPeers(ixp, [asn])
        # 根据 IXP 确定提供商 AS
        if ixp == 100:
            ebgp.addPrivatePeerings(ixp, [2], [asn], PeerRelationship.Provider)
        elif ixp == 101:
            ebgp.addPrivatePeerings(ixp, [2], [asn], PeerRelationship.Provider)
        elif ixp == 102:
            ebgp.addPrivatePeerings(ixp, [2, 4], [asn], PeerRelationship.Provider)
        elif ixp == 103:
            ebgp.addPrivatePeerings(ixp, [3], [asn], PeerRelationship.Provider)
        elif ixp == 104:
            ebgp.addPrivatePeerings(ixp, [3, 4], [asn], PeerRelationship.Provider)
        else:
            ebgp.addPrivatePeerings(ixp, [2], [asn], PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    return emu


def main():
    emu = build_emulator()
    emu.render()
    docker = Docker(platform=Platform.AMD64, internetMapEnabled=False)
    emu.compile(docker, "./output", override=True)
    fix_dockerfiles(Path("./output"))
    print("[+] Build complete: output/docker-compose.yml")


if __name__ == "__main__":
    main()