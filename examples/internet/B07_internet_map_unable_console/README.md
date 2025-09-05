# Building an internet_map that prohibits access to the node console

By default, the  internet_map is the CONSOLE that allows access to all nodes. 
For security reasons, the environment variable "console" is provided. When it is "false", access to the console is prohibited.

We create the internet_map container and set its port_forwarding, and env.
CONSOLE controls whether access to the console is enabled.

`false`, disabled

`true`, enabled

`Default`, enabled

See the comments in the code for detailed explanation.

### Step 1) Set params to InternetMap

```python
docker.attachInternetMap(
    port_forwarding='8080:8080/tcp', env=['CONSOLE=false']
)
```
