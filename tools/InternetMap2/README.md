# InternetMap

This is a visualization tool that we developed for the Internet emulator. 

## Features supported

Currently, the tool supports the following features:

- [index](#home):
  - Home page
- [map](#map):
  - Display topology of the network
  - Search and highlight nodes on the map 
  - Animate packet flows using BPF expressions 
  - Disconnect/reconnect nodes from emulation 
  - Enable/disable BGP peers 
  - Customize node styles 
  - Expand/collapse nodes 
  - Drag-to-fix node positions
- [ixMap](#ixMap):
  - Similar to the map page in function
  - Displayed up to the IX level and will not show the Host at a deeper level
  - Filter by the number or name of IX
- [transitMap](#transitMap):
  - Similar to the map page in function
  - Displayed up to the transit level and will not show the Host at a deeper level
  - Filter by the number or name of transit
- [uploadMap](#uploadMap):
  - Similar to the map page in function
  - The data source is the uploaded docker-compose.yml file, which only displays the network topology diagram
  - Functions such as the terminal and Filter that require background nodes cannot be used
  - Set the displayed topology diagram based on the names and quantities of IX and Transit.
- [dashboard](#dashboard):
  - List nodes in the emulation 
  - Access nodes in the emulation 
  - Search nodes by ASN, node name, or IP address
- [plugin](#plugin)
  - Plugin installation page


## How to use this tool

### Start the tool during the runtime

The Internet Map runs inside an independent container. We can use the `docker-compose.yml` file inside this folder to bring up the container. 


1. Start the emulation as you normally would. (e.g., `docker-compose up`)
2. Run `docker-compose build && docker-compose up` in this folder to build and start the Internet Map container.
3. Once the container is up, access the tool using the following pages:
   1. Home page: [http://localhost:8080/](http://localhost:8080/) or [http://localhost:8080/pro/home](http://localhost:8080/pro/home) 
   2. The Map page: [http://localhost:8080/pro/map](http://localhost:8080/pro/map)
   3. Dashboard: [http://localhost:8080/pro/dashboard](http://localhost:8080/pro/dashboard)
   4. Plugin pag: [http://localhost:8080/pro/plugin](http://localhost:8080/pro/plugin)


### Start the tool during the runtime

Alternatively, the Internet Map container can be directly included in the emulator when we build the emulator. Just set `clientEnabled = True` when using `Docker` compiler (the default value is `True`, so by default, the Internet Map is already included in the emulator). 


### The security issue

Note that the Internet Map allows unauthenticated console access to all nodes, which can potentially allow root access to your emulator host. Only run this tool on trusted networks. If you only want to use the Internet Map to visualize the network, without providing the node access, you can disable the access. For details, please refer to [example/internet/B07_internet_map_unable_console](../../examples/internet/B07_internet_map_unable_console/README.md).


## Pages 

### home

Home page, the entry point. 

![home.png](docs/assets/index.png)

### map

The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging. For detailed introductions, [please refer to this document](./docs/map.md).

![map.png](docs/assets/map.png)

### ixMap

Similar to the map page in function, the difference lies in the display dimension. ixMap only shows up to the IX dimension and does not display the Host at a deeper level. For detailed introductions, [please refer to this document](./docs/ixMap.md).

![ixMap.png](docs/assets/ixMap.png)

### transitMap

Similar to the map page in function, the difference lies in the display dimension. transitMap only shows up to the transit dimension and does not display the Host at a deeper level. For detailed introductions, [please refer to this document](./docs/transitMap.md).

![transitMap.png](docs/assets/transitMap.png)

### uploadMap

Similar to the map page in function, However, the data source is the uploaded docker-compose.yml file, which only displays the network topology diagram. In fact, no corresponding nodes are running on the host machine. Therefore, functions such as the terminal and Filter that require background nodes cannot be used. For detailed introductions, [please refer to this document](./docs/uploadMap.md).

![uploadMap.png](docs/assets/uploadMap.png)

### dashboard

Displays the emulator nodes and networks.

![dashboard.png](docs/assets/dashboard.png)

### plugin

Plugin installation page: installing additional tools inside the emulator. For detailed instructions, [please refer to this document](docs/plugin.md).

![plugin.png](docs/assets/plugin.png)
