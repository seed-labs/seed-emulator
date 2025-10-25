#!/usr/bin/env python3
import requests
import json
import os
from datetime import datetime

# Configure your node URL
BASE_URL = "http://10.151.0.71:8000"
OUTPUT_DIR = f"lighthouse_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Validated endpoints with method and optional payload
ENDPOINTS = [
    {"method": "GET",  "path": "/eth/v1/node/version"},
    {"method": "GET",  "path": "/eth/v1/node/health"},
    {"method": "GET",  "path": "/eth/v1/node/peers"},
    {"method": "GET",  "path": "/eth/v1/node/syncing"},
    {"method": "GET",  "path": "/eth/v1/beacon/genesis"},
    {"method": "GET",  "path": "/eth/v1/beacon/headers"},
    {"method": "GET",  "path": "/eth/v1/beacon/headers/head"},
    {"method": "GET",  "path": "/eth/v1/beacon/states/head/root"},
    {"method": "GET",  "path": "/eth/v1/beacon/states/head/fork"},
    {"method": "GET",  "path": "/eth/v1/beacon/states/head/committees"},
    {"method": "GET",  "path": "/eth/v1/config/spec"},
    {"method": "GET",  "path": "/eth/v1/config/deposit_contract"},
    {"method": "GET",  "path": "/eth/v1/validator/duties/proposer/0"},
    {"method": "GET",  "path": "/eth/v2/debug/beacon/states/head"}  # debug v2 endpoint from spec :contentReference[oaicite:2]{index=2}
]

results = {}

def sanitize_filename(path):
    fname = path.strip("/").replace("/", "_").replace("?", "_").replace("=", "_")
    return fname or "root"

for ep in ENDPOINTS:
    method = ep["method"]
    path = ep["path"]
    url = BASE_URL.rstrip("/") + path
    filename = sanitize_filename(path)
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.txt")

    print(f"\n➡️  Testing {method} {url}")
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10, stream=False)
        elif method == "POST":
            payload = ep.get("payload", {})
            resp = requests.post(url, json=payload, timeout=10)
        else:
            raise ValueError(f"Unsupported method {method}")

        content = resp.content

        # Save raw response
        with open(output_path, "wb") as f:
            f.write(content)

        if resp.status_code == 200:
            if len(content) == 0:
                status = "⚠️  Passed (200) but empty body"
            else:
                status = "✅ Passed (200)"
        else:
            status = f"❌ Failed (HTTP {resp.status_code})"
        results[path] = status
        print(status)

    except Exception as e:
        results[path] = f"❌ Exception: {str(e)}"
        print(f"[ERROR] {str(e)}")

# Print summary
print("\n📋 Test Summary:\n" + "-" * 60)
for path, status in results.items():
    print(f"{path:50} {status}")

# Save summary
with open(os.path.join(OUTPUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\n🗂️  All outputs saved to: {OUTPUT_DIR}")
