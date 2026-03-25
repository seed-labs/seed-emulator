import requests
import pandas as pd
import time
import os
from datetime import datetime

def clear_terminal():
    # Clear terminal screen based on OS
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_validator_data(ip):
    # Standard Beacon API endpoint
    url = f"http://{ip}:8000/eth/v1/beacon/states/head/validators"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"API Request Error: {e}")
        return None

def run_monitor(target_ip):
    # Set pandas display options for wider spacing and full content
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.colheader_justify', 'left')
    
    print(f"Initializing monitor for node: {target_ip}...")
    
    while True:
        raw_validators = fetch_validator_data(target_ip)
        
        if raw_validators:
            extracted_rows = []
            
            for item in raw_validators:
                extracted_rows.append({
                    "INDEX": item['index'],
                    "BALANCE (GWEI)": item['balance'],  # Raw Gwei string, no rounding
                    "STATUS": item['status'],
                    "PUBKEY": item['validator']['pubkey'] # Full pubkey
                })
            
            # Create and sort DataFrame
            df = pd.DataFrame(extracted_rows)
            df['INDEX'] = df['INDEX'].astype(int)
            df = df.sort_values(by='INDEX')
            
            # Refresh output
            clear_terminal()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"=== Validator Monitor | Last Update: {current_time} ===")
            print(f"Node IP: {target_ip}")
            print("=" * 160)
            
            # Use to_string with justify and col_space for large gaps
            print(df.to_string(index=False, col_space=20, justify='left'))
            
            print("=" * 160)
            print("Refreshing every 12 seconds... (Press Ctrl+C to stop)")
            
        else:
            print("No data received. Retrying in 12s...")
            
        time.sleep(12)

if __name__ == "__main__":
    NODE_IP = "10.153.0.96"
    
    try:
        run_monitor(NODE_IP)
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")
