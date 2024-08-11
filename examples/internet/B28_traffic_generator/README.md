# Traffic Generation Service

This example demonstrates how to use the Traffic Generation Service to generate internet traffic among multiple hosts.

## Traffic Service

The `TrafficService` provides `install` method to install the Traffic Generator or Traffic Receiver application on a host and configure the traffic generation process.
The `install` method takes the following parameters:

- `vnode`: The name of the virtual node where the traffic service application will be installed. The `vnode` parameter is used to configure the custom domain name for the underlying host.
- `service_type`: The type of the traffic service application to be installed.

  Following `service_type` are supported:

    - `IPERF_GENERATOR`: Iperf Traffic Generator
    - `IPERF_RECEIVER`: Iperf Traffic Receiver
    - `DITG_GENERATOR`: DITG Traffic Generator
    - `DITG_RECEIVER`: DITG Traffic Receiver
    - `SCAPY_GENERATOR`: Scapy Traffic Generator

- `kwargs`: The keyword arguments to be passed to the traffic service application.

  You can pass the following keyword arguments.

    - `log_file`: The log file where the traffic generation logs will be stored. Default is `/root/traffic.log`.
    - `protocol`: The protocol to be used for traffic generation. Default is `TCP`.
    - `duration`: The duration of the traffic generation process. Default is `300`.
    - `rate`: The rate of the traffic generation process. Default is `5000`.
    - `auto_start`: Start the traffic generator script automatically. Default is `True`.
    - `extra_options`: The extra options to be used for the traffic generation process. The `extra_options` parameter value depends on the type of traffic generator being used. For example, for the iPerf3 traffic generator, you can pass the `--debug` option to enable debug mode. Please note that, the `--debug` option affects the bitrate of the testing. This is because it prints out a lot of messages on the main terminal (consuming bandwidth and CPU cycles).

## Example

The following example demonstrates how to install Traffic Service on a host and configure the traffic generation process.

## Load the Mini-Internet Component

```
emu.load('../../B00-mini-internet/base_component.bin')
```

## Install Traffic Generator and Receiver

```python
traffic_service = TrafficService()
traffic_service.install('iperf-receiver', TrafficServiceType.IPERF_RECEIVER, log_file='/root/iperf3_receiver.log')
traffic_service.install(
    "iperf-generator",
    TrafficServiceType.IPERF_GENERATOR,
    log_file="/root/iperf3_generator.log",
    protocol="TCP",
    duration=600,
    rate=0
).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])
```

## Create necessary hosts for the traffic generator and receiver

```python
as150 = base.getAutonomousSystem(150)
as150.createHost("iperf-generator").joinNetwork("net0")
as162 = base.getAutonomousSystem(162)
as162.createHost("iperf-receiver").joinNetwork("net0")
```

## Bind the Traffic Generator and Receiver to the Hosts

```python
emu.addBinding(
    Binding("iperf-generator", filter=Filter(asn=150, nodeName="iperf-generator"))
)
emu.addBinding(
    Binding("iperf-receiver", filter=Filter(asn=162, nodeName="iperf-receiver"))
)
```

## Add TrafficService to the Emulation

```python
emu.addLayer(traffic_service)
```


## Examples

There are 4 examples in this directory:

### 0-iperf-traffic-generator

