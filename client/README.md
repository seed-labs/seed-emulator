seedsim-client
---

This is a work-in-progress prototype of the seedsim client. 

What's working:

- listing nodes in the emulation.
- attaching to nodes in the emulation.
- search nodes with their ASN, node name, or IP address.
- map:
    - show topology on the map.
    - search and highlight nodes on the map.
    - animate packet flows with BPF expression.
    - disconnect/reconnect nodes from emulation.
    - enable/disable bgp peers.

How to use:

1. start the emulation as you normally would. (e.g., `docker-compose up`)
2. do `docker-compose build && docker-compose up` in this folder.
3. visit [http://localhost:8080/](http://localhost:8080/) for list, and [http://localhost:8080/map.html](http://localhost:8080/map.html) for map.

Note on the map:

- try not to click on any nodes or start packet capture on the map until the emulation is fully started (i.e., all containers are created).