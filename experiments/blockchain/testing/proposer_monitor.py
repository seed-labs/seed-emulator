import requests
import pandas as pd
import numpy as np
import time
import os
from collections import deque
from datetime import datetime

# Configuration
NODE_IP = "10.153.0.96"
BASE_URL = f"http://{NODE_IP}:8000"
MAX_SLOTS = 32

# Buffer to store the last 32 slots of data
# Each element: {"slot": int, "proposer": str, "validators_count": int}
slot_buffer = deque(maxlen=MAX_SLOTS)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_data():
    try:
        # 1. Get current head info (Proposer and Slot)
        header_url = f"{BASE_URL}/eth/v1/beacon/headers/head"
        header_res = requests.get(header_url, timeout=5).json()
        
        header_data = header_res['data']['header']['message']
        current_slot = header_data['slot']
        proposer_index = header_data['proposer_index']

        # 2. Get committee (Validators) for this specific slot
        committee_url = f"{BASE_URL}/eth/v1/beacon/states/head/committees?slot={current_slot}"
        committee_res = requests.get(committee_url, timeout=5).json()
        
        # Extract all validator indices in the committees for this slot
        validators = []
        for comm in committee_res.get('data', []):
            validators.extend(comm.get('validators', []))
        
        # Format validators as a string or count for display
        validator_sample = f"{len(validators)} validators"
        
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
    print(f"Connecting to {NODE_IP}...")
    
    while True:
        new_data = fetch_data()
        
        if new_data:
            # Check if this slot is already in buffer to avoid duplicates
            if not any(d['SLOT'] == new_data['SLOT'] for d in slot_buffer):
                slot_buffer.append(new_data)

            # Convert buffer to DataFrame
            # Using numpy to handle the array-like structure if needed
            data_array = np.array(list(slot_buffer))
            df = pd.DataFrame(list(data_array))

            # Ensure columns are in order
            cols = ["SLOT", "PROPOSER_INDEX", "VALIDATORS_TOTAL", "VALIDATOR_LIST_PREVIEW"]
            df = df[cols].sort_values(by="SLOT", ascending=False)

            clear_terminal()
            print(f"=== Beacon Chain Slot Monitor (Rolling 32) | {datetime.now().strftime('%H:%M:%S')} ===")
            print(f"Node: {NODE_IP}")
            print("=" * 100)
            
            # Use large column spacing
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
