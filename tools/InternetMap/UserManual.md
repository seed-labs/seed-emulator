
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
    - `bash /submit_event.sh -a flash --file /option.json`
  
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