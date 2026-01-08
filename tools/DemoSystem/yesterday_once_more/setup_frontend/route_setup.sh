#!/bin/bash

sudo ip route add 10.0.0.0/8 via 10.174.0.254
sudo ip route add 223.109.0.0/16 via 10.174.0.254

