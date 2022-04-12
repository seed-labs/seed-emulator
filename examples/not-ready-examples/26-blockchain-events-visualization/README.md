# Visualization

## Concept
- The visualization is built on a plugin-type architecture.
- We can now create a new plugin for different projects that fetch data from the emulator and passes it to the frontend

## Client architecture
- The client is divided into two project, the frontend, and the backend
- Both projects use typescript as a base language
- Both projects are technically node projects where we can install external npm packages
- The frontend is clucless about the processing that happens on the backend.
- The data received on the frontend is in no way an indicator of which plugin is running

## Frontend
- The three main npm packages for visualization are the `vis-data`, `vis-network`, and `vis-util`
- We can generate the emulator's graph using these libraries

## Backend
- The backend is built as a node express server
- You can send POST and GET requests to the server depending on what routes are created
- You can also create a websocket connection from the frontend to one of the websocket routes

## Plugin architecture

## Frontend

- Most of the work was added to the `frontend/src/map/ui.ts` file
- The bulk of the work happens when the user clicks on the `Blockchain` tab above the search bar
- For all plugins, we will make use of two APIs provided on the backend server to be able to fetch data
- To create a new plugin, call `await this._datasource.initPlugin(type)`
- This function sends a POST request to `/api/v1/plugin/:type/init` on the server side
- The type must match one of the types in `backend/src/plugin/PluginEnum.ts`
- Once this is called on the frontend, a new plugin of type `type` is created on the server side
- After that, we need create a WebSocket connection with the server
- The socket is created in this way: `const url = 'ws://localhost:8080/api/v1/plugin/${type}/command/'; const ws = new WebSocket(url);`
- This connection is the one which we will make use of to pass data to/from frontend/backend
- To get messages from the backend, we add an `onmessage` listener by writing `ws.onmessage = (event) => {...}`
- To send data to the backend, we use the function `ws.send(JSON.stringify(...))`
- One example of data sent from the frontend to the backend is `
{
	command: "start newBlockHeaders xyz"
}`

## Backend

- There are two parts to cover on the backend: the routes, and the plugin architecture

### Routes
- The routes are added in `/backend/src/api/v1/main.ts`
- We created two new express routes which will be used by all future plugins
- The first one is reached by doing a POST request to `/api/v1/plugin/:type/init`. This is the route that creates a new plugin on the backend side. This plugin is the one that will fetch data from the emulator's docker containers
- To receive data from the plugin instance itself, we add a `instantiated_plugins[type].onMessage(function(data) {...})`
- The second express route is reached by creating a new socket connection to `ap1/v1//plugin/:type/command/`. In this route, we set a `message` listener to get data from the frontend by writing `running_ws[type].on('message', (message) => {...})`
- The data received by the frontend should be an object that has the `command` property. This `command` property is a string of the from `<action> <filter> <params>` where the `<action>` takes the values of `start` or `stop`, the `<filter>` takes the values of the events you want listen to from the emulator (plugin specific), and the `params` field is optional
- Now that the socket connection received the full command from the frontend, we can run our plugin code depending on the `<action>` provided
- To send data to the frontend, we use the `running_ws[type].send(JSON.stringify(...))`


### Plugin architecture
- On the backend side, when the POST request is sent to `/api/v1/plugin/:type/init`, we create a new plugin of type `BasePlugin`
- When we create a new `BasePlugin`, we need to specify the `type` of the plugin as parameter. For blockchain, the type is equal to `1`
- The type must match one of the types in `backend/src/plugin/PluginEnum.ts` as these are the currently supported plugins
- Under the hood, this class creates a new `EventEmitter` which we can use to listen to new messages
- The `onMessage` function that we mentioned above makes use of the `EventEmitter` to get data from the plugin itself
- To create a new plugin, your class has to implement the `PluginInterface` to add the proper functions. You also need to add your class inside `BasePlugin.ts`
- You plugin is the one that will fetch data from the emulator and pass it to the `onMessage` inside the websocket route

