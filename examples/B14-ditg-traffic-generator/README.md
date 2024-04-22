# Iperf Traffic Generator

This example demonstrates how to use the Iperf Traffic Generator application to generate traffic among multiple hosts.

## Traffic Service

The `TrafficService` class is used to install the Iperf Traffic Generator application on the hosts and configure the traffic generation. The `TrafficServiceType` enum is used to specify the type of the traffic service. The following types are supported:

- `IPERF_GENERATOR`: Iperf Traffic Generator
- `IPERF_RECEIVER`: Iperf Traffic Receiver
- `DITG_GENERATOR`: DITG Traffic Generator
- `DITG_RECEIVER`: DITG Traffic Receiver
- `SCAPY_GENERATOR`: Scapy Traffic Generator
- `HYBRID_GENERATOR`: Hybrid Traffic Generator
- `HYBRID_RECEIVER`: Hybrid Traffic Receiver

The `TrafficService` class provides `install` method to install a traffic generator or receiver.

We can add receivers to the traffic generator using the `addReceivers` method. The `hosts` parameter is used to specify the list of receiver hosts.

The following example demonstrates how to install the Iperf Traffic Generator application on the hosts and configure the traffic generation:

```python
traffic_service = TrafficService()
traffic_service.install('iperf-receiver-1', TrafficServiceType.IPERF_RECEIVER)
traffic_service.install('iperf-receiver-2', TrafficServiceType.IPERF_RECEIVER)
traffic_service.install('iperf-generator', TrafficServiceType.IPERF_GENERATOR).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])
```

## Demo

