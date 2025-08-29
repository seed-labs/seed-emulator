**Please start the emulator and map container in `examples/internet/B06_internet_map` first**

1. visit [http://localhost:8080/install.html](http://localhost:8080/install.html), click "install" on the "submit_event" line to install "submit_event".
2. enter any host container, (e.g., `docker exec -it as150h-host_1-10.150.0.72 bash`)
3. execute the submit_event.sh script in the container
   - `bash /submit_event.sh -a flash`, the container will flash.
   - `bash /submit_event.sh -a highlight`, the container will be highlighted.
   - `bash /submit_event.sh -a flash -f /option.json`, the container will alternately flash according to the static and dynamic styles defined in the json file.
   - `bash /submit_event.sh -a highlight -f /option.json`, the container will be displayed in the static style defined in the json file.
   - `bash /submit_event.sh -f /option.json`, when data packets that comply with the filter rules flow through, the container will flash according to the static and dynamic defined in the json file.
   - `bash /submit_event.sh`, when data packets that comply with the filter rules flow through, the container will flash in the default style.
   ```json
   // option.json e.g.1
   {
       "static": {
           "borderWidth": 1,
           "color": {
               "background": "blue"
           },
           "size": 50
       },
       "dynamic": {
           "borderWidth": 8,
           "color": {
               "background": "green"
           },
           "size": 100,
           "shape": "image",
           "image": "https://imgservice.suning.cn/uimg1/b2c/image/cGX8azM3YNHvS-MuQIARqA.jpg_800w_800h_4e"
       }
   }
   ```
   
   ```json
   // option.json e.g.2
   {
    "static": {
        "borderWidth": 1,
        "color": {
            "background": "blue"
        },
        "size": 50
    },
    "dynamic": {
        "borderWidth": 8,
        "color": {
            "background": "green"
        }
    }
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
            'static': {
                "borderWidth": 2,
                "color": {
                    "background": "yellow"
                },
                "size": 20
            }
        }
        json.dump(_option_content, f)

set_option_json()
subprocess.Popen(["bash /submit_event.sh -a flash -f /option.json"], shell=True)
```