### Blockchain plugin
- The `BlockchainPlugin.ts` implements `PluginInterface.ts`
- This plugin is the one that connects to the Ethereum nodes using Web3 and fetches the data from the emulator
- When the user sends `start newBlockHeaders xyz`, we use Web3 to attach event listeners inside the Ethereum nodes.
- To connect to the Ethereum nodes using web3, we use `const web3 = new Web3(new Web3.providers.WebsocketProvider(`ws://${ip}:8546`, {
        clientConfig: {
                // Useful to keep a connection alive
                keepalive: true,
                keepaliveInterval: 60000 // ms
        },
      }));`
- Our ethereum nodes expose port 8546 for external websocket connections. We do this using the `geth` ethereum client.
- The data received by web3 includes new blocks that are mined, and new trddansactions that are performed.
- To listen to `newBlockHeaders`, we use: `const subscription = web3.eth.subscribe("newBlockHeaders", (error, result) => {...})`
- The Ethereum nodes will now start sending to our Plugin instance data which we will relay using the `onMessage` and then using `running_ws[type].send(JSON.stringify(...))` to send the data to the frontend
- When the user sends `stop newBlockHeaders`, we use ` subscription.unsubscribe((error, success) => {...})`
- The Ethereum nodes will now stop sending us data.


### Data

- The data sent to the frontend is in no way representative of what plugin is running on the backend.
- The data is only relevant to the visualization itself.
- The data is structured in the following way: ` {
      eventType: event_type.data,
      timestamp: Date.now(),
      status: data.status, // success or error
      containerId: data.containerId, // node to highlight
      data: data.data, // configs for vis-network library to highligh nodes
    };`
- `data.data` looks like: ` {
                                borderWidth: 4,
                                color: {
                                        background: "purple",
                                        border: "purple"
                                }
                        }`

### docker-compose.yml

- Since the client is built and brought up separately from the emulator, we need to do 2 configurations for it to be connected to the network
- The first configuration requires you to modify the `docker-compose.yml` inside the client folder
- We need to add the `networks` keyword, both inside the service and at the top level. Below is an example of how to do that.
- After running the emulator, you need to find any network to which an ethereum node is connected
- To do so, first use the `docker ps | grep Ethereum` command to find the Ethereum containers
- After that, locate any ip address such as `10.151.0.77`. 151 represents the ASN, and 0 represents the network
- In the docker-compose.yml below, you will replace `net_3_net3` by `net_151_net0`. In addition to that, we use the word `emulator` when setting up the networks (`emulator_net_3_net3`), this represents the folder in which you built your emulator.
- You can now `dcbuild` and `dcup` the client folder.
- Once this is done we will need to change the default routing of the container.
- Start by getting shell access to the client container using the `docksh` alias, 
- To see the current ip table, type `ip route show`. You will see an entry for a `default` route
- Delete this default route using `ip route del default` then add a new default route using `ip route add default via <ip>` where <ip> is the ip of the BGP router in the map. Any packet that doesn't match other routing rules will be routed by default to this new ip that you provide.
- Go to the map, select the search tab, and look for your ASN, in this case `151`. In our convention, all of the nodes in the same network are of the same color. Find the BGP router of the same color, click on it, and copy its ip address from the side panel on the map. This will be the <ip> mentioned above.

`
version: "3"

services:
    seedemu-client:
        build: .
        container_name: seedemu_client
        volumes:
            - /var/run/docker.sock:/var/run/docker.sock
        ports:
            - 8080:8080
        cap_add:
            - ALL
        sysctls:
            - net.ipv4.ip_forward=1
            - net.ipv4.conf.default.rp_filter=0
            - net.ipv4.conf.all.rp_filter=0
        privileged: true
        networks:
            emulator_net_3_net3:
                ipv4_address: 10.3.3.99
networks:
    emulator_net_3_net3:
        external: true

`
