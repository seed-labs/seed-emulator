import requests
import pandas as pd
import numpy as np
import time
import os
from collections import deque
from datetime import datetime
import argparse

# Argument parsing
parser = argparse.ArgumentParser(description="Beacon Chain Slot Monitor")
parser.add_argument("--ip", type=str, default="127.0.0.1",
                    help="Beacon node IP address (default: 127.0.0.1)")
parser.add_argument("--port", type=int, default=8000,
                    help="Beacon node port (default: 8000)")

args = parser.parse_args()

NODE_IP = args.ip
PORT = args.port
BASE_URL = f"http://{NODE_IP}:{PORT}"

MAX_SLOTS = 32

# Buffer to store the last 32 slots of data
slot_buffer = deque(maxlen=MAX_SLOTS)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_data():
    try:
        header_url = f"{BASE_URL}/eth/v1/beacon/headers/head"
        header_res = requests.get(header_url, timeout=5).json()
        
        header_data = header_res['data']['header']['message']
        current_slot = header_data['slot']
        proposer_index = header_data['proposer_index']

        committee_url = f"{BASE_URL}/eth/v1/beacon/states/head/committees?slot={current_slot}"
        committee_res = requests.get(committee_url, timeout=5).json()
        
        validators = []
        for comm in committee_res.get('data', []):
            validators.extend(comm.get('validators', []))
        
        return {
            "SLOT": int(current_slot),
            "PROPOSER_INDEX": proposer_index,
            "VALIDATORS_TOTAL": len(validators),
            "VALIDATOR_LIST_PREVIEW": str(validators[:5]) + "..." if len(validators) > 5 else str(validators)
        }

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def main():
    print(f"Connecting to {NODE_IP}:{PORT}...")
    
    while True:
        new_data = fetch_data()
        
        if new_data:
            if not any(d['SLOT'] == new_data['SLOT'] for d in slot_buffer):
                slot_buffer.append(new_data)

            df = pd.DataFrame(list(slot_buffer))

            cols = ["SLOT", "PROPOSER_INDEX", "VALIDATORS_TOTAL", "VALIDATOR_LIST_PREVIEW"]
            df = df[cols].sort_values(by="SLOT", ascending=False)

            clear_terminal()
            print(f"=== Beacon Chain Slot Monitor (Rolling 32) | {datetime.now().strftime('%H:%M:%S')} ===")
            print(f"Node: {NODE_IP}:{PORT}")
            print("=" * 100)
            
            pd.set_option('display.width', 1000)
            print(df.to_string(index=False, col_space=15, justify='left'))
            
            print("=" * 100)
            print(f"Buffer Size: {len(slot_buffer)}/32 | Refresh: 12s")
        
        time.sleep(12)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
