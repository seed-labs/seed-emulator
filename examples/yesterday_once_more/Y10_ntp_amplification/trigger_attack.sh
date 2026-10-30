#!/bin/sh
set -eu

# Run this inside the attacker container. The default B00-based attacker is
# AS150 host_0, and the default victim is AS151 host_0.
python3 /opt/ntp-like/trigger_attack.py --reflect "$@"
