#!/bin/bash

# Add the content of ./custom_hosts to /etc/hosts,  replacing the 
# old entries between "BEGIN CUSTOM" and "END CUSTOM"

sudo sed -i '/# BEGIN CUSTOM/,/# END CUSTOM/{//!d;}' /etc/hosts && sudo sed -i '/# BEGIN CUSTOM/r ./target_hosts' /etc/hosts

# Set up bird conf's include entries
#protocol static {
#  ipv4 { table t_bgp;  };
#  route *** blackhole   {
#      bgp_large_community.add(LOCAL_COMM);
#  };
#}
