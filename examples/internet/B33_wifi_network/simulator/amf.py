#!/usr/bin/env python3
"""AMF with 3GPP-style state machine and T3560 authentication timer, and N2 handover support."""
import zmq
import time
import argparse
import random
import string
import hashlib
import json
from datetime import datetime, timezone


class AMF:
    T3560_DEFAULT = 10.0

    def __init__(self, amf_id, bus_host, smf_id="smf-000"):
        self.id = amf_id
        self.bus_host = bus_host
        self.smf_id = smf_id
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.id.encode())
        self.socket.connect(f"tcp://{bus_host}:5555")
        self.ue_ctx = {}
        self.ue_state = {}
        self.ue_timer = {}
        self.last_hello = 0
        self.ue_session = {}
        self.handover_ctx = {}
        self.gnb_ip_cache = {}

    def log_event(self, event, extra=None):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "node_id": self.id, "event": event}
        if extra:
            record.update(extra)
        print(json.dumps(record), flush=True)

    def send(self, target, msg_type, payload):
        self.socket.send_json({
            "source": self.id,
            "target": target,
            "type": msg_type,
            "payload": payload
        })

    def _generate_rand(self):
        return ''.join(random.choices(string.hexdigits.lower(), k=32))

    def _compute_xres(self, ue_id, rand):
        return hashlib.sha256(f"{ue_id}{rand}".encode()).hexdigest()[:16]

    def _check_timers(self):
        now = time.time()
        expired = []
        for ue_id, start in self.ue_timer.items():
            if self.ue_state.get(ue_id) == "auth_sent" and now - start > self.T3560_DEFAULT:
                expired.append(ue_id)
        for ue_id in expired:
            self.ue_state[ue_id] = "idle"
            self.ue_timer.pop(ue_id, None)
            self.log_event("T3560Expired", {"ue_id": ue_id})
            ctx = self.ue_ctx.get(ue_id)
            if ctx and ctx.get("gnb_id"):
                self.send(ctx["gnb_id"], "AuthenticationReject", {"ue_id": ue_id})

    def _get_gnb_ctrl_ip(self, gnb_id):
        """获取 gNB 控制面 IP（net0 IP）。"""
        # 优先从动态缓存获取
        if gnb_id in self.gnb_ip_cache:
            return self.gnb_ip_cache[gnb_id]
        # 后备静态映射（与 seed-emulator 拓扑一致）
        gnb_ip_map = {
            "gnb-000": "10.151.0.2",
            "gnb-001": "10.151.0.3",
            "gnb-002": "10.151.0.4",
            "gnb-003": "10.152.0.2",
            "gnb-004": "10.152.0.3",
            "gnb-005": "10.153.0.2",
            "gnb-006": "10.154.0.2",
            "gnb-007": "10.154.0.3",
            "gnb-008": "10.155.0.2",
            "gnb-009": "10.155.0.3",
            "gnb-010": "10.155.0.4",
        }
        return gnb_ip_map.get(gnb_id, "")

    def _get_gnb_data_ip(self, gnb_id):
        """获取 gNB 数据面 IP（数据网络接口 IP）。同样使用预定义映射"""
        # 数据面 IP 是动态分配的，但我们可以从隧道配置中获取，这里仅作示例
        # 在切换过程中，目标 gNB 的数据面 IP 由 ran_link_manager 配置，AMF 无法直接知道。
        # 我们让 SMF 在更新 UPF 时自行获取，或由 AMF 从目标 gNB 的 HandoverRequestAck 中获得。
        # 因此这里不实现，实际上我们会在 HandoverRequestAck 中携带数据面 IP。
        return None

    def run(self):
        print(f"[{self.id}] AMF started", flush=True)
        self.send("eb-server", "HELLO", {})

        while True:
            if time.time() - self.last_hello > 10:
                self.send("eb-server", "HELLO", {})
                self.last_hello = time.time()

            self._check_timers()

            try:
                msg = self.socket.recv_json(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.1)
                continue

            msg_type = msg.get("type")
            payload = msg.get("payload", {})
            ue_id = payload.get("ue_id")
            src = msg.get("source")

            if msg_type == "InitialUEMessage":
                gnb_id = payload.get("gnb_id")
                state = self.ue_state.get(ue_id, "idle")
                if state in ("registered", "auth_sent"):
                    continue
                rand = self._generate_rand()
                xres = self._compute_xres(ue_id, rand)
                self.ue_ctx[ue_id] = {"gnb_id": gnb_id, "rand": rand, "xres": xres}
                self.ue_state[ue_id] = "auth_sent"
                self.ue_timer[ue_id] = time.time()
                self.log_event("InitialUEMessageReceived", {"ue_id": ue_id, "gnb_id": gnb_id})
                self.send(gnb_id, "AuthenticationRequest", {"ue_id": ue_id, "rand": rand, "autn": xres})

            elif msg_type == "AuthenticationResponse":
                res = payload.get("res")
                ctx = self.ue_ctx.get(ue_id)
                state = self.ue_state.get(ue_id)
                if state != "auth_sent":
                    self.log_event("AuthenticationResponseUnexpected", {"ue_id": ue_id, "state": state})
                    continue
                if ctx and res == ctx["xres"]:
                    self.ue_state[ue_id] = "registered"
                    self.ue_timer.pop(ue_id, None)
                    self.log_event("AuthenticationSuccess", {"ue_id": ue_id})
                    self.send(self.smf_id, "PDUSessionEstablishmentRequest", {
                        "ue_id": ue_id,
                        "gnb_id": ctx["gnb_id"]
                    })
                else:
                    self.log_event("AuthenticationFailure", {"ue_id": ue_id})
                    self.ue_state[ue_id] = "idle"
                    self.ue_timer.pop(ue_id, None)
                    if ctx and ctx.get("gnb_id"):
                        self.send(ctx["gnb_id"], "AuthenticationReject", {"ue_id": ue_id})

            elif msg_type == "PDUSessionEstablishmentAccept":
                # SMF 发送的 PDU 会话接受，包含 ip, up_teid, down_teid
                ip = payload.get("ip")
                up_teid = payload.get("up_teid")
                down_teid = payload.get("down_teid")
                ctx = self.ue_ctx.get(ue_id)
                if ctx and ctx.get("gnb_id"):
                    # 保存会话信息
                    self.ue_session[ue_id] = {"ip": ip, "up_teid": up_teid, "down_teid": down_teid}
                    # 转发给 gNB（包含 TEID，gNB 会将其写入隧道配置）
                    self.send(ctx["gnb_id"], "DownlinkNASTransport", {
                        "ue_id": ue_id,
                        "ip": ip,
                        "up_teid": up_teid,
                        "down_teid": down_teid
                    })
                    self.log_event("DownlinkNASTransportSent", {"ue_id": ue_id, "ip": ip, "gnb_id": ctx["gnb_id"]})

            elif msg_type == "PDUSessionEstablishmentReject":
                reason = payload.get("reason", "unknown")
                self.log_event("PDUSessionEstablishmentReject", {"ue_id": ue_id, "reason": reason})

            # ---------- N2 切换流程 ----------
            elif msg_type == "HandoverRequired":
                target_gnb = payload.get("target_gnb")
                source_gnb = src
                if self.ue_state.get(ue_id) != "registered":
                    self.log_event("HandoverRejected", {"ue_id": ue_id, "reason": "UE not registered"})
                    continue
                sess = self.ue_session.get(ue_id)
                if not sess:
                    self.log_event("HandoverRejected", {"ue_id": ue_id, "reason": "No session info"})
                    continue
                # 保存切换上下文
                self.handover_ctx[ue_id] = {
                    "state": "waiting_ack",
                    "source": source_gnb,
                    "target": target_gnb,
                    "session_ip": sess["ip"],
                    "up_teid": sess["up_teid"],
                    "down_teid": sess["down_teid"]
                }
                self.log_event("HandoverRequiredReceived", {"ue_id": ue_id, "source": source_gnb, "target": target_gnb})
                # 向目标 gNB 发送 HandoverRequest
                self.send(target_gnb, "HandoverRequest", {
                    "ue_id": ue_id,
                    "session_ip": sess["ip"],
                    "up_teid": sess["up_teid"],
                    "down_teid": sess["down_teid"]
                })

            elif msg_type == "HandoverRequestAck":
                ue_id = payload.get("ue_id")
                ctx = self.handover_ctx.get(ue_id)
                if not ctx or ctx["state"] != "waiting_ack":
                    self.log_event("HandoverRequestAckUnexpected", {"ue_id": ue_id})
                    continue
                # 获取目标 gNB 控制面 IP，用于 RRC 重配置
                target_ctrl_ip = self._get_gnb_ctrl_ip(ctx["target"])
                if not target_ctrl_ip:
                    self.log_event("HandoverFailed", {"ue_id": ue_id, "reason": "Target gNB IP unknown"})
                    continue
                ctx["state"] = "waiting_notify"
                # 发送 HandoverCommand 给源 gNB
                self.send(ctx["source"], "HandoverCommand", {
                    "ue_id": ue_id,
                    "target_gnb_ip": target_ctrl_ip,
                    "target_gnb_id": ctx["target"],
                    "up_teid": ctx["up_teid"],
                    "down_teid": ctx["down_teid"]
                })
                self.log_event("HandoverCommandSent", {"ue_id": ue_id, "source": ctx["source"], "target": ctx["target"]})

            elif msg_type == "HandoverNotify":
                ue_id = payload.get("ue_id")
                ctx = self.handover_ctx.get(ue_id)
                if not ctx or ctx["state"] != "waiting_notify":
                    self.log_event("HandoverNotifyUnexpected", {"ue_id": ue_id})
                    continue
                # 触发 SMF 路径切换
                self.send("smf-000", "PathSwitchRequest", {
                    "ue_id": ue_id,
                    "target_gnb_id": ctx["target"],
                    "up_teid": ctx["up_teid"],
                    "down_teid": ctx["down_teid"]
                })
                # 发送 UEContextRelease 给源 gNB（可选）
                self.send(ctx["source"], "UEContextRelease", {"ue_id": ue_id})
                # 更新 UE 的当前 gNB（可选）
                if self.ue_ctx.get(ue_id):
                    self.ue_ctx[ue_id]["gnb_id"] = ctx["target"]
                self.log_event("HandoverCompleted", {"ue_id": ue_id, "target": ctx["target"]})
                del self.handover_ctx[ue_id]

            elif msg_type == "PathSwitchAck":
                # SMF 确认路径切换完成
                self.log_event("PathSwitchAckReceived", {"ue_id": ue_id})
                # 可发送 HandoverSuccess 通知外部

            elif msg_type == "GNBInfo":
                gnb_id = payload.get("gnb_id")
                ctrl_ip = payload.get("ctrl_ip")
                if gnb_id and ctrl_ip:
                    self.gnb_ip_cache[gnb_id] = ctrl_ip
                    self.log_event("GNBInfoReceived", {"gnb_id": gnb_id, "ctrl_ip": ctrl_ip})
                    self.send(gnb_id, "GNBInfoAck", {"gnb_id": gnb_id})

            # 其他消息
            elif msg_type == "HELLO":
                # 忽略心跳
                pass
            else:
                self.log_event("UnknownMessage", {"type": msg_type, "source": src})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--bus-host", required=True)
    parser.add_argument("--smf-id", default="smf-000")
    args = parser.parse_args()
    AMF(args.id, args.bus_host, args.smf_id).run()