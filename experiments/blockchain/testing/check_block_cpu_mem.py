#!/usr/bin/env python3
import sys
import time
import datetime
from web3 import Web3
import psutil
import urllib.parse

# -------------------------
# Check args
# -------------------------
if len(sys.argv) < 2:
    print("Usage: python3 check_block_cpu_mem.py <rpc_url>")
    print("Example: python3 check_block_cpu_mem.py http://ip:8545")
    sys.exit(1)

rpc_url = sys.argv[1]

# -------------------------
# Log file initialization
# -------------------------
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"system_info-{safe_rpc}-{timestamp}.log"

with open(filename, "a") as f:
    f.write("time, block_number, mem_usage(GB), cpu_usage(%)\n")

print(f"[INFO] Logging to {filename}")
print(f"[INFO] RPC URL: {rpc_url}")

# -------------------------
# Connect Web3
# -------------------------
web3 = Web3(Web3.HTTPProvider(rpc_url))
if not web3.isConnected():
    print(f"[ERROR] Cannot connect to RPC URL: {rpc_url}")
    sys.exit(1)

print("[INFO] Successfully connected to Geth RPC")

# -------------------------
# Functions
# -------------------------
def get_cpu_usage():
    return psutil.cpu_percent(interval=10)

def get_memory_usage_gb():
    mem = psutil.virtual_memory()
    return round(mem.used / (1024 ** 3), 2)

# -------------------------
# Main loop
# -------------------------
while True:
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Get block number
    try:
        block_num = web3.eth.block_number
    except Exception as e:
        block_num = f"ERR:{e}"

    # CPU + Mem
    mem_usage = get_memory_usage_gb()
    cpu_usage = get_cpu_usage()

    # Console print
    print(f"{now}: Block={block_num} | Mem={mem_usage}GB | CPU={cpu_usage}%")

    # Write log
    with open(filename, "a") as f:
        f.write(f"{now}, {block_num}, {mem_usage}, {cpu_usage}\n")

