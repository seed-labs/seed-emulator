#!/bin/bash

python ./topology_generator.py \
  --ixes 100,101,102,103,104 \
  --stub-asns 150,151,152,153,154 \
  --ebgp-routers 5 \
  --asn 3 \
  --internal-routers 20 \
  --hosts-per-stub 2 \
  --graph-model connected_watts_strogatz \
  --internal-routing rr
