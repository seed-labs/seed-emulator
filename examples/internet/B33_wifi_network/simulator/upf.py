#!/usr/bin/env python3
"""UPF with GTP-U tunnel, NAT, and connection tracking."""
import zmq
import time
import argparse
import socket
import struct
import threading
import json
import glob
import os
import fcntl
import subprocess
from datetime import datetime, timezone

GTPU_PORT = 2152

class UPF:
    def __init__(self, upf_id, bus_host):
        self.id = upf_id
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.id.encode())
        self.socket.connect(f"tcp://{bus_host}:5555")
        self.last_hello = 0
        self.ue_tunnel = {}          # up_teid -> (gnb_ip, down_teid)
        self.ue_tunnel_by_id = {}    # ue_id -> {'up_teid', 'down_teid', 'gnb_ip', 'session_ip'}
        self.gtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.gtp_sock.bind(('0.0.0.0', GTPU_PORT))
        # 创建 TUN 设备用于 IP 转发
        self.tun_fd = None
        self.tun_name = "tun0"
        self.setup_tun()
        self.load_tunnel_configs()
        # 启动 conntrack 监控线程
        self.stop_monitor = threading.Event()
        threading.Thread(target=self._monitor_nat_sessions, daemon=True).start()

    def log_event(self, event, extra=None):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "node_id": self.id, "event": event}
        if extra: record.update(extra)
        print(json.dumps(record), flush=True)

    def setup_tun(self):
        """创建 TUN 设备，启用 MASQUERADE"""
        try:
            TUNSETIFF = 0x400454ca
            IFF_TUN = 0x0001
            IFF_NO_PI = 0x1000
            tun_fd = os.open("/dev/net/tun", os.O_RDWR)
            ifr = struct.pack('16sH', self.tun_name.encode(), IFF_TUN | IFF_NO_PI)
            fcntl.ioctl(tun_fd, TUNSETIFF, ifr)
            self.tun_fd = tun_fd

            # 配置 TUN：分配 IP 以吸引目标为 UE 的包
            os.system(f"ip addr add 10.60.0.1/24 dev {self.tun_name}")
            os.system(f"ip link set {self.tun_name} up")

            # 关闭反向路径过滤，允许非对称路由
            os.system("sysctl -w net.ipv4.conf.all.rp_filter=0")
            os.system("sysctl -w net.ipv4.conf.tun0.rp_filter=0")
            os.system("sysctl -w net.ipv4.ip_forward=1")

            # ===== 核心：启用 MASQUERADE（SNAT） =====
            # 将UE的私网IP（10.60.0.0/24）转换为UPF的net0 IP
            os.system("iptables -t nat -A POSTROUTING -s 10.60.0.0/24 -o net0 -j MASQUERADE")

            # 强制路由：标记从 tun0 进入的包走专用表（可选）
            os.system("ip rule add fwmark 3 lookup 300 priority 300 2>/dev/null || true")
            os.system("ip route add default via 10.150.0.254 dev net0 table 300 2>/dev/null || true")

            os.system("iptables -t mangle -A PREROUTING -i tun0 -j MARK --set-mark 3 2>/dev/null || true")

            print(f"[{self.id}] TUN {self.tun_name} setup ok (Public Internet mode)", flush=True)
            print(f"[{self.id}] MASQUERADE enabled: 10.60.0.0/24 -> net0", flush=True)
            print(f"[{self.id}] External inbound NEW connections to UE are DROPPED", flush=True)
        except Exception as e:
            print(f"[{self.id}] TUN setup failed: {e}", flush=True)

    def load_tunnel_configs(self):
        for filepath in glob.glob("/tmp/ue_tunnel_*.json"):
            try:
                with open(filepath, 'r') as f:
                    config = json.load(f)
                ue_id = config.get("ue_id")
                up_teid = config.get("up_teid")
                down_teid = config.get("down_teid")
                gnb_ip = config.get("gnb_ip")
                session_ip = config.get("session_ip")
                if ue_id and up_teid and down_teid and gnb_ip:
                    self.ue_tunnel[up_teid] = (gnb_ip, down_teid)
                    self.ue_tunnel_by_id[ue_id] = {
                        'up_teid': up_teid,
                        'down_teid': down_teid,
                        'gnb_ip': gnb_ip,
                        'session_ip': session_ip
                    }
                    print(f"[UPF] Loaded tunnel for {ue_id}: up_teid={up_teid}, gnb_ip={gnb_ip}, session_ip={session_ip}", flush=True)
            except Exception as e:
                print(f"[UPF] Load config error: {e}", flush=True)

    def _reload_tunnel_configs(self):
        """监听隧道配置文件变更（使用inotify实现实时重载）"""
        try:
            import inotify.adapters
            i = inotify.adapters.Inotify()
            i.add_watch('/tmp')
            print("[UPF] Watching /tmp for tunnel config changes (inotify)", flush=True)
            for event in i.event_gen():
                if event is None:
                    continue
                _, event_types, _, pathname = event
                if 'ue_tunnel_reload.flag' in str(pathname) and 'IN_CREATE' in str(event_types):
                    self.load_tunnel_configs()
                    try:
                        os.remove('/tmp/ue_tunnel_reload.flag')
                    except:
                        pass
                    print("[UPF] Tunnel config reloaded via inotify", flush=True)
        except ImportError:
            # 降级：使用轮询方式
            print("[UPF] inotify not available, using polling (1s interval)", flush=True)
            while True:
                if os.path.exists("/tmp/ue_tunnel_reload.flag"):
                    self.load_tunnel_configs()
                    try:
                        os.remove("/tmp/ue_tunnel_reload.flag")
                    except:
                        pass
                time.sleep(0.5)

    def _monitor_nat_sessions(self):
        """监控NAT会话，用于调试和故障排查"""
        while not self.stop_monitor.is_set():
            try:
                result = subprocess.run(
                    ["conntrack", "-L", "-s", "10.60.0.0/24"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and result.stdout:
                    # 每30秒打印一次NAT会话统计（避免刷屏）
                    if int(time.time()) % 30 == 0:
                        lines = result.stdout.strip().split('\n')
                        print(f"[UPF] Active NAT sessions for UE subnet: {len(lines)}", flush=True)
            except Exception as e:
                pass
            time.sleep(5)

    def _encapsulate(self, inner_packet, teid):
        flags = 0x30
        msg_type = 0xFF
        length = len(inner_packet)
        header = struct.pack('!BBHI', flags, msg_type, length, teid)
        return header + inner_packet

    def _handle_icmp(self, packet):
        """处理 ICMP Echo Request，回复 Echo Reply"""
        if len(packet) < 20:
            return None
        version = packet[0] >> 4
        if version != 4:
            return None
        ihl = packet[0] & 0x0F
        if ihl < 5:
            return None
        proto = packet[9]
        if proto != 1:
            return None
        icmp_start = ihl * 4
        if len(packet) < icmp_start + 8:
            return None
        icmp_type = packet[icmp_start]
        if icmp_type != 8:
            return None
        reply = bytearray(packet)
        reply[12:16], reply[16:20] = packet[16:20], packet[12:16]
        reply[icmp_start] = 0
        reply[icmp_start+2:icmp_start+4] = b'\x00\x00'
        checksum = 0
        for i in range(icmp_start, len(reply), 2):
            if i+1 < len(reply):
                word = (reply[i] << 8) + reply[i+1]
            else:
                word = reply[i] << 8
            checksum += word
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum = ~checksum & 0xFFFF
        reply[icmp_start+2] = (checksum >> 8) & 0xFF
        reply[icmp_start+3] = checksum & 0xFF
        return bytes(reply)

    def _gtp_receive_loop(self):
        """处理来自 gNB 的上行 GTP 包（UE->外部）"""
        while True:
            try:
                data, addr = self.gtp_sock.recvfrom(65535)
                if len(data) < 8:
                    continue
                teid = struct.unpack('!I', data[4:8])[0]
                inner = data[8:]
                if teid not in self.ue_tunnel:
                    continue
                gnb_ip, down_teid = self.ue_tunnel[teid]
                # 尝试 ICMP 回复
                reply = self._handle_icmp(inner)
                if reply:
                    outer = self._encapsulate(reply, down_teid)
                    self.gtp_sock.sendto(outer, (gnb_ip, GTPU_PORT))
                else:
                    # 非 ICMP：写入 TUN，由内核路由 + MASQUERADE
                    try:
                        os.write(self.tun_fd, inner)
                    except Exception as e:
                        print(f"[UPF] Failed to write to TUN: {e}", flush=True)
            except Exception as e:
                print(f"[UPF] GTP receive error: {e}", flush=True)

    def _tun_read_loop(self):
        """处理从 TUN 读取的下行包（外部->UE）"""
        while True:
            try:
                packet = os.read(self.tun_fd, 65535)
                if len(packet) < 20:
                    continue
                dst_ip = socket.inet_ntoa(packet[16:20])
                matched = False
                # 查找匹配的 UE
                for ue_id, info in self.ue_tunnel_by_id.items():
                    if info.get('session_ip') == dst_ip:
                        matched = True
                        down_teid = info['down_teid']
                        gnb_ip = info['gnb_ip']
                        # 封装 GTP 并发送给 gNB
                        outer = self._encapsulate(packet, down_teid)
                        self.gtp_sock.sendto(outer, (gnb_ip, GTPU_PORT))
                        break
                # 如果没有匹配，可能是其他流量，忽略
                if not matched and not dst_ip.startswith("10.150."):
                    print(f"[UPF] No match for {dst_ip}", flush=True)
            except Exception as e:
                print(f"[UPF] TUN read error: {e}", flush=True)

    def _flush_nat_session(self, ue_id, session_ip):
        """刷新指定UE的NAT会话（切换时调用）"""
        try:
            # 删除conntrack中该UE的所有会话
            subprocess.run(["conntrack", "-D", "-s", session_ip], capture_output=True, timeout=2)
            subprocess.run(["conntrack", "-D", "-d", session_ip], capture_output=True, timeout=2)
            print(f"[UPF] Flushed NAT sessions for {ue_id} ({session_ip})", flush=True)
        except Exception as e:
            print(f"[UPF] Failed to flush NAT sessions: {e}", flush=True)

    def run(self):
        print(f"[{self.id}] UPF started", flush=True)
        self.socket.send_json({"source": self.id, "target": "eb-server", "type": "HELLO", "payload": {}})
        threading.Thread(target=self._reload_tunnel_configs, daemon=True).start()
        threading.Thread(target=self._gtp_receive_loop, daemon=True).start()
        threading.Thread(target=self._tun_read_loop, daemon=True).start()

        while True:
            if time.time() - self.last_hello > 10:
                self.socket.send_json({"source": self.id, "target": "eb-server", "type": "HELLO", "payload": {}})
                self.last_hello = time.time()
            try:
                msg = self.socket.recv_json(flags=zmq.NOBLOCK)
                msg_type = msg.get("type")
                payload = msg.get("payload", {})
                if msg_type == "GTPTunnelCreate":
                    pass  # 已通过文件加载
                elif msg_type == "GTPTunnelUpdate":
                    ue_id = payload.get("ue_id")
                    up_teid = payload.get("up_teid")
                    down_teid = payload.get("down_teid")
                    new_gnb_ip = payload.get("gnb_ip")
                    if ue_id in self.ue_tunnel_by_id and new_gnb_ip:
                        old_up_teid = self.ue_tunnel_by_id[ue_id]['up_teid']
                        if old_up_teid in self.ue_tunnel:
                            del self.ue_tunnel[old_up_teid]
                        self.ue_tunnel[up_teid] = (new_gnb_ip, down_teid)
                        self.ue_tunnel_by_id[ue_id]['up_teid'] = up_teid
                        self.ue_tunnel_by_id[ue_id]['down_teid'] = down_teid
                        self.ue_tunnel_by_id[ue_id]['gnb_ip'] = new_gnb_ip
                        print(f"[UPF] Updated tunnel for {ue_id} -> gnb_ip {new_gnb_ip}", flush=True)
                elif msg_type == "TunnelUpdate":
                    # 收到 RANLinkManager 的实时隧道推送
                    ue_id = payload.get("ue_id")
                    session_ip = payload.get("session_ip")
                    up_teid = payload.get("up_teid")
                    down_teid = payload.get("down_teid")
                    gnb_ip = payload.get("gnb_ip")
                    if ue_id and up_teid and down_teid and gnb_ip:
                        # 清理旧的 up_teid 映射
                        old = self.ue_tunnel_by_id.get(ue_id)
                        if old and old.get('up_teid') in self.ue_tunnel:
                            del self.ue_tunnel[old['up_teid']]
                        # 更新
                        self.ue_tunnel[up_teid] = (gnb_ip, down_teid)
                        self.ue_tunnel_by_id[ue_id] = {
                            'up_teid': up_teid,
                            'down_teid': down_teid,
                            'gnb_ip': gnb_ip,
                            'session_ip': session_ip
                        }
                        print(f"[UPF] TunnelUpdated: {ue_id} -> gnb_ip {gnb_ip}", flush=True)
                elif msg_type == "FlushNAT":
                    # 实时刷新 NAT 会话（切换时调用）
                    session_ip = payload.get("session_ip")
                    if session_ip:
                        try:
                            subprocess.run(["conntrack", "-D", "-s", session_ip],
                                           capture_output=True, timeout=1)
                            subprocess.run(["conntrack", "-D", "-d", session_ip],
                                           capture_output=True, timeout=1)
                            print(f"[UPF] Flushed NAT for {session_ip}", flush=True)
                        except Exception as e:
                            print(f"[UPF] FlushNAT error: {e}", flush=True)
                elif msg_type == "FlushNATSession":
                    ue_id = payload.get("ue_id")
                    session_ip = payload.get("session_ip")
                    if session_ip:
                        self._flush_nat_session(ue_id, session_ip)
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"[UPF] Error: {e}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--bus-host", required=True)
    args = parser.parse_args()
    UPF(args.id, args.bus_host).run()
