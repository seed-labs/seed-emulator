# Traffic Service
This includes development notes on the technical implementation of the Traffic Service.

## Technical Implementation
The following includes some technical notes on the implementation, including aspects which might be improved or expanded on in the future.

### TrafficServiceType

`TrafficServiceType` is an enumeration of the different types of traffic services that can be used in the Emulator. If a new traffic service is added, this enumeration should be updated to include the new traffic service type.

### TrafficService

Based on the `service_type` parameter, the `TrafficService.install` method creates an instance of the appropriate traffic server and associates it with the given virtual node. If multiple traffic servers are insalled on the same virtual node, then the traffic servers are merged together. The traffic server can be an instance of either a `TrafficGenerator` or a `TrafficReceiver`. If a new traffic server is implemented, then the `TrafficService.install` method should be updated to create an instance of the new traffic server.

### TrafficGenerator

The `TrafficGenerator` class is the base class for all traffic generators.
If a new traffic generator is added, it should be a subclass of the `TrafficGenerator` class.

`TrafficGenerator` class provides the following methods:

- `__init__`: Initializes the traffic generator with the following parameters.

  - `name`: The virtual node name for the traffic generator. It is used to configure the custom domain name for the underlying host.
  - `log_file`: The log file where the traffic generation logs will be stored.
  - `protocol`: The protocol to be used for traffic generation.
  - `duration`: The duration of the traffic generation process.
  - `rate`: The rate of the traffic generation process.
  - `extra_options`: The extra options to be used for the traffic generation process. This parameter value depends on the type of traffic generator being used.
- `addReceivers`: Adds traffic receiver host addresses to a traffic generator so that the traffic generator can send traffic to the specified hosts. We can specify the list of receiver hosts for the traffic generator using the `hosts` parameter.
- `install`: Installs the traffic generator application on the host. It creates `/root/traffic-targets` file on the host to store the list of receiver hosts. Any subclass of the `TrafficGenerator` class should implement the `install` method to install necessary packages for the traffic generator application.

- `extend`: Extends the traffic generator with another traffic generator. This method is used to merge multiple traffic generators together.

- `start`: Starts the traffic generation process on the host.

## Traffic Receiver

The `TrafficReceiver` class is the base class for all traffic receivers. Any new traffic receiver be a subclass of the `TrafficReceiver` class.

`TrafficReceiver` class provides the following methods:

- `__init__`: Initializes the traffic receiver with the following parameters.

  - `name`: The virtual node name for the traffic receiver. It is used to configure the custom domain name for the underlying host.
  - `log_file`: The log file where the traffic receiver logs will be stored.
- `install`: Installs the traffic receiver application on the host.  Any subclass of the `TrafficReceiver` class should implement the `install` method to install necessary packages for the traffic receiver application.

- `extend`: Extends the traffic receiver with another traffic receiver. This method is used to merge multiple traffic receivers together.