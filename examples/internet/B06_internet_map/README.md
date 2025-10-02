# Building an internet_map

## Building an internet_map that can communicate with the SEED Emulator network
By default, the internet_map network and the SEED Emulator network are not connected.
In this example, we show how to enable internet communication between the internet_map network and the SEED Emulator
network through docker's environment variables.

We create the internet_map container and set its asn, net, ip_address, port_forwarding, and env.
DEFAULT_ROUTE is the default route set for the map container

See the comments in the code for detailed explanation.

### Step 1) Set params to InternetMap

```python
docker.attachInternetMap(
    asn=151, net='net0', ip_address='10.151.0.90', node_name='access_node',
    port_forwarding='8080:8080/tcp', env=['DEFAULT_ROUTE=10.151.0.254']
)
```

## Building an internet_map that prohibits access to the node console

By default, the  internet_map is the CONSOLE that allows access to all nodes. 
For security reasons, the environment variable "console" is provided. When it is "false", access to the console is prohibited.

We create the internet_map container and set its port_forwarding, and env.
CONSOLE controls whether access to the console is enabled.

`CONSOLE=false`, disabled

`CONSOLE=true`, enabled

`Default`, enabled

See the comments in the code for detailed explanation.

### Step 1) Set params to InternetMap

```python
docker.attachInternetMap(
    node_name='no_access_node', port_forwarding='8081:8080/tcp', env=['CONSOLE=false']
)
```

## submit_event plugin

**Please start the emulator and map container in `examples/internet/B06_internet_map` first**

1. visit [http://localhost:8080/plugin.html](http://localhost:8080/plugin.html), click "install" on the "submit_event" line to install "submit_event".
2. enter any host container, (e.g., `docker exec -it as150h-host_1-10.150.0.72 bash`)
3. execute the submit_event.sh script in the container
   - `bash /map-plugins/submit_event.sh -a flash`, the container will flash.
   - `bash /map-plugins/submit_event.sh -a highlight`, the container will be highlighted.
   - `bash /map-plugins/submit_event.sh -a flash -s /option.json`, the container will alternately flash according to the static and dynamic styles defined in the json file.
   - `bash /map-plugins/submit_event.sh -a highlight -s /option.json`, the container will be displayed in the static style defined in the json file.
   ```json
   // option.json e.g.1
   {
      # The hightlight style
      "highlight": { ... }, 
      # The flashing style. Flashing includes two styles; it basically switches between these two styles
      "flash": {  # both fields can be null, using the default setting
             "static":  { ... },  
             "dynamic": { ... },
             "duration": N  # The duration between two flashes (in milliseconds), default 300ms (only meaningful for the continuous flashing option)
        }
    }
   ```
   
   The ... above represents the actual style specificataion, which follows the official `vis-network` document. Please see [vis-network](https://visjs.github.io/vis-network/docs/network/nodes.html) for more detailed explanation. Here we give an example.
    ```js
    {
        "borderWidth": 1,
        "color": {
            "background": "blue"
        },
        "size": 50
    }
    ```

## Morris Worm Attack Lab
For details, please refer to the [link](https://seedsecuritylabs.org/Labs_20.04/Networking/Morris_Worm/)

worm.py needs to be modified, replace `subprocess.Popen(["ping -q -i2 1.2.3.4"], shell=True)` with the following code

```python
import json
def set_option_json():
   with open("/option.json", "w") as f:
      _option_content = {
         'flash': {
            'static': {
               "borderWidth": 2,
               "color": {
                  "background": "yellow"
               },
               "size": 20
            }
         }
      }
      json.dump(_option_content, f)

set_option_json()
subprocess.Popen(["bash /map-plugins/submit_event.sh -a flash -s /option.json"], shell=True)
```
