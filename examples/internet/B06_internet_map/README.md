# Building an internet_map that can communicate with the SEED Emulator network

By default, the internet_map network and the SEED Emulator network are not connected.
In this example, we show how to enable internet communication between the internet_map network and the SEED Emulator
network through docker's environment variables.

We create the internet_map container and set its asn, net, ip_address, port_forwarding, and env.
DEFAULT_ROUTE is the default route set for the map container

See the comments in the code for detailed explanation.

### Step 1) Set params to InternetMap

```python
docker.attachInternetMap(
    asn=151, net='net0', ip_address='10.151.0.90',
    port_forwarding='8080:8080/tcp', env=['DEFAULT_ROUTE=10.151.0.254']
)
```
