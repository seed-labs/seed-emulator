# Instructions

- Step 1: Run `vpn_connect.sh` to connect this VM to the remote emulator. 
  The `ip` is the IP address of the remote machine (where the emulator is running)
```
vpn_connect.sh <ip>
```

- Step 2: Run `client_setup.sh` to set up the client side. The information of the target sites
  is inside `target_networks_hosts`. This script does the following:
 
  - Set up the routing table: route the target traffic to the emulator; 
    this is only for the targeted sites.

  - Modify `/etc/hosts`: Fix the IP-hostname mapping in `/etc/hosts`. 
    The IP addresses for the target site might change from time to time. To solve this problem,
    we fix these addresses in `/etc/hosts`. These  mappings typically won't change
    over a short period of time, but they may change, so before doing the demo, check the 
    IP addresses in `target_networks_hosts`.


