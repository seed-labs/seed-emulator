#!/bin/bash

echo "===== High-Capacity Network Parameter Configuration (for 96 cores + 256GB RAM) ====="
echo "Writing to /etc/sysctl.conf ..."

cat <<'EOF' | sudo tee -a /etc/sysctl.conf > /dev/null

### ===== Large ARP table capacity (1,000,000 entries) ===== ###
net.ipv4.neigh.default.gc_thresh1 = 262144
net.ipv4.neigh.default.gc_thresh2 = 524288
net.ipv4.neigh.default.gc_thresh3 = 1048576

### ===== Large socket buffer size (128MB) ===== ###
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 134217728
net.core.wmem_default = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.optmem_max = 131072

### ===== High-concurrency queue tuning ===== ###
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 1000000

### ===== Large conntrack table (16 million entries) ===== ###
net.netfilter.nf_conntrack_max = 16777216
net.netfilter.nf_conntrack_buckets = 4194304

### ===== IP fragment buffer expansion ===== ###
net.ipv4.ipfrag_high_thresh = 268435456
net.ipv4.ipfrag_low_thresh  = 134217728

EOF

echo "===== Applying new sysctl settings ====="
sudo sysctl -p

echo "===== Flushing ARP/Neighbor table (important) ====="
sudo ip -s -s neigh flush all

echo "===== Configuration completed ====="
echo "Your system ARP table capacity is now increased to 1,000,000 entries, optimized for high-density container networking."

