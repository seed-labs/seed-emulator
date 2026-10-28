#!/usr/bin/env python3
"""SMF with PDU session management + TEID allocation + path switch."""
import zmq
import time
import argparse
import json
import random
from datetime import datetime, timezone


class SMF:
    def __init__(self, smf_id, bus_host):
        self.id = smf_id
        self.bus_host = bus_host
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.id.encode())
        self.socket.connect(f"tcp://{bus_host}:5555")
        self.ip_pool = [f"10.60.0.{i}" for i in range(2, 254)]
        self.allocated_ips = {}
        self.ue_teid = {}
        self.last_hello = 0

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

    def _save_ip_map(self):
        try:
            with open("/app/simulator/ue_ip_map.json", "w") as f:
                json.dump(self.allocated_ips, f)
        except Exception as e:
            print(f"[{self.id}] save ip map failed: {e}", flush=True)

    def allocate_ip(self, ue_id, gnb_id):
        if ue_id in self.allocated_ips:
            return self.allocated_ips[ue_id]
        if not self.ip_pool:
            return None
        ip = self.ip_pool.pop(0)
        self.allocated_ips[ue_id] = ip
        self._save_ip_map()
        up_teid = random.randint(1, 0xFFFFFFFF)
        down_teid = random.randint(1, 0xFFFFFFFF)
        self.ue_teid[ue_id] = (up_teid, down_teid)
        return ip

    def run(self):
        print(f"[{self.id}] SMF started", flush=True)
        self.send("eb-server", "HELLO", {})

        while True:
            if time.time() - self.last_hello > 10:
                self.send("eb-server", "HELLO", {})
                self.last_hello = time.time()

            try:
                msg = self.socket.recv_json(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.1)
                continue

            msg_type = msg.get("type")
            payload = msg.get("payload", {})
            ue_id = payload.get("ue_id")
            src = msg.get("source")

            if msg_type == "PDUSessionEstablishmentRequest":
                gnb_id = payload.get("gnb_id", "unknown")
                ip = self.allocate_ip(ue_id, gnb_id)
                if ip:
                    up_teid, down_teid = self.ue_teid[ue_id]
                    # 通知 AMF（转发给 gNB）
                    self.send(src, "PDUSessionEstablishmentAccept", {
                        "ue_id": ue_id,
                        "ip": ip,
                        "up_teid": up_teid,
                        "down_teid": down_teid
                    })
                    # 通知 UPF
                    self.send("upf-000", "GTPTunnelCreate", {
                        "ue_id": ue_id,
                        "ip": ip,
                        "gnb_id": gnb_id,
                        "up_teid": up_teid,
                        "down_teid": down_teid
                    })
                    # 通知 gNB
                    self.send(gnb_id, "GTPTunnelCreate", {
                        "ue_id": ue_id,
                        "ip": ip,
                        "up_teid": up_teid,
                        "down_teid": down_teid,
                        "upf_ip": "172.19.0.3"   # 数据面网络中 UPF 的 IP
                    })
                    self.log_event("PDUSessionEstablished", {
                        "ue_id": ue_id,
                        "ip": ip,
                        "gnb_id": gnb_id,
                        "up_teid": up_teid,
                        "down_teid": down_teid
                    })
                else:
                    self.send(src, "PDUSessionEstablishmentReject",
                              {"ue_id": ue_id, "reason": "IP pool exhausted"})

            elif msg_type == "PathSwitchRequest":
                target_gnb_id = payload.get("target_gnb_id")
                up_teid = payload.get("up_teid")
                down_teid = payload.get("down_teid")
                gnb_ip = payload.get("gnb_ip")  # 由 AMF 提供目标 gNB 数据面 IP
                if not gnb_ip:
                    self.log_event("PathSwitchError", {"ue_id": ue_id, "reason": "Missing gnb_ip"})
                    continue
                self.send("upf-000", "GTPTunnelUpdate", {
                    "ue_id": ue_id,
                    "up_teid": up_teid,
                    "down_teid": down_teid,
                    "gnb_ip": gnb_ip
                })
                # 回复 AMF 确认
                self.send(src, "PathSwitchAck", {"ue_id": ue_id})
                self.log_event("PathSwitchRequestReceived", {"ue_id": ue_id, "target_gnb": target_gnb_id})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--bus-host", required=True)
    args = parser.parse_args()
    SMF(args.id, args.bus_host).run()