
# Some of the random thoughts

## Composability 

>Composability is a system design principle that deals with the inter-relationships of components. A highly composable system provides components that can be selected and assembled in various combinations to satisfy specific user requirements ([Wikipedia](https://en.wikipedia.org/wiki/Composability)).


We need to be able to form a large emulator based on existing ones. There are two types:
- compose emulators running on the same computer
- compose emulators running on different computers.

## List of components we want to provide

Feel free to add more to this list. This is our wish list. 

- **DNS server** 
  - DNS can be used to support load balancing. Can we provide this type of DNS in our emulator?

  - Use should provide the zone files to our DNS class. We will automatically configure the DNS server

- **DNS infrastructure** (including multiple servers)

- **DNS support**: Right now, we have to use IP address to talk to the machines inside the emulator. We have two ways to support DNS:

  - Automatically generate mappings to the ```/etc/hosts``` for each container.
  - Provide an external DNS server (running on the VM), which serves as the local DNS server for all the containers. This local DNS server will serve the ROOT zone, so it can map everything to its IP address. We will generate the zone file automatically. 

- **Firewall**: users can specify their firewall rules either as a script file or directly feed their rules to our Firewall class

- **NAT server (both DNAT and SNAT)**: there are many interesting things that we can do with DNAT and SNAT, such as load balancing. I did that in my lecture using VMs, but the number of machine I could use is quite limited. Container solves that problem.

- **Special BGP**: this special BGP router can connect our emulator to the outside world. It is the gateway from the emulator to the real world. 

- **Distributed emulation**: Deploy the emulator accross multiple computers. 

- **Software Defined Network (SDN)**: Build a SDN using the opensource tools.

- **Data collection node**: We can build various type of data-collection nodes, and deploy them inside the emulator. For example, we can deploy a sniffer node on a BGP router, it only sniffs the packets with ```TOS==99```. For this node, we attach a file storage to it, so its data will be permanently stored in a central place, and then we can use existing pcap tools to analyze/visualize the network trace.  This is useful for visualizing attacks.  

- **Disjoint AS**: right now, we assume that all the BGP routers inside an AS are connected (directly or via an internal network). We should also support disjoint AS, which place its networks in different places, and they are not internally connected. This is quite common for global organization. 

- **Transit AS with complicated internal network**: For these ASes, to specify its internal network's topology, we can use these approaches: (1) Automatically generate one for users if users do not care too much about the topology. (2) Prepare some existing topology for users to select. (3) Ask users to provide their own topology file (CSV).

- **Testing nodes**: To automate the testing effort, for each feature we build, we should develop some testing script, and deploy them in testing nodes. When the emulator runs, those testing nodes will give us a report on the results.  For example, we can run ```birdc``` script on BGP routers to get the protocol information and save them to a permanent storage. 
This is much better than manual effort. I believe ```birdc``` can be accessed from remotely. That will be even better, because we can just run the testing script on the VM.<br> 
**Note**: This is just one idea to automate the testing. We should put more thoughts on this, so we can improve our productivity. 

- **Kubernetes**: We can deploy our emulator on multiple VMs using Kubernetes. We should generate all the Kubernetes files. 

- **Command and Control**: We can install a control server on each node. If we want to do something on a particular node, we can just send a command to it. This could be used for our management (we can have a central management system). It can also be used for botnet emulation, which is a lab that we can develop based on the emulator. 

- **Segment Routing**: The new traffic-engineering technology - makes network programming very straightforward. (example (note: In Chinese): https://www.cisco.com/c/dam/global/zh_cn/solutions/service-provider/segment-routing/pdf/linux_srv6_article1.pdf) 

- **RPKI**: The PKI for Internet Number Resources (IP addresses, ASNs). RPKI enables authenticated route origin authorization. Commonly used for defeating prefix hijacks and prevent misconfigs.

## Miscellaneous

Most of the tools we use in our container will come from the existing open-source tools. However, if needed, we may need to develop our own tool that will be used in the container.  Basically, we develop two types of software:

- Software that generates the emulation files
- Software that runs during the emulation

## Graph generation

The main file that we will generate is the docker and docker-compose files. However, we can also generate other graph files for our emulator, which is used for visualization:

- **dot file (and image file)**: We can automatically generate the dot file or image files from the model. This will make visualization much easier. 

- **web page**: We can also generate a web page and use JavaScript graphic libraries to display generated diagrams. This is for the web-based applications.

- **NetworkX**: We can use generate Python code to generate images (e.g., using the ```NetworkX``` module).

- **Levels of details**: When generating the graph, we can control the level of details. For example, we can generate a high-level graph that only shows the peering relationship among the ASes. We can also generate a detailed graph to display the detailed peering inside an IXP. 
