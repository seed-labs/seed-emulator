#!/usr/bin/env python3
"""
UE with 3GPP states, supports dynamic gNB IP and handover.
States: UNREGISTERED -> RRC_CONNECTED -> AUTHENTICATING -> REGISTERED
Timers: T3510 (15 s registration timeout), T3502 (30 s periodic registration)
"""
import zmq
import time
import argparse
import hashlib
import json
import subprocess
import re
import os
import glob
from datetime import datetime, timezone


class UE:
    T3510_DEFAULT = 15.0
    T3502_DEFAULT = 30.0

    def __init__(self, ue_id, gnb_ip="gnb"):
        self.id = ue_id
        self.gnb_ip = gnb_ip
        self.context = zmq.Context()
        self.socket = None
        self.state = "UNREGISTERED"
        self.last_request_time = 0
        self.heartbeat_interval = self.T3502_DEFAULT
        self.retry_interval = 3.0
        self.miss_count = 0
        self.session_ip = None
        self.last_switch_time = 0
        self.t3510_start = 0
        self.t3510_running = False
        self.last_ping_time = 0
        self._create_socket()

    def log_event(self, event, extra=None):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "ue_id": self.id, "event": event, "state": self.state}
        if extra:
            record.update(extra)
        print(json.dumps(record), flush=True)

    def _create_socket(self):
        if self.socket:
            self.socket.close()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.id.encode())
        self.socket.setsockopt(zmq.RCVTIMEO, 2000)
        self.socket.setsockopt(zmq.SNDTIMEO, 2000)
        self.socket.setsockopt(zmq.IMMEDIATE, 1)
        self.socket.setsockopt(zmq.LINGER, 0)
        try:
            self.socket.connect(f"tcp://{self.gnb_ip}:5556")
            return True
        except zmq.ZMQError:
            return False

    def reconnect_gnb(self, new_gnb_ip: str):
        """动态切换到新 gNB，保留所有状态"""
        if new_gnb_ip == self.gnb_ip:
            return
        print(f"[{self.id}] Reconnecting from {self.gnb_ip} to {new_gnb_ip}", flush=True)
        self.gnb_ip = new_gnb_ip
        self._create_socket()

    def _compute_res(self, rand):
        return hashlib.sha256(f"{self.id}{rand}".encode()).hexdigest()[:16]

    def _send_rrc_setup_request(self):
        if time.time() - self.last_switch_time < 2.0:
            return False
        if not self.socket:
            self._create_socket()
        msg = {"source": self.id, "type": "RRCSetupRequest", "payload": {"ue_id": self.id}}
        try:
            self.socket.send_json(msg)
            self.last_request_time = time.time()
            self.t3510_start = time.time()
            self.t3510_running = True
            if self.state == "UNREGISTERED":
                self.state = "RRC_CONNECTED"
            self.log_event("RRCSetupRequestSent")
            return True
        except zmq.ZMQError:
            self.miss_count += 1
            return False

    def _check_timers(self):
        if self.t3510_running and (time.time() - self.t3510_start > self.T3510_DEFAULT):
            self.t3510_running = False
            self.log_event("T3510Expired")
            if self.state in ("RRC_CONNECTED", "AUTHENTICATING"):
                self.state = "UNREGISTERED"

    def _do_ping(self):
        if self.state != "REGISTERED" or not self.session_ip:
            return
        if time.time() - self.last_ping_time < 2.0:
            return
        self.last_ping_time = time.time()
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", "10.150.0.5"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                match = re.search(r"time=(\d+\.?\d*) ms", result.stdout)
                latency = float(match.group(1)) if match else None
                self.log_event("PingSuccess", {"target": "10.150.0.5", "latency_ms": latency})
            else:
                self.log_event("PingFailure", {"target": "10.150.0.5"})
        except Exception as e:
            self.log_event("PingError", {"error": str(e)})

    def _check_reconnect_flag(self):
        """检查 /tmp/reconnect_to_*.flag，触发重连"""
        for flag in glob.glob("/tmp/reconnect_to_*.flag"):
            try:
                new_ip = flag.split("_")[-1].replace(".flag", "")
                if new_ip and new_ip != self.gnb_ip:
                    self.reconnect_gnb(new_ip)
                os.remove(flag)
            except Exception as e:
                print(f"[{self.id}] Error processing reconnect flag: {e}", flush=True)

    def run(self):
        print(f"[{self.id}] UE started (gnb IP: {self.gnb_ip})", flush=True)
        while True:
            self._check_reconnect_flag()
            self._check_timers()
            interval = self.heartbeat_interval if self.state == "REGISTERED" else self.retry_interval
            if time.time() - self.last_request_time > interval:
                self._send_rrc_setup_request()

            try:
                msg = self.socket.recv_json(flags=zmq.NOBLOCK)
                msg_type = msg.get("type")
                if msg_type == "AuthenticationRequest":
                    rand = msg["payload"]["rand"]
                    res = self._compute_res(rand)
                    self.socket.send_json({
                        "source": self.id,
                        "type": "AuthenticationResponse",
                        "payload": {"ue_id": self.id, "res": res}
                    })
                    self.state = "AUTHENTICATING"
                    self.log_event("AuthenticationResponseSent", {"rand": rand})
                elif msg_type == "RRCReconfiguration":
                    payload = msg.get("payload", {})
                    # 检查是否包含 target_gnb_ip（切换命令）
                    target_gnb_ip = payload.get("target_gnb_ip")
                    if target_gnb_ip:
                        # 切换：更新控制面连接
                        self.reconnect_gnb(target_gnb_ip)
                        # 重新注册流程（由 AMF 触发）—— 实际上 UE 应保持注册，但为了简化，我们重置状态？
                        # 标准切换不重新注册，我们保持 REGISTERED 状态，但需要新建立 RRC？
                        # 实际上 UE 收到 RRCReconfiguration 后应回复 RRCReconfigurationComplete
                        # 我们立即回复完成
                        self.socket.send_json({
                            "source": self.id,
                            "type": "RRCReconfigurationComplete",
                            "payload": {}
                        })
                        self.log_event("HandoverRRCReconfigurationComplete", {"target_gnb": target_gnb_ip})
                        # 不重置状态
                    else:
                        # 初始注册或会话建立
                        self.socket.send_json({
                            "source": self.id,
                            "type": "RRCReconfigurationComplete",
                            "payload": {}
                        })
                        ip = payload.get("ip")
                        self.session_ip = ip
                        old_state = self.state
                        self.state = "REGISTERED"
                        self.t3510_running = False
                        self.miss_count = 0
                        if old_state != "REGISTERED":
                            self.log_event("Registered", {"ip": ip})
                        else:
                            self.log_event("PeriodicRegistrationComplete", {"ip": ip})
            except zmq.Again:
                pass
            except zmq.ZMQError:
                self.socket = None

            self._do_ping()
            time.sleep(0.1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--gnb-ip", default="gnb", help="gNB ZMQ server IP/hostname")
    args = parser.parse_args()
    UE(args.id, args.gnb_ip).run()