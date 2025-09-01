# seedemu-client

This is a work-in-progress prototype of the seedemu client. 

What's working:

- [map](#maphtml):
    - show topology on the map.
    - search and highlight nodes on the map.
    - animate packet flows with BPF expression.
    - disconnect/reconnect nodes from emulation.
    - enable/disable bgp peers.
    - customize the style of the node.
    - expand / collapse nodes
    - drag fixed
- [index](#indexhtml):
  - listing nodes in the emulation.
  - attaching to nodes in the emulation.
  - search nodes with their ASN, node name, or IP address.
- [install](#installhtml)
  - plugin installation

How to use:
1. start the emulation as you normally would. (e.g., `docker-compose up`)
2. do `docker-compose build && docker-compose up` in this folder.
3. there are mainly the following pages
   1. visit [http://localhost:8080/](http://localhost:8080/) or [http://localhost:8080/index.html](http://localhost:8080/index.html) for list
   2. visit [http://localhost:8080/install.html](http://localhost:8080/install.html) for install plugin.
   3. visit [http://localhost:8080/map.html](http://localhost:8080/map.html) for map.

Alternatively, set `clientEnabled = True` when using `Docker` compiler. Note that `seedemu-client` allows unauthenticated console access to all nodes, which can potentially allow root access to your emulator host. Only run `seedemu-client` on trusted networks.

## map.html

The network topology diagram shows the interconnection relationship between each node and its network, and includes some auxiliary functions such as filter, search, setting, replay, Log, etc. For detailed introduction, [please click](./docs/map.md)

![map.png](docs/assets/map.png)

## index.html

`seedemu dashboard`, display the current simulator node and network

![index.png](docs/assets/index.png)

## install.html

Plugin installation page.

The plugin is implemented through the dockerAPI and is independent of the basic functions of the "client". 

It can be extended with some custom functions. 

For example, the submit_event plugin can customize the style of the host node in the map.

Just install the corresponding plugin for the required functions.

Currently, only the submit_event plugin is available. It will gradually become more diverse in the future.

For specific usage, [please click](docs/install.md)

![install.png](docs/assets/install.png)