iPerf3 is a tool designed for actively measuring the maximum achievable bandwidth on IP networks. It allows users to adjust various parameters related to timing, buffers, and protocols, including TCP, UDP, and SCTP with both IPv4 and IPv6. Each test performed with iPerf3 provides detailed reports on bandwidth, loss, and other relevant metrics. For more information, see [iPerf3](https://iperf.fr/iperf-doc.php) documentation.

This example demonstrates how to install and configure the iperf3 traffic generator. The traffic generation logs will be stored in the log file you specify when installing the traffic generator. In this example, the logs are in `/root/iperf3_generator.log` file. Following is the iPerf3 traffic generation log.

```
cat /root/iperf3_generator.log
Connecting to host iperf-receiver-1, port 5201
[  6] local 10.150.0.73 port 60824 connected to 10.162.0.73 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  6]   0.00-1.00   sec  3.99 GBytes  34.2 Gbits/sec  602    486 KBytes       
Connecting to host iperf-receiver-2, port 5201
[  6] local 10.150.0.73 port 41830 connected to 10.171.0.73 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  6]   0.00-1.00   sec  2.21 GBytes  19.0 Gbits/sec  499    546 KBytes       
[  6]   1.00-2.00   sec  4.17 GBytes  35.8 Gbits/sec  224    510 KBytes       
[  6]   1.00-2.00   sec  2.22 GBytes  19.1 Gbits/sec   46    546 KBytes       
[  6]   2.00-3.00   sec  3.92 GBytes  33.7 Gbits/sec  136    533 KBytes       
[  6]   2.00-3.00   sec  2.16 GBytes  18.6 Gbits/sec    4    546 KBytes       
[  6]   3.00-4.00   sec  4.09 GBytes  35.2 Gbits/sec   46    539 KBytes       
[  6]   3.00-4.00   sec  2.21 GBytes  19.0 Gbits/sec    0    546 KBytes       
[  6]   4.00-5.00   sec  4.14 GBytes  35.5 Gbits/sec   45    549 KBytes       
[  6]   4.00-5.00   sec  2.27 GBytes  19.5 Gbits/sec  136    546 KBytes       
[  6]   5.00-6.00   sec  4.45 GBytes  38.3 Gbits/sec    0    549 KBytes       
[  6]   5.00-6.00   sec  2.38 GBytes  20.5 Gbits/sec    0    546 KBytes       
[  6]   6.00-7.00   sec  4.24 GBytes  36.4 Gbits/sec    0    550 KBytes       
[  6]   6.00-7.00   sec  2.27 GBytes  19.5 Gbits/sec    1    546 KBytes       
[  6]   7.00-8.00   sec  4.40 GBytes  37.8 Gbits/sec    0    550 KBytes       
[  6]   7.00-8.00   sec  2.35 GBytes  20.2 Gbits/sec    0    546 KBytes       
[  6]   8.00-9.00   sec  4.28 GBytes  36.8 Gbits/sec    1    550 KBytes       
[  6]   8.00-9.00   sec  2.28 GBytes  19.6 Gbits/sec    0    564 KBytes       
[  6]   9.00-10.00  sec  4.41 GBytes  37.9 Gbits/sec    0    570 KBytes       
[  6]   9.00-10.00  sec  2.35 GBytes  20.2 Gbits/sec    0    564 KBytes       
[  6]  10.00-11.00  sec  4.39 GBytes  37.7 Gbits/sec  184    577 KBytes       
[  6]  10.00-11.00  sec  2.35 GBytes  20.1 Gbits/sec    3    564 KBytes       
[  6]  11.00-12.00  sec  4.35 GBytes  37.3 Gbits/sec    0    577 KBytes       
[  6]  11.00-12.00  sec  2.36 GBytes  20.3 Gbits/sec    0    612 KBytes       
[  6]  12.00-13.00  sec  4.32 GBytes  37.1 Gbits/sec   46    585 KBytes       
[  6]  12.00-13.00  sec  2.36 GBytes  20.3 Gbits/sec    1    612 KBytes       
[  6]  13.00-14.00  sec  4.26 GBytes  36.6 Gbits/sec  107    592 KBytes       
[  6]  13.00-14.00  sec  2.30 GBytes  19.7 Gbits/sec   45    656 KBytes       
[  6]  14.00-15.00  sec  4.47 GBytes  38.4 Gbits/sec    0    595 KBytes       
[  6]  14.00-15.00  sec  2.37 GBytes  20.4 Gbits/sec    0    656 KBytes       
[  6]  15.00-16.00  sec  4.29 GBytes  36.8 Gbits/sec    1    662 KBytes       
[  6]  15.00-16.00  sec  2.34 GBytes  20.1 Gbits/sec   91    694 KBytes       
[  6]  16.00-17.00  sec  4.02 GBytes  34.5 Gbits/sec  1142    755 KBytes       
[  6]  16.00-17.00  sec  2.25 GBytes  19.4 Gbits/sec  685    696 KBytes       
[  6]  17.00-18.00  sec  3.93 GBytes  33.7 Gbits/sec   45    802 KBytes       
[  6]  17.00-18.00  sec  2.04 GBytes  17.5 Gbits/sec    0    696 KBytes       
[  6]  18.00-19.00  sec  4.35 GBytes  37.4 Gbits/sec  337    802 KBytes       
[  6]  18.00-19.00  sec  2.33 GBytes  20.0 Gbits/sec   90    696 KBytes       
[  6]  19.00-20.00  sec  3.98 GBytes  34.2 Gbits/sec    0    802 KBytes       
[  6]  19.00-20.00  sec  2.28 GBytes  19.6 Gbits/sec    0    696 KBytes       
[  6]  20.00-21.00  sec  3.55 GBytes  30.5 Gbits/sec   45    802 KBytes       
[  6]  20.00-21.00  sec  2.21 GBytes  19.0 Gbits/sec   49    696 KBytes       
[  6]  21.00-22.00  sec  3.48 GBytes  29.9 Gbits/sec   95    587 KBytes       
[  6]  21.00-22.00  sec  2.16 GBytes  18.5 Gbits/sec  271    708 KBytes       
[  6]  22.00-23.00  sec  3.51 GBytes  30.2 Gbits/sec   46    587 KBytes       
[  6]  22.00-23.00  sec  2.20 GBytes  18.9 Gbits/sec    0    708 KBytes       
[  6]  23.00-24.00  sec  3.34 GBytes  28.7 Gbits/sec    4    587 KBytes       
[  6]  23.00-24.00  sec  2.10 GBytes  18.1 Gbits/sec    0    741 KBytes       
[  6]  24.00-25.00  sec  3.57 GBytes  30.7 Gbits/sec   93    587 KBytes       
[  6]  24.00-25.00  sec  2.24 GBytes  19.3 Gbits/sec    1    745 KBytes       
[  6]  25.00-26.00  sec  3.42 GBytes  29.4 Gbits/sec  180    632 KBytes       
[  6]  25.00-26.00  sec  2.13 GBytes  18.3 Gbits/sec  186    747 KBytes       
[  6]  26.00-27.00  sec  3.70 GBytes  31.8 Gbits/sec   55    632 KBytes       
[  6]  26.00-27.00  sec  2.31 GBytes  19.9 Gbits/sec    0    757 KBytes       
[  6]  27.00-28.00  sec  3.45 GBytes  29.6 Gbits/sec    0    632 KBytes       
[  6]  27.00-28.00  sec  2.20 GBytes  18.9 Gbits/sec   46    759 KBytes       
[  6]  28.00-29.00  sec  3.58 GBytes  30.7 Gbits/sec   47    632 KBytes       
[  6]  28.00-29.00  sec  2.30 GBytes  19.8 Gbits/sec    0    759 KBytes       
[  6]  29.00-30.00  sec  3.36 GBytes  28.9 Gbits/sec   49    667 KBytes       
[  6]  29.00-30.00  sec  2.11 GBytes  18.1 Gbits/sec    2    769 KBytes       
[  6]  30.00-31.00  sec  3.62 GBytes  31.1 Gbits/sec    1    667 KBytes       
[  6]  30.00-31.00  sec  2.24 GBytes  19.2 Gbits/sec   45    769 KBytes       
[  6]  31.00-32.00  sec  3.57 GBytes  30.7 Gbits/sec  175    499 KBytes       
[  6]  31.00-32.00  sec  2.27 GBytes  19.5 Gbits/sec   45    778 KBytes       
[  6]  32.00-33.00  sec  3.67 GBytes  31.5 Gbits/sec    0    580 KBytes       
[  6]  32.00-33.00  sec  2.30 GBytes  19.8 Gbits/sec    0    778 KBytes       
[  6]  33.00-34.00  sec  3.52 GBytes  30.2 Gbits/sec  181    580 KBytes       
[  6]  33.00-34.00  sec  2.23 GBytes  19.2 Gbits/sec   91    778 KBytes       
[  6]  34.00-35.00  sec  3.35 GBytes  28.8 Gbits/sec    1    580 KBytes       
[  6]  34.00-35.00  sec  2.09 GBytes  17.9 Gbits/sec    0    778 KBytes       
[  6]  35.00-36.00  sec  3.55 GBytes  30.5 Gbits/sec   50    445 KBytes       
[  6]  35.00-36.00  sec  2.21 GBytes  19.0 Gbits/sec   45    807 KBytes       
[  6]  36.00-37.00  sec  3.84 GBytes  32.9 Gbits/sec    0    510 KBytes       
[  6]  36.00-37.00  sec  2.37 GBytes  20.4 Gbits/sec    1    807 KBytes       
[  6]  37.00-38.00  sec  3.85 GBytes  33.1 Gbits/sec    0    556 KBytes       
[  6]  37.00-38.00  sec  2.40 GBytes  20.6 Gbits/sec    0    807 KBytes       
[  6]  38.00-39.00  sec  3.61 GBytes  31.0 Gbits/sec   45    573 KBytes       
[  6]  38.00-39.00  sec  2.24 GBytes  19.2 Gbits/sec    0    820 KBytes       
[  6]  39.00-40.00  sec  3.82 GBytes  32.8 Gbits/sec    0    573 KBytes       
[  6]  39.00-40.00  sec  2.39 GBytes  20.5 Gbits/sec    0    831 KBytes       
[  6]  40.00-41.00  sec  3.51 GBytes  30.1 Gbits/sec   92    573 KBytes       
[  6]  40.00-41.00  sec  2.16 GBytes  18.5 Gbits/sec    0    867 KBytes       
[  6]  41.00-42.00  sec  3.64 GBytes  31.3 Gbits/sec    0    573 KBytes       
[  6]  41.00-42.00  sec  2.26 GBytes  19.4 Gbits/sec    0    867 KBytes       
[  6]  42.00-43.00  sec  3.48 GBytes  29.9 Gbits/sec   45    660 KBytes       
[  6]  42.00-43.00  sec  2.17 GBytes  18.7 Gbits/sec   50    867 KBytes       
[  6]  43.00-44.00  sec  3.54 GBytes  30.4 Gbits/sec    0    660 KBytes       
[  6]  43.00-44.00  sec  2.20 GBytes  18.9 Gbits/sec    0    867 KBytes       
[  6]  44.00-45.00  sec  3.35 GBytes  28.8 Gbits/sec    0    687 KBytes       
[  6]  44.00-45.00  sec  2.14 GBytes  18.4 Gbits/sec   46    891 KBytes       
[  6]  45.00-46.00  sec  3.55 GBytes  30.5 Gbits/sec   45    687 KBytes       
[  6]  45.00-46.00  sec  2.17 GBytes  18.7 Gbits/sec   92    891 KBytes       
[  6]  46.00-47.00  sec  3.50 GBytes  30.1 Gbits/sec    0    687 KBytes       
[  6]  46.00-47.00  sec  2.23 GBytes  19.1 Gbits/sec    0    906 KBytes       
[  6]  47.00-48.00  sec  3.29 GBytes  28.3 Gbits/sec  355    696 KBytes       
[  6]  47.00-48.00  sec  2.08 GBytes  17.9 Gbits/sec  452    906 KBytes       
[  6]  48.00-49.00  sec  3.62 GBytes  31.1 Gbits/sec    1    732 KBytes       
[  6]  48.00-49.00  sec  2.27 GBytes  19.5 Gbits/sec   46    930 KBytes       
[  6]  49.00-50.00  sec  3.84 GBytes  33.0 Gbits/sec    0    732 KBytes       
[  6]  49.00-50.00  sec  2.36 GBytes  20.2 Gbits/sec    0    930 KBytes       
[  6]  50.00-51.00  sec  3.65 GBytes  31.4 Gbits/sec  318    734 KBytes       
[  6]  50.00-51.00  sec  2.31 GBytes  19.8 Gbits/sec    0    930 KBytes       
[  6]  51.00-52.00  sec  3.76 GBytes  32.3 Gbits/sec   45    734 KBytes       
[  6]  51.00-52.00  sec  2.35 GBytes  20.2 Gbits/sec    1    930 KBytes       
[  6]  52.00-53.00  sec  3.57 GBytes  30.6 Gbits/sec    0    748 KBytes       
[  6]  52.00-53.00  sec  2.29 GBytes  19.6 Gbits/sec   90    942 KBytes       
[  6]  53.00-54.00  sec  3.79 GBytes  32.5 Gbits/sec    1    748 KBytes       
[  6]  53.00-54.00  sec  2.38 GBytes  20.5 Gbits/sec    0    946 KBytes       
[  6]  54.00-55.00  sec  3.68 GBytes  31.6 Gbits/sec  230    748 KBytes       
[  6]  54.00-55.00  sec  2.30 GBytes  19.8 Gbits/sec    0    967 KBytes       
[  6]  55.00-56.00  sec  3.78 GBytes  32.5 Gbits/sec    0    748 KBytes       
[  6]  55.00-56.00  sec  2.39 GBytes  20.5 Gbits/sec    1    967 KBytes       
[  6]  56.00-57.00  sec  3.68 GBytes  31.7 Gbits/sec   45    748 KBytes       
[  6]  56.00-57.00  sec  2.32 GBytes  19.9 Gbits/sec   46    967 KBytes       
[  6]  57.00-58.00  sec  3.87 GBytes  33.2 Gbits/sec    0    748 KBytes       
[  6]  57.00-58.00  sec  2.42 GBytes  20.8 Gbits/sec   45    967 KBytes       
[  6]  58.00-59.00  sec  3.65 GBytes  31.3 Gbits/sec  176    757 KBytes       
[  6]  58.00-59.00  sec  2.30 GBytes  19.7 Gbits/sec   37    984 KBytes       
[  6]  59.00-60.00  sec  2.43 GBytes  20.8 Gbits/sec    0    984 KBytes       
[  6]  59.00-60.00  sec  3.82 GBytes  32.8 Gbits/sec    0    757 KBytes       
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  6]   0.00-60.00  sec   136 GBytes  19.5 Gbits/sec  3289             sender
[  6]   0.00-60.03  sec   136 GBytes  19.5 Gbits/sec                  receiver

iperf Done.
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  6]   0.00-60.00  sec   228 GBytes  32.7 Gbits/sec  5336             sender
[  6]   0.00-60.03  sec   228 GBytes  32.7 Gbits/sec                  receiver

iperf Done.
```

### 1-ditg-traffic-generator

D-ITG is a tool capable to produce traffic at packet level accurately replicating appropriate stochastic processes for both IDT (Inter Departure Time) and PS (Packet Size) random variables (exponential, uniform, cauchy, normal, pareto, etc.). D-ITG supports both IPv4 and IPv6 traffic generation and it is capable to generate traffic at network, transport, and application layer. For more information, see [D-ITG](https://allstar.jhuapl.edu/repo/p1/amd64/d-itg/doc/d-itg-manual.pdf) manual.

This example demonstrates how to install and configure the D-ITG (Distributed Internet Traffic Generator). 

The traffic generation logs will be stored in the log file you specify when installing the traffic generator. In this example, the logs are in `/root/ditg_generator.log` file. To view the logs, you need to decode the logs using `ITGDec` utility command which is provided by the D-ITG tool.

```
ITGDec /root/ditg_generator.log 
ITGDec version 2.8.1 (r1023)
Compile-time options: sctp dccp bursty multiport
-----------------------------------------------------------
Flow number: 1
From 10.150.0.73:36532
To    10.170.0.73:8999
----------------------------------------------------------
Total time               =    119.987494 s
Total packets            =          1033
Minimum delay            =      0.000000 s
Maximum delay            =      0.000000 s
Average delay            =      0.000000 s
Average jitter           =      0.000000 s
Delay standard deviation =      0.000000 s
Bytes received           =        528896
Average bitrate          =     35.263408 Kbit/s
Average packet rate      =      8.609231 pkt/s
Packets dropped          =          4182 (80.19 %)
Average loss-burst size  =   1394.000000 pkt
----------------------------------------------------------
----------------------------------------------------------
Flow number: 1
From 10.150.0.73:50558
To    10.162.0.73:8999
----------------------------------------------------------
Total time               =    102.724312 s
Total packets            =          4182
Minimum delay            =      0.000000 s
Maximum delay            =      0.000000 s
Average delay            =      0.000000 s
Average jitter           =      0.000000 s
Delay standard deviation =      0.000000 s
Bytes received           =       2141184
Average bitrate          =    166.751879 Kbit/s
Average packet rate      =     40.710908 pkt/s
Packets dropped          =          1000 (19.30 %)
Average loss-burst size  =    333.333333 pkt
----------------------------------------------------------

__________________________________________________________
****************  TOTAL RESULTS   ******************
__________________________________________________________
Number of flows          =             2
Total time               =    119.987494 s
Total packets            =          5215
Minimum delay            =      0.000000 s
Maximum delay            =      0.000000 s
Average delay            =      0.000000 s
Average jitter           =      0.000000 s
Delay standard deviation =      0.000000 s
Bytes received           =       2670080
Average bitrate          =    178.023886 Kbit/s
Average packet rate      =     43.462863 pkt/s
Packets dropped          =          5182 (49.84 %)
Average loss-burst size  =    863.666667 pkt
Error lines              =             0
----------------------------------------------------------
```

### 2-scapy-traffic-generator

Scapy is a python package that enables the user to send, sniff, dissect and forge network packets. This capability allows construction of tools that can probe, scan or attack networks. We can use Scapy to generate custom packets and send them to the network. For more information, see [Scapy](https://scapy.readthedocs.io/en/latest/) documentation.

This example demonstrates how to install and configure the Scapy Traffic Generator.

The traffic generation logs will be stored in the log file you specify when installing the traffic generator. For Scapy Generator, there will be one log file for each pair of hosts in the given network. In this example, the prefix of the logs files is `/root/scapy-logs*` .

View list of log files generated by the Scapy Traffic Generator.

```
cd /root
ls | grep scapy-logs
scapy-logs-main.log
scapy-logs_10.164.0.71_10.164.0.72.log
scapy-logs_10.164.0.71_10.170.0.71.log
scapy-logs_10.164.0.71_10.170.0.72.log
scapy-logs_10.164.0.72_10.164.0.71.log
scapy-logs_10.164.0.72_10.170.0.71.log
scapy-logs_10.164.0.72_10.170.0.72.log
scapy-logs_10.170.0.71_10.164.0.71.log
scapy-logs_10.170.0.71_10.164.0.72.log
scapy-logs_10.170.0.71_10.170.0.72.log
scapy-logs_10.170.0.72_10.164.0.71.log
scapy-logs_10.170.0.72_10.164.0.72.log
scapy-logs_10.170.0.72_10.170.0.71.log
```

The main log file is `/root/scapy-logs-main.log`.

```
cat /root/scapy-logs-main.log
Scanning networks for active hosts
Scan complete
Active hosts: ['10.164.0.72', '10.170.0.71', '10.170.0.72', '10.164.0.71']
Generating traffic from 10.164.0.72 to 10.170.0.71
Log file: /root/scapy-logs_10.164.0.72_10.170.0.71.log
Generating traffic from 10.170.0.71 to 10.164.0.72
Log file: /root/scapy-logs_10.170.0.71_10.164.0.72.log
Generating traffic from 10.164.0.72 to 10.170.0.72
Log file: /root/scapy-logs_10.164.0.72_10.170.0.72.log
Generating traffic from 10.170.0.72 to 10.164.0.72
Log file: /root/scapy-logs_10.170.0.72_10.164.0.72.log
Generating traffic from 10.164.0.72 to 10.164.0.71
Log file: /root/scapy-logs_10.164.0.72_10.164.0.71.log
Generating traffic from 10.164.0.71 to 10.164.0.72
Log file: /root/scapy-logs_10.164.0.71_10.164.0.72.log
Generating traffic from 10.170.0.71 to 10.170.0.72
Log file: /root/scapy-logs_10.170.0.71_10.170.0.72.log
Generating traffic from 10.170.0.72 to 10.170.0.71
Log file: /root/scapy-logs_10.170.0.72_10.170.0.71.log
Generating traffic from 10.170.0.71 to 10.164.0.71
Log file: /root/scapy-logs_10.170.0.71_10.164.0.71.log
Generating traffic from 10.164.0.71 to 10.170.0.71
Log file: /root/scapy-logs_10.164.0.71_10.170.0.71.log
Generating traffic from 10.170.0.72 to 10.164.0.71
Log file: /root/scapy-logs_10.170.0.72_10.164.0.71.log
Generating traffic from 10.164.0.71 to 10.170.0.72
Log file: /root/scapy-logs_10.164.0.71_10.170.0.72.log
```

You can view the log file for each host pair to see the traffic generation logs.

```
cat /root/scapy-logs_10.164.0.71_10.170.0.72.log
Sending traffic from 10.164.0.71 to 10.170.0.72
Duration: 300/300
Packet Sent: 8185
```

### 3-multi-traffic-generator

In this example, we demonstrate how to install and configure the multiple traffic generators or receivers on the same host. Here, we install both iPerf3 and D-ITG traffic generators on one host and install both iPerf3 and D-ITG receivers on another host. For each traffic generator and reciever, we can specify the log file to store the traffic generation logs. We can also specify any other parameters for each traffic generator and receiver individually.

For iPerf3 Traffic Generator, the logs are in `/root/iperf3_generator.log` file. For D-ITG Traffic Generator, the logs are in `/root/ditg_generator.log` file. The contents of the log files are shown below.

```
cat /root/iperf3_generator.log 
Connecting to host multi-traffic-receiver, port 5201
[  6] local 10.150.0.73 port 36858 connected to 10.162.0.73 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  6]   0.00-1.00   sec   128 KBytes  1.05 Mbits/sec    0    140 KBytes       
[  6]   1.00-2.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   2.00-3.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   3.00-4.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   4.00-5.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   5.00-6.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   6.00-7.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   7.00-8.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   8.00-9.00   sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]   9.00-10.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  10.00-11.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  11.00-12.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  12.00-13.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  13.00-14.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  14.00-15.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  15.00-16.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  16.00-17.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  17.00-18.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  18.00-19.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  19.00-20.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  20.00-21.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  21.00-22.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  22.00-23.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  23.00-24.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  24.00-25.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  25.00-26.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  26.00-27.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  27.00-28.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  28.00-29.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  29.00-30.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  30.00-31.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  31.00-32.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  32.00-33.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  33.00-34.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  34.00-35.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  35.00-36.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  36.00-37.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  37.00-38.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  38.00-39.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  39.00-40.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  40.00-41.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  41.00-42.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  42.00-43.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  43.00-44.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  44.00-45.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  45.00-46.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  46.00-47.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  47.00-48.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  48.00-49.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  49.00-50.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  50.00-51.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  51.00-52.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  52.00-53.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  53.00-54.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  54.00-55.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  55.00-56.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  56.00-57.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  57.00-58.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  58.00-59.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
[  6]  59.00-60.00  sec  0.00 Bytes  0.00 bits/sec    0    140 KBytes       
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  6]   0.00-60.00  sec   128 KBytes  17.5 Kbits/sec    0             sender
[  6]   0.00-60.04  sec   128 KBytes  17.5 Kbits/sec                  receiver

iperf Done.
```

```
ITGDec ditg_generator.log 
ITGDec version 2.8.1 (r1023)
Compile-time options: sctp dccp bursty multiport
|----------------------------------------------------------
Flow number: 1
From 10.150.0.73:49365
To    10.162.0.73:8999
----------------------------------------------------------
Total time               =     59.998796 s
Total packets            =         51873
Minimum delay            =      0.000000 s
Maximum delay            =      0.000000 s
Average delay            =      0.000000 s
Average jitter           =      0.000000 s
Delay standard deviation =      0.000000 s
Bytes received           =      26558976
Average bitrate          =   3541.267861 Kbit/s
Average packet rate      =    864.567349 pkt/s
Packets dropped          =             0 (0.00 %)
Average loss-burst size  =      0.000000 pkt
----------------------------------------------------------

__________________________________________________________
****************  TOTAL RESULTS   ******************
__________________________________________________________
Number of flows          =             1
Total time               =     59.998796 s
Total packets            =         51873
Minimum delay            =      0.000000 s
Maximum delay            =      0.000000 s
Average delay            =      0.000000 s
Average jitter           =      0.000000 s
Delay standard deviation =      0.000000 s
Bytes received           =      26558976
Average bitrate          =   3541.267861 Kbit/s
Average packet rate      =    864.567349 pkt/s
Packets dropped          =             0 (0.00 %)
Average loss-burst size  =             0 pkt
Error lines              =             0
----------------------------------------------------------
```


## Visualizing Traffic Flow using Internet Map

You can visualize live traffic generation using the seed emulators' web interface by applying appropriate filters. Since the iperf traffic generator was configured to generate `TCP` traffic, you can filter the traffic using the `TCP` filter. Similarly, you can filter and visualize traffic flows for other traffic generators by using their respective filters.

Avoid using the Internet map for visualizing traffic, as this will generate a significant amount of additional network traffic and could affect the test results.
