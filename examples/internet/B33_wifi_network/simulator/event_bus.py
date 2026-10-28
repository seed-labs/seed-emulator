#!/usr/bin/env python3
"""EventBus: ZMQ ROUTER-based message broker for 5G control-plane."""
import zmq
import json
import time
from datetime import datetime, timezone


class EventBus:
    """ZMQ ROUTER 消息代理，负责控制面信令路由"""

    def __init__(self):
        self.context = zmq.Context()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind("tcp://0.0.0.0:5555")
        self.peers = {}           # peer_id → ZMQ identity
        self.last_hello = {}      # 心跳时间戳

    def log(self, event, extra=None):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event}
        if extra:
            record.update(extra)
        print(json.dumps(record), flush=True)

    def log_message(self, src, tgt, msg_type, payload):
        """打印控制面消息（简化版，只显示关键字段）"""
        # 截断 payload 中的长字段（如 rand, res）
        safe_payload = {}
        for k, v in payload.items():
            if isinstance(v, str) and len(v) > 20:
                safe_payload[k] = v[:10] + "..."
            else:
                safe_payload[k] = v
        self.log("MSG", {
            "src": src,
            "target": tgt,
            "type": msg_type,
            "payload": safe_payload
        })

    def run(self):
        print("[EventBus] started on 0.0.0.0:5555", flush=True)
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)

        while True:
            socks = dict(poller.poll(timeout=100))
            if self.frontend in socks:
                # ROUTER 收到 DEALER 消息时，格式为 [identity, msg]（无空帧）
                frames = self.frontend.recv_multipart()
                if len(frames) != 2:
                    # 如果格式异常，丢弃
                    continue
                identity, msg = frames
                try:
                    data = json.loads(msg.decode())
                    src = data.get("source", "unknown")
                    msg_type = data.get("type", "unknown")
                    payload = data.get("payload", {})
                    tgt = data.get("target")

                    # 记录所有非 HELLO 消息（HELLO 会频繁产生）
                    if msg_type != "HELLO":
                        self.log_message(src, tgt, msg_type, payload)

                    # 心跳：记录对端身份
                    if msg_type == "HELLO":
                        self.peers[src] = identity
                        self.last_hello[src] = time.time()
                        continue

                    # 消息转发
                    if tgt and tgt in self.peers:
                        # 转发时同样使用两帧格式：目标 identity + 原始消息
                        self.frontend.send_multipart([self.peers[tgt], msg])
                    else:
                        self.log("DropNoTarget", {"target": tgt, "source": src})

                except Exception as e:
                    print(f"[EventBus] error: {e}", flush=True)

            # 清理 60 秒未心跳的对端
            now = time.time()
            stale = [k for k, v in self.last_hello.items() if now - v > 60]
            for k in stale:
                self.peers.pop(k, None)
                self.last_hello.pop(k, None)


if __name__ == "__main__":
    EventBus().run()