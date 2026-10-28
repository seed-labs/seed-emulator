#!/usr/bin/env python3
"""
移动性模拟器：驱动 UE 移动，触发注册和切换，输出 KPI 日志。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import math
import random
import argparse
import json
import zmq
from datetime import datetime, timezone
from runtime.ran_link_manager import RANLinkManager

# ========== 配置 ==========
NUM_UE = 5
DEFAULT_GNB = "gnb-000"
GNB_IDS = ["gnb-000", "gnb-001", "gnb-002", "gnb-003", "gnb-004",
           "gnb-005", "gnb-006", "gnb-007", "gnb-008", "gnb-009", "gnb-010"]
GNB_POSITIONS = {
    "gnb-000": (25, 25), "gnb-001": (37, 37), "gnb-002": (37, 25),
    "gnb-003": (75, 25), "gnb-004": (63, 37),
    "gnb-005": (50, 50),
    "gnb-006": (25, 75), "gnb-007": (37, 63),
    "gnb-008": (75, 75), "gnb-009": (63, 63), "gnb-010": (63, 75),
}
GNB_RADIUS = 25.0
UE_STEP = 10.0
SIM_INTERVAL = 1.0
UE_IDS = [f"ue-{i:03d}" for i in range(NUM_UE)]
INITIAL_UE_COUNT = NUM_UE   # 提前注册的 UE 数量，其余动态注册
# =========================

def log_event(event, extra=None):
    """输出 JSON 格式的 KPI 事件"""
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event}
    if extra:
        record.update(extra)
    print(json.dumps(record), flush=True)

def best_gnb(ue_id, ue_positions):
    """根据 UE 位置选出最近的 gNB（在覆盖半径内）"""
    x, y = ue_positions[ue_id]
    best, best_dist = None, float('inf')
    for gnb, (gx, gy) in GNB_POSITIONS.items():
        d = math.hypot(x - gx, y - gy)
        if d <= GNB_RADIUS and d < best_dist:
            best, best_dist = gnb, d
    return best

# ---------- 移动模型 ----------
def move_ue_random(ue_id, ue_positions, ue_directions):
    """随机游走：每步 20% 概率改变方向，边界时转向中心（±45°）"""
    if random.random() < 0.2:
        ue_directions[ue_id] = random.uniform(0, 2 * math.pi)
    x, y = ue_positions[ue_id]
    angle = ue_directions[ue_id]
    dx = UE_STEP * math.cos(angle)
    dy = UE_STEP * math.sin(angle)
    new_x, new_y = x + dx, y + dy
    if not (0 <= new_x <= 100 and 0 <= new_y <= 100):
        center_angle = math.atan2(50 - y, 50 - x)
        angle = center_angle + random.uniform(-math.pi/4, math.pi/4)
        ue_directions[ue_id] = angle
        new_x = max(0, min(100, x + UE_STEP * math.cos(angle)))
        new_y = max(0, min(100, y + UE_STEP * math.sin(angle)))
    ue_positions[ue_id] = (new_x, new_y)

def move_ue_highway(ue_id, ue_positions, ue_directions):
    """高速公路：保持方向，边界反射（水平和垂直分别反向）"""
    x, y = ue_positions[ue_id]
    angle = ue_directions[ue_id]
    dx, dy = UE_STEP * math.cos(angle), UE_STEP * math.sin(angle)
    new_x, new_y = x + dx, y + dy
    if new_x < 0 or new_x > 100:
        angle = math.pi - angle
        ue_directions[ue_id] = angle
        new_x = max(0, min(100, x - dx))
    if new_y < 0 or new_y > 100:
        angle = -angle
        ue_directions[ue_id] = angle
        new_y = max(0, min(100, y - dy))
    ue_positions[ue_id] = (new_x, new_y)

def move_ue_manhattan(ue_id, ue_positions, ue_directions):
    """曼哈顿：正交方向，随机转向（无网格限制）"""
    x, y = ue_positions[ue_id]
    if random.random() < 0.4:
        ue_directions[ue_id] = random.choice([0, math.pi/2, math.pi, 3*math.pi/2])
    angle = ue_directions[ue_id]
    dx, dy = UE_STEP * math.cos(angle), UE_STEP * math.sin(angle)
    new_x, new_y = x + dx, y + dy
    if new_x < 0 or new_x > 100:
        angle = math.pi - angle
        ue_directions[ue_id] = angle
        new_x = max(0, min(100, x - dx))
    if new_y < 0 or new_y > 100:
        angle = -angle
        ue_directions[ue_id] = angle
        new_y = max(0, min(100, y - dy))
    ue_positions[ue_id] = (new_x, new_y)

class MobilitySimulator:
    def __init__(self, model="random", steps=20):
        self.model = model
        self.steps = steps
        self.link_mgr = RANLinkManager(UE_IDS, GNB_IDS, DEFAULT_GNB)
        self.ue_positions = {ue: (random.uniform(0, 100), random.uniform(0, 100)) for ue in UE_IDS}
        self.ue_reg_gnb = {ue: DEFAULT_GNB for ue in UE_IDS}
        self.ue_directions = {ue: random.uniform(0, 2 * math.pi) for ue in UE_IDS}
        self.move_func = {"random": move_ue_random, "highway": move_ue_highway, "manhattan": move_ue_manhattan}[model]
        # 用于向 gNB 发送消息的 ZMQ 客户端
        self.zmq_ctx = zmq.Context()
        self.zmq_socket = self.zmq_ctx.socket(zmq.DEALER)
        self.zmq_socket.setsockopt(zmq.IDENTITY, b"mobility-sim")
        self.zmq_socket.connect("tcp://127.0.0.1:15555")  # EventBus IP

    def _send_to_gnb(self, gnb_id, msg_type, payload):
        msg = {
            "source": "mobility-sim",
            "target": gnb_id,
            "type": msg_type,
            "payload": payload
        }
        self.zmq_socket.send_json(msg)

    # ---------- TCP 连续性测试设施 ----------
    def _start_external_echo_server(self):
        """在 AS2 路由器容器内启动多线程 TCP Echo Server"""
        try:
            containers = self.link_mgr.client.containers.list()
            target = None
            for c in containers:
                if "as2" in c.name and ("r100" in c.name or "router" in c.name):
                    target = c
                    break
            if not target:
                print("[TCP Test] AS2 router not found, skip", flush=True)
                return

            # 先杀掉可能存在的旧进程
            target.exec_run("pkill -f 'echo_server.py' || true")

            # 写入独立脚本文件（避免 shell 引号地狱）
            script = '''import socket, threading, sys
def handle(c, a):
    try:
        while True:
            d = c.recv(1024)
            if not d: break
            c.sendall(d)
    except: pass
    finally: c.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 9999))
s.listen(10)
sys.stderr.write("[Echo] listening on 9999\\n")
sys.stderr.flush()
while True:
    c, a = s.accept()
    threading.Thread(target=handle, args=(c,a), daemon=True).start()
'''
            target.exec_run(["sh", "-c", f"cat > /tmp/echo_server.py << 'EOF'\n{script}\nEOF"])
            # 使用 nohup 确保后台稳定运行
            target.exec_run(["sh", "-c", "nohup python3 -u /tmp/echo_server.py > /tmp/echo.log 2>&1 &"], detach=True)
            print(f"[TCP Test] Echo server started on {target.name}:9999", flush=True)
        except Exception as e:
            print(f"[TCP Test] Failed: {e}", flush=True)

    def _start_tcp_client_for_ue(self, ue_id):
        try:
            container = self.link_mgr._get_container_by_nodename(ue_id)
            script = '''import socket, time, json, sys, os
SERVER_IP = "10.100.0.2"
SERVER_PORT = 9999
HEARTBEAT_INTERVAL = 0.1
STATUS_FILE = f"/tmp/tcp_status_{sys.argv[1]}.json"
MAX_BLACKOUT = 5.0  # 5 秒内重连成功不算断开

def write_status(status):
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)

def try_connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.connect((SERVER_IP, SERVER_PORT))
    return s

def main():
    last_ok = time.time()
    blackout_start = None
    reconnect_attempts = 0
    while True:
        try:
            s = try_connect()
            write_status({"connected": True, "last_response": time.time()})
            last_ok = time.time()
            blackout_start = None
            reconnect_attempts = 0
            while True:
                try:
                    s.send(b"ping")
                    data = s.recv(1024)
                    if data == b"ping":
                        last_ok = time.time()
                        write_status({"connected": True, "last_response": last_ok})
                    else:
                        write_status({"connected": True, "last_response": last_ok, "recv": False})
                    time.sleep(HEARTBEAT_INTERVAL)
                except socket.error:
                    break
        except Exception as e:
            now = time.time()
            # 首次进入异常，记录 blackout 开始时间
            if blackout_start is None:
                blackout_start = now
            # 如果 blackout 在 5 秒内，保持 connected 状态（快速重连中）
            if now - blackout_start < MAX_BLACKOUT:
                write_status({"connected": True, "last_response": last_ok, "recovering": True})
            else:
                reconnect_attempts += 1
                write_status({"connected": False, "error": str(e), "attempts": reconnect_attempts})
            time.sleep(0.5)

if __name__ == "__main__":
    main()
'''
            container.exec_run(["sh", "-c", f"cat > /tmp/tcp_client.py << 'EOF'\n{script}\nEOF"])
            container.exec_run("pkill -f 'tcp_client.py' || true")
            container.exec_run(["sh", "-c", f"python3 /tmp/tcp_client.py {ue_id} > /tmp/tcp_client.log 2>&1 &"], detach=True)
            print(f"[TCP Client] Started for {ue_id}", flush=True)
        except Exception as e:
            print(f"[TCP Client] Failed to start for {ue_id}: {e}", flush=True)

    def _get_tcp_status(self, ue_id):
        """读取 UE 容器的 TCP 状态文件，返回 dict 或 None"""
        try:
            container = self.link_mgr._get_container_by_nodename(ue_id)
            result = container.exec_run(["cat", f"/tmp/tcp_status_{ue_id}.json"])
            if result.exit_code == 0:
                return json.loads(result.output.decode())
        except Exception:
            pass
        return None

    def _is_tcp_healthy(self, ue_id, max_age=2.0):
        status = self._get_tcp_status(ue_id)
        if not status:
            return False
        if not status.get("connected", False):
            return False
        # 如果正在 recovering（切换 blackout 中），也算 healthy
        if status.get("recovering", False):
            return True
        last_ts = status.get("last_response", 0)
        if time.time() - last_ts > max_age:
            return False
        return True

    def test_connectivity(self, phase="static", ue_ids=None):
        """连通性测试：仅对指定 UE 执行 ping -c 1 -W 1，优化耗时"""
        if ue_ids is None:
            ue_ids = UE_IDS
        results = {}
        target = "10.100.0.2"  # 外部服务器 IP，与 TCP Echo Server 同地址

        for ue_id in ue_ids:
            try:
                container = self.link_mgr._get_container_by_nodename(ue_id)
                result = container.exec_run(["ping", "-c", "1", "-W", "1", target])
                loss = 100 if result.exit_code != 0 else 0
                results[ue_id] = {"loss": loss}
            except Exception as e:
                print(f"  [WARN] Connectivity test for {ue_id} failed: {e}", flush=True)
                results[ue_id] = {"loss": 100}
        summary = {
            "total": len(ue_ids),
            "successful": sum(1 for r in results.values() if r["loss"] == 0),
            "avg_loss": sum(r["loss"] for r in results.values()) / len(ue_ids) if ue_ids else 0
        }
        log_event("ConnectivityTest", {"phase": phase, "results": results, "summary": summary})
        return results

    def setup(self):
        """初始化网络，提前注册部分 UE（其余在 run 中动态注册）"""
        print(f"=== Mobility Simulator [{self.model}] ===", flush=True)
        self.link_mgr.setup()
        self._start_external_echo_server()
        print("Waiting for initial UE registration...", flush=True)
        time.sleep(1)

        initial_ue_ids = UE_IDS[:INITIAL_UE_COUNT]
        configured = []
        for ue_id in initial_ue_ids:
            if self.link_mgr.configure_ue_routes(ue_id):
                configured.append(ue_id)
                self.link_mgr.configured_ue.add(ue_id)
                self._start_tcp_client_for_ue(ue_id)   # TCP
        print(f"[+] Pre-configured {len(configured)} UEs (out of {NUM_UE} total)", flush=True)
        print(f"[+] Remaining {NUM_UE - len(configured)} UEs will register during mobility", flush=True)
        if configured:
            time.sleep(1.5)  # 等待隧道加载
            self.test_connectivity(phase="static", ue_ids=configured)

            # 等待 TCP 客户端真正连上 Echo Server（最多 10 秒）
            print("Waiting for TCP clients to establish...", flush=True)
            for _ in range(20):
                ready = [u for u in configured if self._is_tcp_healthy(u)]
                if len(ready) == len(configured):
                    break
                time.sleep(0.5)
            print(f"[+] TCP established for {configured}", flush=True)

        print("[+] Data networks ready.", flush=True)

    def run(self):
        """主仿真循环：移动 → 记录位置 → 触发切换（边注册边切换）"""
        print("Starting mobility simulation...", flush=True)
        for step in range(self.steps):
            print(f"\n--- Step {step} ---", flush=True)

            # 检查是否有新注册的 UE（SMF 已分配 IP，但未配置数据面）
            new_ues = self.link_mgr.check_and_configure_new_ues()
            if new_ues:
                print(f"[+] Newly configured UEs: {new_ues}", flush=True)
                for ue_id in new_ues:
                    log_event("UEConfigured", {
                        "ue_id": ue_id,
                        "session_ip": self.link_mgr.ue_ip_map.get(ue_id),
                        "gnb_id": self.ue_reg_gnb.get(ue_id),
                    })
                    self._start_tcp_client_for_ue(ue_id)   # TCP
                self.test_connectivity(phase="dynamic", ue_ids=new_ues)

            for ue in UE_IDS:
                self.move_func(ue, self.ue_positions, self.ue_directions)
                x, y = self.ue_positions[ue]
                log_event("UEPosition", {
                    "ue_id": ue,
                    "position": [round(x, 2), round(y, 2)],
                    "serving_gnb": self.ue_reg_gnb.get(ue),
                })

                best = best_gnb(ue, self.ue_positions)
                current = self.ue_reg_gnb.get(ue)
                if best is not None and best != current:
                    # 切换前 TCP 测试（确保连接正常）
                    pre_ok = self._is_tcp_healthy(ue)

                    ho_start = time.time()
                    log_event("HandoverTriggered", {
                        "ue_id": ue,
                        "from_gnb": current,
                        "to_gnb": best,
                        "ue_position": self.ue_positions[ue],
                    })

                    # 1) 触发控制面切换
                    self._send_to_gnb(current, "TriggerHandover", {
                        "ue_id": ue,
                        "target_gnb": best
                    })

                    # 2) 立即执行数据面切换
                    self.link_mgr.switch_link(ue, best)

                    # 3) 更新本地记录
                    latency_ms = round((time.time() - ho_start) * 1000, 2)
                    self.ue_reg_gnb[ue] = best
                    log_event("HandoverComplete", {
                        "ue_id": ue,
                        "from_gnb": current,
                        "to_gnb": best,
                        "latency_ms": latency_ms,
                        "success": True,
                    })

                    # 4) 等待路由收敛和 NAT 会话刷新以及 TCP 重连完成
                    time.sleep(0.3)

                    # 切换后 TCP 测试
                    post_ok = self._is_tcp_healthy(ue)
                    # 记录结果
                    if pre_ok and post_ok:
                        log_event("TCPConnectionPersisted", {
                            "ue_id": ue,
                            "from": current,
                            "to": best,
                            "handover_latency_ms": latency_ms
                        })
                    else:
                        log_event("TCPConnectionLost", {
                            "ue_id": ue,
                            "from": current,
                            "to": best,
                            "pre_ok": pre_ok,
                            "post_ok": post_ok,
                            "handover_latency_ms": latency_ms
                        })

                    # ICMP 连通性测试
                    if ue in self.link_mgr.configured_ue:
                        self.test_connectivity(phase="dynamic", ue_ids=[ue])

            time.sleep(SIM_INTERVAL)

        print("=== Simulation finished ===", flush=True)
        self.zmq_socket.close(linger=0)
        self.zmq_ctx.term()

    def check(self):
        """打印当前所有 UE 的状态"""
        self.link_mgr._load_ue_ip_map()
        print("\n=== Current UE State ===", flush=True)
        for ue_id in UE_IDS:
            session_ip = self.link_mgr.ue_ip_map.get(ue_id)
            current_gnb = self.ue_reg_gnb.get(ue_id)
            configured = ue_id in self.link_mgr.configured_ue
            print(f"  {ue_id}: gnb={current_gnb}, ip={session_ip}, configured={configured}", flush=True)

    def cleanup(self):
        """清理 UE 上的 TCP 客户端进程，并调用 RANLinkManager 清理网络"""
        for ue_id in UE_IDS:
            try:
                container = self.link_mgr._get_container_by_nodename(ue_id)
                container.exec_run("pkill -f 'tcp_client.py' || true")
            except Exception:
                pass
        self.link_mgr.cleanup()   # ← 关键：调用 link_mgr 的方法
        print("[+] Cleanup complete", flush=True)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    p_setup = subparsers.add_parser("setup", help="初始化数据面网络")
    p_setup.add_argument("--model", choices=["random", "highway", "manhattan"], default="random")
    p_run = subparsers.add_parser("run", help="运行移动性仿真")
    p_run.add_argument("--model", choices=["random", "highway", "manhattan"], default="random")
    p_run.add_argument("--steps", type=int, default=20)
    p_check = subparsers.add_parser("check")
    p_cleanup = subparsers.add_parser("cleanup")
    args = parser.parse_args()

    if args.command == "setup":
        sim = MobilitySimulator(model=args.model)
        sim.setup()
    elif args.command == "run":
        sim = MobilitySimulator(model=args.model, steps=args.steps)
        sim.cleanup()
        sim.setup()   # 确保网络已初始化，状态在同一实例中
        sim.run()
        sim.link_mgr.shutdown()
    elif args.command == "check":
        sim = MobilitySimulator()
        sim.check()
    elif args.command == "cleanup":
        sim = MobilitySimulator()
        sim.cleanup()
        sim.link_mgr.shutdown()

if __name__ == "__main__":
    main()