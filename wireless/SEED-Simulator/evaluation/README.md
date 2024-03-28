## Evaluation 
We attempted to evaluate SEED wireless internet emulator by comparing its performance with other simulators or emulators used in academic papers. 
We aims to replicate their experiments and contrast the results with those obtained from our emulator.  However, this endeavor encountered certain limitations. Our emulator lacks adequate configuration support in comparison to other simulators or emulators. Prior to proceeding with this evaluation, we opted to enhance our emulator.

## Here are some areas we need to further enhance:

### MAC Layer configuration supports
We are emulating wireless networks using a wired network. After calculating the loss rate and delay between nodes using propagation loss and delay models, we apply the network loss rate and delay between nodes using the `tc` tool. Due to this design, our platform currently lacks sufficient support for detailed configuration of the MAC layer compared to other simulators or emulators. For example, experiments such as assigning different channels to nodes or comparing performance based on WiFi standards cannot be conducted. The parameters provided by NS3 for the MAC layer include the following:
- WiFi Standard
- DataMode
- ControlMode
- MCS
- ChannelWidth
- Channel number

### Mobility Simulation (SUMO)
When reviewing the VANET simulator[1], they implemented two types of simulators: Network simulator and Mobility simulator. As of now, we have Network simulator. We also need to integrate a mobility simulator into our platform, similar to these considerations. Since most VANET simulators adopt SUMO as the mobility simulator, we believe it is necessary to review and analyze SUMO[2].

### Various Routing Protocol supports.
Upon reviewing various papers, I found that there are many articles comparing routing protocols. However, at present, we only support the Babel routing protocol, which means we are not equipped to compare multiple routing protocols.

### Network Performance Testing
We need to provide functionality for Network Performance Testing. There is a necessity to offer capabilities for testing not only with Iperf but also for assessing performance during video streaming. (This aspect is currently being developed by one of the CIS700 students.)





[1] Weber, J., Neves, M. & Ferreto, T. VANET simulators: an updated review. J Braz Comput Soc 27, 8 (2021). https://doi.org/10.1186/s13173-021-00113-x
[2] Pablo Alvarez Lopez, Michael Behrisch, Laura Bieker-Walz, Jakob Erdmann, Yun-Pang Flötteröd, Robert Hilbrich, Leonhard Lücken, Johannes Rummel, Peter Wagner, and Evamarie Wießner. 2018. Microscopic Traffic Simulation using SUMO, In The 21st IEEE International 