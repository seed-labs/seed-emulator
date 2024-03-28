# Strategic Network Model for Real-Time Video Streaming and Interactive Applications in IoT-MANET

Gupta, A. et al. (2023). Strategic Network Model for Real-Time Video Streaming and Interactive Applications in IoT-MANET. In: Zhang, YD., Senjyu, T., So-In, C., Joshi, A. (eds) Smart Trends in Computing and Communications. Lecture Notes in Networks and Systems, vol 396. Springer, Singapore. https://doi.org/10.1007/978-981-16-9967-2_26

## Simulation parameters

### General
Simulation time         : 300
Total number of nodes   : 16
source node             : 12
sink node               : 4
coverage area           : 1000 x 1000 m^2
*data rate              : 331,776kbps(15FPS)*
packet size             : 1472 Bytes

### Physical Layer
Transmission power 30dBm
*Tx antenna gain        : 9dBi*
*Rx antenna gain        : 9dBi*
Propagatio loss model   : FriisPropagationLossModel - implemented
propataion delay model  : constant speed propagation delay model

### *MAC Layer*
*WiFi standard               : WIFI_PHY_STANDARD_80211ac*
*RemoteStationManager        : ns3::Constant Rate Wifi Manager*
*DataMode                    : VhtMcs8*
*controlMode                 : VhtMcs8*
*MCS                         : 8*
*ChannelWidth                : 80*
=======================================
*Nodes 0-3 channel number    : 106*
*Nodes 4-7 channel number    : 122*
*Nodes 8-11 channel number   : 138*
*Nodes 12-15 channel number  : 155*
=======================================
-> The setting allows only nodes sharing the same channel to communicate with each other. In our setting, the loss rate will be set to 100% to prevent communication between different groups.


## Limitation
* The setting allows only nodes sharing the same channel to communicate with each other. In our setting, the loss rate will be set to 100% to prevent communication between different groups.
* The movements are limited.
* When conducting network testing, it is unclear which nodes to use as the source and destination nodes are not specified.






