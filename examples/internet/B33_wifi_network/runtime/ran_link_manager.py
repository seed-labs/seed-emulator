#!/usr/bin/env python3
"""
RAN Link Manager: Make-before-Break handover with batched exec calls.
- PREPARE: 按需建立目标链路（一次 docker network connect + 轮询 IP）
- COMMIT:  单次 bash 脚本原子替换路由（合并 4 次 exec 为 1 次）
- 隧道+NAT: 每容器一次脚本完成（合并 3 次 exec 为 1 次）
- GRACE/CLEANUP: 后台线程延迟释放旧链路
- ZMQ 实时推送隧道配置（替代文件轮询）
- 预建邻居池（切换时命中预建链路，跳过 docker network connect）
- 保留文件兜底机制（ZMQ 失败时仍可工作）
"""
import docker
import json
import time
import os
import subprocess
import random
import threading
import zmq
from typing import Dict, List, Optional, Tuple, Set


class RANLinkManager:
    def __init__(self, ue_ids: List[str], gnb_ids: List[str],
                 default_gnb: str = "gnb-000",
                 eventbus_ip: str = "127.0.0.1",
                 eventbus_port: int = 15555):
        self.client = docker.from_env()
        self.ue_ids = ue_ids
        self.gnb_ids = gnb_ids
        self.default_gnb = default_gnb
        self.bridge_prefix = "net-"
        self.current_data_net: Dict[str, str] = {}
        self.ue_ip_map: Dict[str, str] = {}
        self.ue_teid: Dict[str, tuple] = {}
        self.configured_ue: set = set()

        # 待清理登记（代际号机制）
        self._pending_cleanup: Dict[str, Dict] = {}

        # 预建邻居池
        # ue_id -> {gnb_id: (iface, gnb_docker_ip)}
        self._prepared_links: Dict[str, Dict[str, Tuple[str, str]]] = {}
        self._prepared_lock = threading.Lock()
        # 新增：IP 缓存
        self._ip_cache: Dict[str, Dict[str, str]] = {}

        # 记录 EventBus 地址供重建使用
        self._eventbus_ip = eventbus_ip
        self._eventbus_port = eventbus_port

        # 主 ZMQ socket
        self.zmq_ctx = None
        self.zmq_socket = None
        self._init_zmq()

        # 心跳使用独立 socket（避免与主线程竞争）
        self._hb_ctx = zmq.Context()
        self._hb_socket = self._hb_ctx.socket(zmq.DEALER)
        self._hb_socket.setsockopt(zmq.IDENTITY, b"ran-link-mgr-hb")
        self._hb_socket.setsockopt(zmq.LINGER, 0)
        self._hb_socket.setsockopt(zmq.SNDTIMEO, 500)
        try:
            self._hb_socket.connect(f"tcp://{eventbus_ip}:{eventbus_port}")
        except Exception:
            pass
        threading.Thread(target=self._zmq_heartbeat_loop, daemon=True).start()

    def _init_zmq(self):
        """初始化/重建主 ZMQ socket"""
        try:
            if self.zmq_socket:
                try:
                    self.zmq_socket.close(linger=0)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self.zmq_ctx:
                try:
                    self.zmq_ctx.term()
                except Exception:
                    pass
        except Exception:
            pass

        self.zmq_ctx = zmq.Context()
        self.zmq_socket = self.zmq_ctx.socket(zmq.DEALER)
        self.zmq_socket.setsockopt(zmq.IDENTITY, b"ran-link-mgr")
        self.zmq_socket.setsockopt(zmq.LINGER, 0)
        self.zmq_socket.setsockopt(zmq.SNDTIMEO, 500)
        try:
            self.zmq_socket.connect(f"tcp://{self._eventbus_ip}:{self._eventbus_port}")
            print(f"[RANLinkManager] ZMQ (re)connected to EventBus {self._eventbus_ip}:{self._eventbus_port}", flush=True)
        except Exception as e:
            print(f"[RANLinkManager] ZMQ connect failed: {e}", flush=True)

    def _ensure_zmq(self):
        """确保主 ZMQ socket 有效，失效则重建"""
        need_reinit = False
        try:
            if not hasattr(self, 'zmq_socket') or self.zmq_socket is None:
                need_reinit = True
            # 不要访问 .closed 属性！zmq.Socket 没有这个字段
        except Exception:
            need_reinit = True

        if need_reinit:
            self._init_zmq()

    # ========== ZMQ 辅助 ==========
    def _zmq_heartbeat_loop(self):
        """定期发送 HELLO 保持注册状态"""
        while True:
            try:
                self._hb_socket.send_json({
                    "source": "ran-link-mgr-hb",
                    "target": "eb-server",
                    "type": "HELLO",
                    "payload": {}
                })
            except Exception:
                pass
            time.sleep(5)

    def _push_tunnel_update(self, target: str, ue_id: str, session_ip: str,
                            docker_ip: str, up_teid: int, down_teid: int,
                            upf_ip: str = None, gnb_ip: str = None):
        """ZMQ 推送隧道配置到 gNB 或 UPF"""
        self._ensure_zmq()   # ← 新增
        payload = {
            "ue_id": ue_id,
            "session_ip": session_ip,
            "docker_ip": docker_ip,
            "up_teid": up_teid,
            "down_teid": down_teid,
        }
        if upf_ip:
            payload["upf_ip"] = upf_ip
        if gnb_ip:
            payload["gnb_ip"] = gnb_ip
        try:
            self.zmq_socket.send_json({
                "source": "ran-link-mgr",
                "target": target,
                "type": "TunnelUpdate",
                "payload": payload
            })
        except Exception as e:
            print(f"  [WARN] ZMQ send TunnelUpdate to {target}: {e}", flush=True)

    def _push_flush_nat(self, ue_id: str, session_ip: str):
        """ZMQ 推送 NAT 刷新命令到 UPF"""
        self._ensure_zmq()   # ← 新增
        try:
            self.zmq_socket.send_json({
                "source": "ran-link-mgr",
                "target": "upf-000",
                "type": "FlushNAT",
                "payload": {"ue_id": ue_id, "session_ip": session_ip}
            })
        except Exception as e:
            print(f"  [WARN] ZMQ send FlushNAT: {e}", flush=True)

    # ========== 辅助方法 ==========
    def _load_ue_ip_map(self):
        try:
            with open("simulator/ue_ip_map.json") as f:
                data = json.load(f)
                if data:
                    self.ue_ip_map = data
                    return
        except Exception:
            pass
        try:
            container = self._get_container_by_nodename("smf-000")
            result = container.exec_run(["cat", "/app/simulator/ue_ip_map.json"])
            if result.exit_code == 0 and result.output:
                self.ue_ip_map = json.loads(result.output.decode())
                return
        except Exception:
            pass
        self.ue_ip_map = {}

    def _get_container_by_nodename(self, nodename: str):
        containers = self.client.containers.list(
            filters={"label": f"org.seedsecuritylabs.seedemu.meta.nodename={nodename}"}
        )
        if not containers:
            raise RuntimeError(f"Container for node {nodename} not found")
        return containers[0]

    def _get_container_ip_in_network(self, nodename: str, net_name: str) -> str:
        try:
            network = self.client.networks.get(net_name)
            network.reload()
            container = self._get_container_by_nodename(nodename)
            for cid, config in network.attrs.get('Containers', {}).items():
                if cid == container.id:
                    ip = config.get('IPv4Address', '').split('/')[0]
                    if ip:
                        return ip
            container.reload()
            nets = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            for k, v in nets.items():
                if net_name in k:
                    return v.get('IPAddress', '')
        except Exception as e:
            print(f"  [WARN] get docker ip for {nodename} in {net_name}: {e}", flush=True)
        return ""

    def _get_cached_ip(self, nodename: str, net_name: str) -> str:
        """优先从缓存获取 IP"""
        cached = self._ip_cache.get(net_name, {}).get(nodename)
        if cached:
            return cached
        ip = self._get_container_ip_in_network(nodename, net_name)
        if ip:
            self._ip_cache.setdefault(net_name, {})[nodename] = ip
        return ip

    def _invalidate_ip_cache(self, net_name: str, nodename: str = None):
        if net_name in self._ip_cache:
            if nodename:
                self._ip_cache[net_name].pop(nodename, None)
            else:
                self._ip_cache.pop(net_name, None)

    def _get_data_iface(self, nodename: str, target_ip: str) -> Optional[str]:
        try:
            container = self._get_container_by_nodename(nodename)
            result = container.exec_run(["ip", "route", "get", target_ip])
            if result.exit_code == 0:
                out = result.output.decode().strip()
                parts = out.split()
                for i, part in enumerate(parts):
                    if part == "dev" and i + 1 < len(parts):
                        iface = parts[i + 1]
                        if iface != "lo":
                            return iface
        except Exception:
            pass
        return None

    def _exec_in_container(self, nodename: str, cmd: List[str]) -> bool:
        try:
            container = self._get_container_by_nodename(nodename)
            result = container.exec_run(cmd)
            out = result.output.decode().strip() if result.output else ""
            ignore_msgs = (
                "No such process", "File exists", "Cannot find device",
                "Address already assigned", "ipv4:", "onlink",
                "Nexthop has invalid gateway", "Not supported",
                "No such file or directory", "Bad rule",
                "RTNETLINK answers: File exists",
                "RTNETLINK answers: Cannot assign requested address",
                "RTNETLINK answers: No such process",
                "No chain/target/match by that name"
            )
            if result.exit_code != 0 and out and not any(m in out for m in ignore_msgs):
                print(f"  [exec {nodename}] exit={result.exit_code}: {out}", flush=True)
            return result.exit_code == 0
        except Exception as e:
            print(f"  [exec error {nodename}] {e}", flush=True)
            return False

    # ========== GTP-U 隧道配置 ==========
    def _allocate_teid(self, ue_id: str):
        if ue_id not in self.ue_teid:
            up_teid = random.randint(1, 0xFFFFFFFF)
            down_teid = random.randint(1, 0xFFFFFFFF)
            self.ue_teid[ue_id] = (up_teid, down_teid)

    def _build_gnb_config(self, ue_id, gnb_id, net_name) -> dict:
        gnb_docker_ip = self._get_cached_ip(gnb_id, net_name)     # ← 改
        upf_docker_ip = self._get_cached_ip("upf-000", net_name)  # ← 改
        ue_docker_ip = self._get_cached_ip(ue_id, net_name)       # ← 改
        session_ip = self.ue_ip_map.get(ue_id, "")
        up_teid, down_teid = self.ue_teid[ue_id]
        return {
            "ue_id": ue_id, "docker_ip": ue_docker_ip, "session_ip": session_ip,
            "up_teid": up_teid, "down_teid": down_teid, "upf_ip": upf_docker_ip,
        }

    def _build_upf_config(self, ue_id, gnb_id, net_name) -> dict:
        gnb_docker_ip = self._get_cached_ip(gnb_id, net_name)     # ← 改
        ue_docker_ip = self._get_cached_ip(ue_id, net_name)       # ← 改
        session_ip = self.ue_ip_map.get(ue_id, "")
        up_teid, down_teid = self.ue_teid[ue_id]
        return {
            "ue_id": ue_id, "docker_ip": ue_docker_ip, "session_ip": session_ip,
            "up_teid": up_teid, "down_teid": down_teid, "gnb_ip": gnb_docker_ip,
        }

    def _write_tunnel_configs_batch(self, ue_id: str, gnb_id: str, net_name: str,
                                     session_ip: str = ""):
        """
        双通道更新：
        1. ZMQ 实时推送（主路径）
        2. 文件写入（兜底，兼容现有 gNB/UPF 逻辑）
        """
        # ZMQ 推送
        gnb_config = self._build_gnb_config(ue_id, gnb_id, net_name)
        upf_config = self._build_upf_config(ue_id, gnb_id, net_name)
        self._push_tunnel_update(
            gnb_id, ue_id,
            gnb_config["session_ip"], gnb_config["docker_ip"],
            gnb_config["up_teid"], gnb_config["down_teid"],
            upf_ip=gnb_config["upf_ip"]
        )
        self._push_tunnel_update(
            "upf-000", ue_id,
            upf_config["session_ip"], upf_config["docker_ip"],
            upf_config["up_teid"], upf_config["down_teid"],
            gnb_ip=upf_config["gnb_ip"]
        )
        self._push_flush_nat(ue_id, session_ip)

        # 文件兜底（异步，不阻塞主线程）
        def write_files():
            try:
                gnb_container = self._get_container_by_nodename(gnb_id)
                upf_container = self._get_container_by_nodename("upf-000")
                gnb_json = json.dumps(gnb_config).replace("'", "'\\''")
                upf_json = json.dumps(upf_config).replace("'", "'\\''")
                gnb_container.exec_run(["sh", "-c",
                    f"echo '{gnb_json}' > /tmp/ue_tunnel_{ue_id}.json && "
                    f"touch /tmp/ue_tunnel_reload.flag"])
                upf_container.exec_run(["sh", "-c",
                    f"echo '{upf_json}' > /tmp/ue_tunnel_{ue_id}.json && "
                    f"touch /tmp/ue_tunnel_reload.flag"])
            except Exception:
                pass
        threading.Thread(target=write_files, daemon=True).start()

    # ========== 系统参数 ==========
    def _setup_gnb_sysctl(self, gnb_id: str):
        iface = self._get_data_iface(gnb_id, "172.19.0.3") or "eth1"
        self._exec_in_container(gnb_id, ["sysctl", "-w", "net.ipv4.conf.all.rp_filter=0"])
        self._exec_in_container(gnb_id, ["sysctl", "-w", f"net.ipv4.conf.{iface}.rp_filter=0"])
        self._exec_in_container(gnb_id, ["sysctl", "-w", "net.ipv4.ip_forward=1"])
        self._exec_in_container(gnb_id, ["sysctl", "-w", f"net.ipv4.conf.{iface}.forwarding=1"])
        self._exec_in_container(gnb_id, ["iptables", "-P", "FORWARD", "ACCEPT"])

    def _setup_upf_sysctl(self):
        self._exec_in_container("upf-000", ["sysctl", "-w", "net.ipv4.conf.all.rp_filter=0"])
        self._exec_in_container("upf-000", ["sysctl", "-w", "net.ipv4.ip_forward=1"])

    # ========== UE 路由 ==========
    def _setup_ue_route(self, ue_id: str, gnb_docker_ip: str, session_ip: str, iface: str) -> bool:
        src_ip = session_ip.split('/')[0]
        cmd = ["ip", "route", "replace", "default", "via", gnb_docker_ip,
               "dev", iface, "onlink", "src", src_ip]
        ok = self._exec_in_container(ue_id, cmd)
        if ok:
            self._exec_in_container(ue_id, ["sysctl", "-w", "net.ipv4.conf.all.rp_filter=0"])
            self._exec_in_container(ue_id, ["sysctl", "-w", f"net.ipv4.conf.{iface}.rp_filter=0"])
        return ok

    def _configure_ue_session_ip(self, ue_id: str, session_ip: str, data_iface: str):
        self._exec_in_container(ue_id, ["ip", "addr", "del", session_ip, "dev", data_iface])
        ok = self._exec_in_container(ue_id, ["ip", "addr", "add", session_ip, "dev", data_iface])
        if ok:
            print(f"  [UE session IP] {ue_id} added {session_ip} dev {data_iface}", flush=True)

    def _configure_gnb_route_to_ue(self, gnb_id: str, session_ip: str, gnb_data_iface: str):
        self._exec_in_container(gnb_id, ["ip", "route", "replace", session_ip, "dev", gnb_data_iface])

    # ========== PREPARE：按需建立链路 ==========
    def _prepare_link(self, ue_id: str, gnb_id: str) -> Optional[Tuple[str, str]]:
        """
        按需为 UE 建立到指定 gNB 的链路。
        - 只连接网络，等待 IP 分配，获取接口名
        - 不添加会话 IP，不改默认路由（真正的切换在 COMMIT 阶段）
        返回 (iface_name, gnb_docker_ip)，失败返回 None。
        """
        net_name = self.bridge_prefix + gnb_id
        container = self._get_container_by_nodename(ue_id)

        # 1. 连接网络（若已连接则跳过）
        if not self._is_container_in_network(container, net_name):
            if not self._safe_connect(net_name, container, aliases=["ue"]):
                print(f"  [WARN] connect {ue_id} to {net_name} failed", flush=True)
                return None

        # 2. 等待 IP 分配（Docker 异步）
        gnb_ip, ue_ip = "", ""
        for _ in range(40):
            gnb_ip = self._get_container_ip_in_network(gnb_id, net_name)
            ue_ip = self._get_container_ip_in_network(ue_id, net_name)
            if gnb_ip and ue_ip:
                break
            time.sleep(0.05)

        if not gnb_ip or not ue_ip:
            print(f"  [WARN] {ue_id} IP lookup timeout in {net_name}", flush=True)
            return None

        # 3. 反查接口名
        result = container.exec_run(["bash", "-c",
            f"ip -o addr show | grep '{ue_ip.split('/')[0]}' | head -1 | awk '{{print $2}}'"])
        iface = result.output.decode().strip().rstrip(':') if result.exit_code == 0 else None
        if not iface:
            result = container.exec_run(["bash", "-c",
                "ip -o link show | awk -F: '$2 !~ /lo/ {print $2}' | sed 's/ //g' | tail -1"])
            iface = result.output.decode().strip() if result.exit_code == 0 else None

        if not iface:
            print(f"  [WARN] No interface for {ue_id} in {net_name}", flush=True)
            return None

        # 写入 IP 缓存
        self._ip_cache.setdefault(net_name, {})
        self._ip_cache[net_name][gnb_id] = gnb_ip
        self._ip_cache[net_name][ue_id] = ue_ip

        return (iface, gnb_ip)

    def _get_neighbors(self, gnb_id: str) -> List[str]:
        """返回所有其他 gNB（小规模场景下一次性预建全部）"""
        return [g for g in self.gnb_ids if g != gnb_id]

    # ========== 初始注册 ==========
    def configure_ue_routes(self, ue_id: str) -> bool:
        self._load_ue_ip_map()
        session_ip = self.ue_ip_map.get(ue_id)
        if not session_ip:
            return False

        # 只建立到默认 gNB 的链路
        result = self._prepare_link(ue_id, self.default_gnb)
        if not result:
            return False
        default_iface, default_gnb_ip = result

        self.current_data_net[ue_id] = self.bridge_prefix + self.default_gnb

        # 配置会话 IP 和默认路由
        self._configure_ue_session_ip(ue_id, session_ip, default_iface)
        self._setup_ue_route(ue_id, default_gnb_ip, session_ip, default_iface)

        # 系统参数
        self._allocate_teid(ue_id)
        self._setup_gnb_sysctl(self.default_gnb)
        self._setup_upf_sysctl()

        # gNB 回程路由
        self._configure_gnb_route_to_ue(self.default_gnb, session_ip, "eth1")

        # 隧道配置
        net_name = self.bridge_prefix + self.default_gnb
        self._write_tunnel_configs_batch(ue_id, self.default_gnb, net_name, session_ip)

        self.configured_ue.add(ue_id)

        # 注册后预建邻居
        threading.Thread(target=self._prefetch_neighbors, args=(ue_id, self.default_gnb), daemon=True).start()

        print(f"[+] {ue_id} configured (session {session_ip}, gnb {self.default_gnb})", flush=True)
        return True


    def _prefetch_neighbors(self, ue_id: str, current_gnb: str):
        """并行预建邻居 gNB 的链路"""
        time.sleep(0.5)
        neighbors = self._get_neighbors(current_gnb)

        def prefetch_one(nb):
            with self._prepared_lock:
                if ue_id in self._prepared_links and nb in self._prepared_links[ue_id]:
                    return
            result = self._prepare_link(ue_id, nb)
            if result:
                iface, gnb_ip = result
                with self._prepared_lock:
                    self._prepared_links.setdefault(ue_id, {})[nb] = (iface, gnb_ip)
                print(f"  [PREFETCH] {ue_id} pre-built link to {nb} via {iface}", flush=True)

        # 并行执行
        threads = []
        for nb in neighbors:
            t = threading.Thread(target=prefetch_one, args=(nb,), daemon=True)
            t.start()
            threads.append(t)

    def check_and_configure_new_ues(self) -> List[str]:
        self._load_ue_ip_map()
        newly_configured = []
        for ue_id, session_ip in self.ue_ip_map.items():
            if ue_id not in self.configured_ue and session_ip:
                if self.configure_ue_routes(ue_id):
                    newly_configured.append(ue_id)
        return newly_configured

    # ============================================================
    # 核心：Make-before-Break 切换
    # ============================================================
    def switch_link(self, ue_id: str, target_gnb: str):
        old_net = self.current_data_net.get(ue_id)
        target_net = self.bridge_prefix + target_gnb
        if old_net == target_net:
            return

        session_ip = self.ue_ip_map.get(ue_id)
        if not session_ip:
            print(f"  [WARN] {ue_id} no session IP", flush=True)
            return

        old_gnb = old_net.replace(self.bridge_prefix, "") if old_net else None
        src_ip = session_ip.split('/')[0]
        container = self._get_container_by_nodename(ue_id)

        # ============ PHASE 1: PREPARE ============
        t0 = time.time()

        # 检查预建池
        with self._prepared_lock:
            cached = self._prepared_links.get(ue_id, {}).get(target_gnb)
            if cached:
                self._prepared_links[ue_id].pop(target_gnb, None)

        if cached:
            target_iface, target_gnb_ip = cached
            print(f"  [PREPARE] {ue_id}->{target_gnb} HIT via {target_iface} (<1ms)", flush=True)
        else:
            result = self._prepare_link(ue_id, target_gnb)
            if not result:
                print(f"  [ERROR] PREPARE failed for {ue_id} -> {target_gnb}", flush=True)
                return
            target_iface, target_gnb_ip = result
            prepare_ms = int((time.time() - t0) * 1000)
            print(f"  [PREPARE] {ue_id}->{target_gnb} link via {target_iface} ({prepare_ms}ms)", flush=True)

        # 提前在目标 gNB 上添加回程路由（此时默认路由还指向旧 gNB，不会误导流量）
        self._configure_gnb_route_to_ue(target_gnb, session_ip, "eth1")

        # ============ PHASE 2: COMMIT ============
        t1 = time.time()

        # 从旧接口删除会话 IP（避免 ARP 双绑）
        old_iface = ""
        if old_net:
            old_ue_ip = self._get_container_ip_in_network(ue_id, old_net)
            if old_ue_ip:
                r = container.exec_run(["bash", "-c",
                    f"ip -o addr show | grep '{old_ue_ip.split('/')[0]}' | head -1 | awk '{{print $2}}'"])
                old_iface = r.output.decode().strip().rstrip(':') if r.exit_code == 0 else ""

        # 合并为一条 bash 脚本，全部在 UE 容器内完成
        parts = ["set +e"]
        if old_iface and old_iface != target_iface:
            parts.append(f"ip addr del {session_ip} dev {old_iface} 2>/dev/null")
        parts.append(f"ip addr add {session_ip} dev {target_iface} 2>/dev/null")
        parts.append(
            f"ip route replace default via {target_gnb_ip} dev {target_iface} "
            f"onlink src {src_ip}"
        )
        parts.append(
            f"ip route get {target_gnb_ip} | grep -q 'dev {target_iface}' && echo COMMIT_OK || echo COMMIT_FAIL"
        )
        commit_script = " ; ".join(parts)

        r = container.exec_run(["bash", "-c", commit_script])
        output = r.output.decode().strip() if r.output else ""
        commit_ms = int((time.time() - t1) * 1000)
        if "COMMIT_OK" in output:
            print(f"  [COMMIT] {ue_id} default -> {target_gnb} via {target_iface} ({commit_ms}ms)", flush=True)
        else:
            print(f"  [ERROR] COMMIT failed for {ue_id}: {output}", flush=True)
            return

        # ============ PHASE 3: 隧道 + NAT（ZMQ 推送）============
        t2 = time.time()
        self._write_tunnel_configs_batch(ue_id, target_gnb, target_net, session_ip)
        tunnel_ms = int((time.time() - t2) * 1000)
        print(f"  [TUNNEL] {ue_id} pushed to {target_gnb} and UPF ({tunnel_ms}ms)", flush=True)

        # 更新状态
        self.current_data_net[ue_id] = target_net

        # ============ PHASE 4: GRACE + CLEANUP ============
        # 检查该网络是否还有 pending cleanup（前一次切换遗留的）
        # 如果有，取消它（因为用户又切回来了或即将使用该网络）
        old_pending = self._pending_cleanup.get(ue_id)
        if old_pending and old_pending['net'] == target_net:
            # 用户切回到正在等待清理的网络，直接取消清理
            self._pending_cleanup.pop(ue_id, None)
            print(f"  [GRACE] {ue_id} came back to {target_net}, cancel pending cleanup", flush=True)

        if old_net and old_gnb:
            # 生成一个代际号，用于识别 cleanup 是否有效
            generation = time.time()
            self._pending_cleanup[ue_id] = {'net': old_net, 'gen': generation}

            def delayed_cleanup(cleanup_net=old_net, cleanup_gnb=old_gnb, gen=generation):
                time.sleep(5)
                current = self._pending_cleanup.get(ue_id)
                if not current or current['gen'] != gen:
                    return
                if self.current_data_net.get(ue_id) == cleanup_net:
                    self._pending_cleanup.pop(ue_id, None)
                    return

                # 新增：检查该网络是否在预建池中
                with self._prepared_lock:
                    in_prefetch = (ue_id in self._prepared_links and
                                   cleanup_gnb in self._prepared_links[ue_id])

                try:
                    # 删除旧 gNB 上的回程路由（总是做）
                    self._exec_in_container(cleanup_gnb, ["ip", "route", "del", session_ip])

                    if in_prefetch:
                        # 预建池中保留：只删除会话 IP，不断开网络
                        c = self._get_container_by_nodename(ue_id)
                        old_ue_ip = self._get_container_ip_in_network(ue_id, cleanup_net)
                        if old_ue_ip:
                            r = c.exec_run(["bash", "-c",
                                f"ip -o addr show | grep '{old_ue_ip.split('/')[0]}' | head -1 | awk '{{print $2}}'"])
                            oi = r.output.decode().strip().rstrip(':') if r.exit_code == 0 else None
                            if oi:
                                c.exec_run(["ip", "addr", "del", session_ip, "dev", oi])
                        print(f"  [CLEANUP] {ue_id} kept {cleanup_net} (in prefetch pool)", flush=True)
                    else:
                        # 非预建池：完全断开
                        c = self._get_container_by_nodename(ue_id)
                        if not self._is_container_in_network(c, cleanup_net):
                            self._pending_cleanup.pop(ue_id, None)
                            return
                        old_ue_ip = self._get_container_ip_in_network(ue_id, cleanup_net)
                        if old_ue_ip:
                            r = c.exec_run(["bash", "-c",
                                f"ip -o addr show | grep '{old_ue_ip.split('/')[0]}' | head -1 | awk '{{print $2}}'"])
                            oi = r.output.decode().strip().rstrip(':') if r.exit_code == 0 else None
                            if oi:
                                c.exec_run(["ip", "addr", "del", session_ip, "dev", oi])
                        self.client.networks.get(cleanup_net).disconnect(c, force=True)
                        self._invalidate_ip_cache(cleanup_net)
                        print(f"  [CLEANUP] {ue_id} released {cleanup_net}", flush=True)
                except docker.errors.APIError as e:
                    if "not connected" not in str(e).lower():
                        print(f"  [WARN] cleanup {cleanup_net}: {e}", flush=True)
                except Exception as e:
                    print(f"  [WARN] cleanup {cleanup_net}: {e}", flush=True)
                finally:
                    cur = self._pending_cleanup.get(ue_id)
                    if cur and cur['gen'] == gen:
                        self._pending_cleanup.pop(ue_id, None)

            threading.Thread(target=delayed_cleanup, daemon=True).start()

        # ============ PHASE 5: 后台预建新邻居 ============
        def prefetch():
            time.sleep(0.3)
            neighbors = self._get_neighbors(target_gnb)

            def prefetch_one(nb):
                if nb == old_gnb:
                    return
                with self._prepared_lock:
                    if ue_id in self._prepared_links and nb in self._prepared_links[ue_id]:
                        return
                result = self._prepare_link(ue_id, nb)
                if result:
                    iface, gnb_ip = result
                    with self._prepared_lock:
                        self._prepared_links.setdefault(ue_id, {})[nb] = (iface, gnb_ip)
                    print(f"  [PREFETCH] {ue_id} pre-built link to {nb}", flush=True)

            threads = []
            for nb in neighbors:
                t = threading.Thread(target=prefetch_one, args=(nb,), daemon=True)
                t.start()
                threads.append(t)
        threading.Thread(target=prefetch, daemon=True).start()

        total_ms = int((time.time() - t0) * 1000)
        print(f"[+] {ue_id} switched to {target_gnb} (total {total_ms}ms)", flush=True)

    # ========== 网络管理 ==========
    def _disconnect_all_containers_from_network(self, net_name: str):
        try:
            net = self.client.networks.get(net_name)
            for container in net.containers:
                try:
                    net.disconnect(container, force=True)
                except docker.errors.APIError:
                    pass
        except docker.errors.NotFound:
            return

    def _remove_network(self, net_name: str):
        try:
            self.client.networks.get(net_name).remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError:
            pass

    def _cleanup_all_data_networks(self):
        print("[RANLinkManager] Cleaning up data-plane networks...", flush=True)
        for gnb in self.gnb_ids:
            net_name = self.bridge_prefix + gnb
            self._disconnect_all_containers_from_network(net_name)
            self._remove_network(net_name)

    def _create_network(self, net_name: str):
        try:
            self.client.networks.get(net_name)
        except docker.errors.NotFound:
            self.client.networks.create(net_name, driver="bridge", check_duplicate=True)

    def _is_container_in_network(self, container, net_name: str) -> bool:
        try:
            network = self.client.networks.get(net_name)
            return container.id in [c.id for c in network.containers]
        except docker.errors.NotFound:
            return False

    # ========== 默认路由备份/恢复（解决 Docker 连接冲突） ==========
    def _backup_default_routes(self, container):
        """备份容器当前的默认路由"""
        routes = []
        try:
            result = container.exec_run(["ip", "route", "show", "default"])
            if result.exit_code == 0:
                for line in result.output.decode().strip().split("\n"):
                    if line.strip():
                        routes.append(line.strip())
        except Exception:
            pass
        return routes

    def _restore_default_routes(self, container, routes):
        """恢复之前备份的默认路由"""
        try:
            for route in routes:
                container.exec_run(["ip", "route", "add"] + route.split())
        except Exception:
            pass

    def _cleanup_container_routes(self, container):
        """清空容器的默认路由和路由缓存（为 Docker 连接腾位）"""
        try:
            container.exec_run(["ip", "route", "flush", "default"])
            container.exec_run(["ip", "route", "flush", "cache"])
        except Exception:
            pass

    def _safe_connect(self, net_name: str, container, aliases=None) -> bool:
        """
        安全连接 Docker 网络。
        处理 'file exists' 类错误：备份默认路由 → 清理 → 连接 → 恢复。
        """
        net = self.client.networks.get(net_name)
        if self._is_container_in_network(container, net_name):
            return True

        # 1. 备份现有默认路由，并清空（避免 Docker 设置网关时冲突）
        backup_routes = self._backup_default_routes(container)
        self._cleanup_container_routes(container)

        try:
            net.connect(container, aliases=aliases)
            self._restore_default_routes(container, backup_routes)
            return True
        except docker.errors.APIError as e:
            err = str(e).lower()
            if "file exists" in err or "gateway" in err or "already exists" in err:
                # 2. 用 docker CLI 强制断开后重试
                try:
                    subprocess.run(
                        ["docker", "network", "disconnect", "-f", net_name, container.id],
                        capture_output=True, timeout=5
                    )
                    time.sleep(1)
                except Exception:
                    pass

                self._cleanup_container_routes(container)
                try:
                    net.connect(container, aliases=aliases)
                    self._restore_default_routes(container, backup_routes)
                    return True
                except Exception as e2:
                    print(f"  [ERROR] connect to {net_name} failed: {e2}", flush=True)
                    self._restore_default_routes(container, backup_routes)
                    return False
            # 其他错误：恢复默认路由后抛出
            self._restore_default_routes(container, backup_routes)
            raise

    def _connect_gNB(self, gnb_id: str):
        net_name = self.bridge_prefix + gnb_id
        container = self._get_container_by_nodename(gnb_id)
        if self._safe_connect(net_name, container, aliases=["gnb"]):
            print(f"  gNB {gnb_id} connected to {net_name}", flush=True)

    def _connect_ue(self, ue_id: str, net_name: str) -> bool:
        container = self._get_container_by_nodename(ue_id)
        return self._safe_connect(net_name, container, aliases=["ue"])

    def _setup_amf_route(self):
        self._exec_in_container("amf-000", ["ip", "route", "replace", "10.60.0.0/24", "via", "10.150.0.5"])

    def setup(self):
        print("[RANLinkManager] Setting up data-plane networks...", flush=True)
        try:
            default_net = self.bridge_prefix + self.default_gnb
            self.client.networks.get(default_net)
            upf_container = self._get_container_by_nodename("upf-000")
            if self._is_container_in_network(upf_container, default_net):
                print("  Data networks already configured, skip setup", flush=True)
                return
        except Exception:
            pass

        self._cleanup_all_data_networks()
        upf_container = self._get_container_by_nodename("upf-000")
        for gnb in self.gnb_ids:
            net_name = self.bridge_prefix + gnb
            self._create_network(net_name)
            time.sleep(1)
            self._connect_gNB(gnb)
            if not self._is_container_in_network(upf_container, net_name):
                self._safe_connect(net_name, upf_container)
            self._setup_gnb_sysctl(gnb)

        self._setup_amf_route()
        print("[RANLinkManager] Network infrastructure ready", flush=True)

    def cleanup(self):
        """只清理 Docker 网络，不关闭 ZMQ"""
        self._cleanup_all_data_networks()

    def shutdown(self):
        """进程退出时调用，关闭所有 ZMQ 资源"""
        try:
            self.zmq_socket.close(linger=0)
            self.zmq_ctx.term()
        except Exception:
            pass
        try:
            self._hb_socket.close(linger=0)
            self._hb_ctx.term()
        except Exception:
            pass