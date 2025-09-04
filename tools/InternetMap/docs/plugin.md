## plugin.html

Plugin installation page.

Plugins are implemented through the Docker API and operate independently of the core "client" functionality. They enable extended custom functionality.

For example, the submit_event plugin allows customization of host node styles on the map.

Simply install the corresponding plugin for your required functionality.

Currently, only the submit_event plugin is available. More plugins will be added in the future.

For specific usage instructions, [please refer to this document](docs/plugin.md)

![plugin.png](assets/plugin.png)

### submit_event plugin

Support customizing the display style of nodes in the map and execute it on the emulator container.

Click `install` to install the corresponding plugin for each emulator container.

The `submit_event.sh` script will be generated in the root directory of the emulator container

- submit_event.sh
  - params
    - `-a, --action`, flash|highlight, default: null
      - flash, the container where it is located is flashing
      - flashOnce, the difference from flash is that flash flashes all the time, while Flash Once flashes only once
      - highlight, highlight the container where it is located
      - without parameters, a custom style in the file will be set. This file needs to be created by yourself in json format. The file path must be specified with `-f, --file`
    - `-f, --file`, option json file path, default: /option.json
      - custom style configuration file
  - usage
    - Execute on the emulator container, `bash /submit_event.sh -a flash --file /option.json`
  
- Custom style configuration file
    ```python
    # static styles and dynamic styles alternate to create a flickering effect
    {
      # the style displayed when the topology diagram does not flicker
      "static": {}, 
      # the style displayed when the topology diagram flickers
      "dynamic": {}
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
For usage examples, please refer to `tools/InternetMap/example/submit_event`