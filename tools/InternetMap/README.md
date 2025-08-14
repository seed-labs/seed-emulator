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
5. after installing submit_event, option.json and submit_event.sh will be generated under the "/" path of each emulator container. Please modify the corresponding style in Option.json according to the description of option in the example. Execute "bash submit_event.sh" to display the custom style (the style is only valid for the current page, and the original default style will be restored after the page is refreshed).
6. bash /submit_event.sh, parameters are optional,  flash / highlight, or none
  - flash, the container where it is located is flashing
  - highlight, highlight the container where it is located
  - without parameters, execute the custom style settings in option.json

```python
# option.json
# static styles and dynamic styles alternate to create a flickering effect
{
  # The hash long ID of the current simulator container
  "id": "f777419811d191a317fedfbeacc0645b80de2f2c22f8e3a0ca6715acf7589cd6",
  # the style displayed when the topology diagram does not flicker
  "static": {}, 
  # the style displayed when the topology diagram flickers
  "dynamic": {},
  "interval": 300 # the period for switching between static and dynamic styles, it is recommended not to modify
}
```

```js
// static field description example  (same as dynamic)
// Please see https://visjs.github.io/vis-network/docs/network/nodes.html# more detailed explanation
{
    "borderWidth": 1,
    "color": {
        "background": "blue"
    },
    "size": 50
}
```

Alternatively, set `clientEnabled = True` when using `Docker` compiler. Note that `seedemu-client` allows unauthenticated console access to all nodes, which can potentially allow root access to your emulator host. Only run `seedemu-client` on trusted networks.

Note on the map:

- try not to click on any nodes or start packet capture on the map until the emulation is fully started (i.e., all containers are created).