# SCION Bandwidth Tester

This example adds SCION bandwidth test servers to the infrastructure. The SCION bandwidth tester is a sample application that measures the bandwidth and packet loss over a link. The size of the packets, the number of packets, the attempted bandwidth and the duration are set by the test client. For more information please visit the [SCION documentation (external link)](https://docs.scionlab.org/content/apps/bwtester.html).

## Create hosts and run bandwidth test servers

The SCION bandwidth tester is available as the service `ScionBwtestService` which has to be included and instantiated.
```python
from seedemu.services import ScionBwtestService

bwtest = ScionBwtestService()
```

The server needs a host to run on that is created in the usual way. We set the IP address explicitly to simplify connecting to the server later. Optionally, it is possible to set the UDP port the server is binding to.
```python
as150.createHost('bwtest').joinNetwork('net0', address='10.150.0.30')
bwtest.install('bwtest150').setPort(40002) # Setting the port is optional (40002 is the default)
emu.addBinding(Binding('bwtest150', filter=Filter(nodeName='bwtest', asn=150)))
```

Finally the SCION bandwidth tester service has to be added as a layer for rendering.
```python
emu.addLayer(bwtest_server)
```

The server persists over the whole time the SEED infrastructure is running and every SCION bandwidth-test client application from the SEED infrastructure can connect to it.

## Run bandwidth tests

The bandwidth test server and client commands are installed on all SCION hosts. To run a bandwidth test against the server in AS 153 we can run the following client command on any host:
```zsh
scion-bwtestclient -s 1-153,10.153.0.30:40002
```

The server address has the form `ISD-AS,IP:port`. Test parameters can be set independently in the client-to-server amd server-to-client direction with the `-cs` and `-sc` arguments, respectively. The parameters have the format `<duration (seconds)>,<packet size (bytes)>,<number of packets>,<attempted bandwidth>`. They default to `3,1000,30,80kbps`.

```zsh
scion-bwtestclient -s 1-153,10.153.0.30:40002 -cs "5,500,?,1Mbps" -sc "5,1000,?,1Mbps"
```

If at least one test parameter tuple (`cs` or `sc`) is specified, the other one use the same values. The question mark `?` can be used as a wildcard. If only one parameter is omitted, it will be calculated from the remaining ones, if more than one parameter is omitted, the default values are used.
