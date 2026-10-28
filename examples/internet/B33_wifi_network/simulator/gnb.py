#!/usr/bin/env python3
"""gNB simulator with GTP-U tunnel, N2 and Xn handover support."""
import zmq
import json
import time
import argparse
import socket
import struct
import os
import fcntl
import threading
import glob
from datetime import datetime, timezone

GTPU_PORT = 2152
DEFAULT_UPF_IP = "172.19.0.3"


class GNB:
    def __init__(self, gnb_id, bus_host):
        self.id = gnb_id
        self.context = zmq.Context()
        self.ue_socket = self.context.socket(zmq.ROUTER)
        self.ue_socket.bind("tcp://*:5556")
        self.bus_socket = self.context.socket(zmq.DEALER)
        self.bus_socket.setsockopt(zmq.IDENTITY, self.id.encode())
        self.bus_socket.connect(f"tcp://{bus_host}:5555")
        self.ue_identities = {}
        self.pending_msgs = {}
        self.last_hello = 0

        # GTP-U
        self.gtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.gtp_sock.bind(('0.0.0.0', GTPU_PORT))
        self.tun_fd = None
        self.tun_name = "tun0"
        self.setup_tun()

        self.ue_tunnel = {}           # ue_id -> (up_teid, down_teid, upf_ip)
        self.docker_ip_to_ueid = {}   # docker_ip -> ue_id
        self.session_ip_to_ueid = {}  # session_ip -> ue_id
        self.load_tunnel_configs()
        # 存储 UE 当前数据面网关（用于切换时更新）
        self.ue_gw_ip = {}   # ue_id -> gNB data IP
        self.handover_pending_ues = set()

    def log_event(self, event, extra=None):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "node_id": self.id, "event": event}
        if extra:
            record.update(extra)
        print(json.dumps(record), flush=True)

    def setup_tun(self):
        try:
            import subprocess
            result = subprocess.run(["ip", "route", "get", DEFAULT_UPF_IP], capture_output=True, text=True)
            data_iface = "eth1"
            # if result.returncode == 0:
            #     parts = result.stdout.split()
            #     for i, part in enumerate(parts):
            #         if part == "dev" and i+1 < len(parts):
            #             data_iface = parts[i+1]
            #             break

            TUNSETIFF = 0x400454ca
            IFF_TUN = 0x0001
            IFF_NO_PI = 0x1000
            tun_fd = os.open("/dev/net/tun", os.O_RDWR)
            ifr = struct.pack('16sH', self.tun_name.encode(), IFF_TUN | IFF_NO_PI)
            fcntl.ioctl(tun_fd, TUNSETIFF, ifr)
            self.tun_fd = tun_fd

            os.system(f"ip addr add 10.254.0.1/32 dev {self.tun_name}")
            os.system(f"ip link set {self.tun_name} up")
            os.system("ip rule del fwmark 1 lookup 100 2>/dev/null || true")
            os.system("ip rule add fwmark 1 lookup 100 priority 100")
            os.system("ip route del default dev tun0 table 100 2>/dev/null || true")
            os.system(f"ip route add default dev {self.tun_name} table 100")
            os.system(f"iptables -t mangle -D PREROUTING -i {data_iface} -j MARK --set-mark 1 2>/dev/null || true")
            os.system(f"iptables -t mangle -A PREROUTING -i {data_iface} -j MARK --set-mark 1")
            os.system("sysctl -w net.ipv4.ip_forward=1")
            os.system(f"sysctl -w net.ipv4.conf.{data_iface}.forwarding=1")
            os.system("sysctl -w net.ipv4.conf.all.rp_filter=0")
            os.system(f"sysctl -w net.ipv4.conf.{data_iface}.rp_filter=0")
            print(f"[{self.id}] TUN setup ok (iface={data_iface})", flush=True)
        except Exception as e:
            print(f"[{self.id}] TUN setup failed: {e}", flush=True)

    def load_tunnel_configs(self):
        for filepath in glob.glob("/tmp/ue_tunnel_*.json"):
            try:
                with open(filepath, 'r') as f:
                    config = json.load(f)
                ue_id = config.get("ue_id")
                docker_ip = config.get("docker_ip")
                session_ip = config.get("session_ip")
                up_teid = config.get("up_teid")
                down_teid = config.get("down_teid")
                upf_ip = config.get("upf_ip", DEFAULT_UPF_IP)
                if ue_id and docker_ip and up_teid:
                    self.docker_ip_to_ueid[docker_ip] = ue_id
                    if session_ip:
                        self.session_ip_to_ueid[session_ip] = ue_id
                    self.ue_tunnel[ue_id] = (up_teid, down_teid, upf_ip)
                    self.ue_gw_ip[ue_id] = docker_ip  # 数据面网关IP（gNB IP）
                    print(f"[{self.id}] Loaded tunnel for {ue_id}", flush=True)
            except Exception:
                pass

    def _reload_tunnel_configs(self):
        while True:
            if os.path.exists("/tmp/ue_tunnel_reload.flag"):
                self.load_tunnel_configs()
                os.remove("/tmp/ue_tunnel_reload.flag")
            time.sleep(0.2)

    def _encapsulate(self, inner_packet, teid):
        flags = 0x30
        msg_type = 0xFF
        length = len(inner_packet)
        header = struct.pack('!BBHI', flags, msg_type, length, teid)
        return header + inner_packet

    def _send_to_upf(self, inner_packet, teid, upf_ip):
        outer = self._encapsulate(inner_packet, teid)
        self.gtp_sock.sendto(outer, (upf_ip, GTPU_PORT))

    def _send_to_eventbus(self, target, msg_type, payload):
        self.bus_socket.send_json({
            "source": self.id,
            "target": target,
            "type": msg_type,
            "payload": payload
        })

    def _send_to_ue(self, ue_id, msg):
        if ue_id in self.ue_identities:
            identity = self.ue_identities[ue_id]
            self.ue_socket.send_multipart([identity, json.dumps(msg).encode()])
            return True
        else:
            if ue_id not in self.pending_msgs:
                self.pending_msgs[ue_id] = []
            self.pending_msgs[ue_id].append(msg)
            return False

    def _flush_pending(self, ue_id):
        if ue_id in self.pending_msgs:
            for msg in self.pending_msgs.pop(ue_id):
                self._send_to_ue(ue_id, msg)

    def _gtp_receive_loop(self):
        while True:
            try:
                data, addr = self.gtp_sock.recvfrom(65535)
                if len(data) < 8:
                    continue
                teid = struct.unpack('!I', data[4:8])[0]
                inner = data[8:]
                print(f"[{self.id}] Received GTP from {addr}, TEID={teid}, len={len(inner)}", flush=True)
                matched = False
                for ue_id, (up_teid, down_teid, upf_ip) in self.ue_tunnel.items():
                    if teid == down_teid:
                        matched = True
                        print(f"[{self.id}] Matched UE {ue_id}, down_teid={down_teid}, writing to TUN", flush=True)
                        os.write(self.tun_fd, inner)
                        break
                if not matched:
                    print(f"[{self.id}] No match for TEID {teid}", flush=True)
            except Exception as e:
                print(f"[{self.id}] GTP receive loop error: {e}", flush=True)

    def _tun_read_loop(self):
        while True:
            try:
                packet = os.read(self.tun_fd, 65535)
                if len(packet) < 20:
                    continue
                # print(f"[{self.id}] TUN read len={len(packet)}, first 20 bytes: {packet[:20].hex()}", flush=True)
                src_ip = socket.inet_ntoa(packet[12:16])
                # dst_ip = socket.inet_ntoa(packet[16:20])
                # print(f"[{self.id}] TUN read: src={src_ip}, dst={dst_ip}", flush=True)
                ue_id = self.session_ip_to_ueid.get(src_ip)
                if ue_id is None:
                    ue_id = self.docker_ip_to_ueid.get(src_ip)
                    if ue_id is None:
                        continue
                    # print(f"[{self.id}] Unknown src IP {src_ip}, dropping", flush=True)
                if ue_id not in self.ue_tunnel:
                    continue
                up_teid, down_teid, upf_ip = self.ue_tunnel[ue_id]
                self._send_to_upf(packet, up_teid, upf_ip)
            except Exception:
                pass

    # ---------- 切换处理 ----------
    def _handle_handover_required(self, ue_id, target_gnb):
        """外部触发 N2 切换（由 mobility_simulator 发送 TriggerHandover）"""
        # 查询 UE 会话信息（可从 AMF 获取，但这里我们通过自己的隧道信息）
        if ue_id not in self.ue_tunnel:
            self.log_event("HandoverFailed", {"ue_id": ue_id, "reason": "No tunnel"})
            return
        # 发起 N2 切换：向 AMF 发送 HandoverRequired
        self._send_to_eventbus("amf-000", "HandoverRequired", {
            "ue_id": ue_id,
            "target_gnb": target_gnb
        })
        self.log_event("HandoverRequiredSent", {"ue_id": ue_id, "target": target_gnb})

    def _handle_handover_request(self, payload):
        """目标 gNB 收到 HandoverRequest（来自 AMF）"""
        ue_id = payload.get("ue_id")
        session_ip = payload.get("session_ip")
        up_teid = payload.get("up_teid")
        down_teid = payload.get("down_teid")
        # 准备数据面资源（这里由 RANLinkManager 完成，但我们无法直接调用，需通知外部）
        # 由于 RANLinkManager 在外部，我们发送消息给一个控制节点？或者我们通过文件方式？
        # 实际上，RANLinkManager 是 Python 类，在 mobility_simulator 中运行，不能直接调用。
        # 我们只能通过 EventBus 发送消息，但 RANLinkManager 不是 ZMQ 节点。
        # 解决方案：在 mobility_simulator 中监听此类消息？但 mobility_simulator 不参与 ZMQ。
        # 我们改用文件方式：目标 gNB 写入 /tmp/handover_prepare_ue_id 文件，由外部脚本读取？
        # 或者更简单：我们假设目标 gNB 自己能够完成准备（因为它有权访问 Docker API）。
        # 但 gNB 容器内没有 docker 客户端。因此，我们只能依赖外部 RANLinkManager。
        # 为了简化，我们让 RANLinkManager 在切换决策时提前准备目标 gNB，然后目标 gNB 在这里仅是响应。
        # 所以我们在此只回复 ACK，并携带数据面 IP。
        # 数据面 IP 可从自己的接口获取（eth1 IP）。
        data_ip = self._get_data_ip()
        self.handover_pending_ues.add(ue_id)
        self._send_to_eventbus("amf-000", "HandoverRequestAck", {
            "ue_id": ue_id,
            "data_ip": data_ip,
            "up_teid": up_teid,
            "down_teid": down_teid
        })
        self.log_event("HandoverRequestAckSent", {"ue_id": ue_id})

    def _handle_handover_command(self, payload):
        """源 gNB 收到 HandoverCommand（来自 AMF），通知 UE 重配"""
        ue_id = payload.get("ue_id")
        target_gnb_ip = payload.get("target_gnb_ip")  # 控制面 IP
        # 发送 RRCReconfiguration 给 UE，携带目标 gNB 的控制面 IP
        self._send_to_ue(ue_id, {
            "type": "RRCReconfiguration",
            "payload": {
                "ue_id": ue_id,
                "target_gnb_ip": target_gnb_ip,
                "new_data_gw": None  # 数据面网关由 UE 从网络配置获取？
            }
        })

    def _handle_handover_notify(self, payload):
        """目标 gNB 收到 UE 的 RRCReconfigurationComplete 后，通知 AMF"""
        ue_id = payload.get("ue_id")
        self._send_to_eventbus("amf-000", "HandoverNotify", {"ue_id": ue_id})

    def _get_data_ip(self):
        """获取本 gNB 的数据面 IP（eth1）"""
        try:
            result = os.popen("ip -4 addr show eth1 | grep inet | awk '{print $2}' | cut -d/ -f1").read().strip()
            if result:
                return result
        except:
            pass
        return ""

    def _get_ctrl_ip(self):
        """获取 net0 接口的 IP（控制面 IP）"""
        try:
            import subprocess
            result = subprocess.run(["ip", "-4", "addr", "show", "net0", "scope", "global"],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            return parts[1].split('/')[0]
        except Exception:
            pass
        return ""

    def run(self):
        print(f"[{self.id}] gNB started", flush=True)
        # 获取控制面 IP（net0）
        ctrl_ip = self._get_ctrl_ip()
        if ctrl_ip:
            self._send_to_eventbus("amf-000", "GNBInfo", {
                "gnb_id": self.id,
                "ctrl_ip": ctrl_ip
            })
        self.last_gnb_info_time = time.time()
        self.gnb_info_count = 0
        self.gnb_info_acknowledged = False
        self._send_to_eventbus("eb-server", "HELLO", {})
        threading.Thread(target=self._reload_tunnel_configs, daemon=True).start()
        threading.Thread(target=self._gtp_receive_loop, daemon=True).start()
        threading.Thread(target=self._tun_read_loop, daemon=True).start()

        poller = zmq.Poller()
        poller.register(self.ue_socket, zmq.POLLIN)
        poller.register(self.bus_socket, zmq.POLLIN)

        while True:
            # 每 10 秒重发一次 GNBInfo，最多 5 次
            if (not self.gnb_info_acknowledged and time.time() - self.last_gnb_info_time > 5 and self.gnb_info_count < 5):
                if ctrl_ip:
                    self._send_to_eventbus("amf-000", "GNBInfo", {
                        "gnb_id": self.id,
                        "ctrl_ip": ctrl_ip
                    })
                    self.last_gnb_info_time = time.time()
                    self.gnb_info_count += 1

            if time.time() - self.last_hello > 5:
                self._send_to_eventbus("eb-server", "HELLO", {})
                self.last_hello = time.time()

            socks = dict(poller.poll(timeout=100))

            if self.ue_socket in socks:
                identity, msg = self.ue_socket.recv_multipart()
                try:
                    data = json.loads(msg.decode())
                    msg_type = data.get("type")
                    if msg_type == "RRCSetupRequest":
                        ue_id = data["payload"]["ue_id"]
                        self.ue_identities[ue_id] = identity
                        self.log_event("RRCSetupRequestReceived", {"ue_id": ue_id})
                        self._flush_pending(ue_id)
                        self._send_to_eventbus("amf-000", "InitialUEMessage",
                                               {"ue_id": ue_id, "gnb_id": self.id})
                    elif msg_type == "AuthenticationResponse":
                        ue_id = data["payload"]["ue_id"]
                        self.log_event("AuthenticationResponseReceived", {"ue_id": ue_id})
                        self._send_to_eventbus("amf-000", "AuthenticationResponse", data["payload"])
                    elif msg_type == "RRCReconfigurationComplete":
                        ue_id = data.get("source")
                        self.log_event("RRCReconfigurationComplete", {"ue_id": ue_id})
                        # 目标 gNB 收到完成，通知 AMF
                        if ue_id in self.handover_pending_ues:
                            self._send_to_eventbus("amf-000", "HandoverNotify", {"ue_id": ue_id})
                            self.handover_pending_ues.remove(ue_id)
                except Exception as e:
                    pass

            if self.bus_socket in socks:
                try:
                    bus_msg = self.bus_socket.recv_json()
                    msg_type = bus_msg.get("type")
                    payload = bus_msg.get("payload", {})
                    ue_id = payload.get("ue_id")

                    if msg_type == "AuthenticationRequest":
                        self._send_to_ue(ue_id, bus_msg)
                    elif msg_type == "DownlinkNASTransport":
                        self._send_to_ue(ue_id, {
                            "type": "RRCReconfiguration",
                            "payload": {"ue_id": ue_id, "ip": payload.get("ip")}
                        })
                    elif msg_type == "TunnelUpdate":
                        # 收到 RANLinkManager 的实时隧道推送
                        ue_id = payload.get("ue_id")
                        session_ip = payload.get("session_ip")
                        docker_ip = payload.get("docker_ip")
                        up_teid = payload.get("up_teid")
                        down_teid = payload.get("down_teid")
                        upf_ip = payload.get("upf_ip", DEFAULT_UPF_IP)
                        if ue_id and up_teid and down_teid:
                            if docker_ip:
                                self.docker_ip_to_ueid[docker_ip] = ue_id
                            if session_ip:
                                self.session_ip_to_ueid[session_ip] = ue_id
                            self.ue_tunnel[ue_id] = (up_teid, down_teid, upf_ip)
                            if docker_ip:
                                self.ue_gw_ip[ue_id] = docker_ip
                            self.log_event("TunnelUpdated", {
                                "ue_id": ue_id,
                                "up_teid": up_teid,
                                "upf_ip": upf_ip
                            })
                    # 新增切换消息
                    elif msg_type == "TriggerHandover":
                        # 由 mobility_simulator 发送，触发 N2 切换
                        target = payload.get("target_gnb")
                        self._handle_handover_required(ue_id, target)
                    elif msg_type == "HandoverRequest":
                        self._handle_handover_request(payload)
                    elif msg_type == "HandoverCommand":
                        self._handle_handover_command(payload)
                    elif msg_type == "HandoverNotify":
                        # 目标 gNB 收到 UE 完成，转发给 AMF（上面已做）
                        pass
                    elif msg_type == "UEContextRelease":
                        # 释放 UE 上下文（可选）
                        pass
                    elif msg_type == "GNBInfoAck":
                        self.gnb_info_acknowledged = True
                        self.log_event("GNBInfoAcknowledged", {"gnb_id": self.id})
                except Exception as e:
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--bus-host", required=True)
    args = parser.parse_args()
    GNB(args.id, args.bus_host).run()