#!/usr/bin/env python3
import time
import argparse
from datetime import datetime
from web3 import Web3
import os

def log_message(message: str, log_file: str):
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def main():
    parser = argparse.ArgumentParser(description="Monitor Ethereum block interval time")
    parser.add_argument("--node", required=True, help="Ethereum node HTTP URL, e.g. http://127.0.0.1:8545")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5s)")
    parser.add_argument("--threshold", type=int, default=20, help="Warn if block interval > threshold (default: 20s)")
    args = parser.parse_args()


    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"block_interval_{timestamp}.log"

    w3 = Web3(Web3.HTTPProvider(args.node))

    if callable(getattr(w3, "is_connected", None)):
        connected = w3.is_connected()
    else:
        connected = w3.isConnected()

    if not connected:
        raise ConnectionError(f"? Cannot connect to node: {args.node}")

    print(f"? Connected to node: {args.node}")
    print(f"? Logging to: {log_file}")
    print("? Waiting for new blocks...")

    last_block = w3.eth.block_number
    last_time = time.time()

    while True:
        current_block = w3.eth.block_number
        if current_block > last_block:
            now = time.time()
            diff = now - last_time
            normal=(f"?? New block detected: {current_block} | Interval: {diff:.2f}s")
            print(normal)
            log_message(normal,log_file)
            if diff > args.threshold:
                warning = f"?? WARNING, Block interval too long ({diff:.2f}s) at block {current_block}"
                print(warning)
                log_message(warning, log_file)

            last_block = current_block
            last_time = now

        time.sleep(args.interval)

if __name__ == "__main__":
    main()
