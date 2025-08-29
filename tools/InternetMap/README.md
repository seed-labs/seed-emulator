seedemu-client
---

This is a work-in-progress prototype of the seedemu client. 

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
    - customize the style of the node.
    - expand / collapse nodes
    - drag fixed


1. start the emulation as you normally would. (e.g., `docker-compose up`)
2. do `docker-compose build && docker-compose up` in this folder.
3. visit [http://localhost:8080/](http://localhost:8080/) for list, and [http://localhost:8080/map.html](http://localhost:8080/map.html) for map.
4. [http://localhost:8080/install.html](http://localhost:8080/install.html) for install, click "install" on the "submit_event" line to install submit_event.
5. after installing submit_event, submit_event.sh will be generated under the "/" path of each emulator container. Execute "bash submit_event.sh" to display the custom style (the style is only valid for the current page, and the original default style will be restored after the page is refreshed).
6. bash /submit_event.sh, parameters are optional. For details, please refer to the `UserManual.md`

Alternatively, set `clientEnabled = True` when using `Docker` compiler. Note that `seedemu-client` allows unauthenticated console access to all nodes, which can potentially allow root access to your emulator host. Only run `seedemu-client` on trusted networks.

Note on the map:

- try not to click on any nodes or start packet capture on the map until the emulation is fully started (i.e., all containers are created).