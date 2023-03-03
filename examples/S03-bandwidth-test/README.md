
# SCION Bandwidth-test

This example is based on `scion/simplescion.py`.
It adds a SCION bandwidth-test server as SEED-service to the infrastructure.
Server and client are always present as applications inside the normal SCION Docker containers created by SEED. The possibility of attaching the server as a SEED service allows more automated testbeds where the bandwidth-test can be executed without the need to explicitly start it from inside the Docker containers while the infrastructure is running.

## The SCION Bandwidth-test

The SCION bandwidth-test is a simple application that measures the bandwidth and pakcet loss over a link. Therefore, a client attempts to send SCION packets at a predefined bandwidth to a server which then returns the packets again to the client. The size of the packets, the number of packets, the attempted bandwidth and the duration can be defined by the user. The measurements described before are done by the client. For more information please visit the [SCION-Documentation (external link!)](https://docs.scionlab.org/content/apps/bwtester.html).

Server and client are pre-installed on every SEED SCION Docker container. The server can be called with
```bash
$ ./scion-bwtestserver [--listen=:<port>]
```
and the client's call is
```bash
$ ./scion-bwtestclient -s <server-address> [-cs <client-to-server-test-parameters> -sc <server-to-client-test-parameters>]
```
The server address is mandatory to set and has the form ``ISD-AS,IP:port``, e.g. ``1-150,10.150.0.71:40002``. The test parameters have the format ``<duration (seconds)>,<packet size (bytes)>,<number of packets>,<attempted bandwidth>``. It defaults to ``3,1000,30,80kbps``. If at least one test parameter tuple (``cs`` or ``sc``) is specified, the other one uses the same values. The question mark ``?`` can be used as a wildcard. If only one parameter is omitted, it will be calculated from the remaining ones, if more than one parameter is omitted, the default values are used.

## Usage as a SEED Service

The SCION bandwidth-test's server is defined as a SEED service called ScionBandwidthServerService which has to be included:
```python
from seedemu.services import ScionBwtestServerService
```
At first, the server's service class has to be initialized:
```python
bwtest_server = ScionBwtestServerService()
```
The host the server should run on can be created on the usual way. If a client will be created using a script, it has to be ensured that the IP is defined explicitly to be able to connect a client to it:
```python
as150.createHost('bwtest_server').joinNetwork('net0', address='10.150.0.30')
```
It is possible to set the port the server is binding to optionally after the service is installed, using
```python
bwtest_server.install('bwtest_server').setPort(40000)
```
otherwise the port defaults to ``40002``. Binding the server is done similarly to other services in SEED with
```python
emu.addBinding(Binding('bwtest_server', filter = Filter(nodeName='bwtest_server', asn=150)))
```
At the end, the SCION bandwidth-test server has to be added as a layer to the emulator to allow rendering:
```python
emu.addLayer(bwtest_server)
```
The server persists over the whole time the SEED infrastructure is running and every SCION bandwidth-test client application from the SEED infrastructure can connect to it.
