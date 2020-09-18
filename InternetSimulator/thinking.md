
# Some of the random thoughts

## Composability 

>Composability is a system design principle that deals with the inter-relationships of components. A highly composable system provides components that can be selected and assembled in various combinations to satisfy specific user requirements ([Wikipedia](https://en.wikipedia.org/wiki/Composability)).


We need to be able to form a large simulator based on existing ones. There are two types:
- compose simulators running on the same computer
- compose simulators running on different computers.

## List of components we want to provide

Feel free to add more to this list. This is our wish list. 

- **DNS server** 
  - DNS can be used to support load balancing. Can we provide this type of DNS in our simulator?

  - Use should provide the zone files to our DNS class. We will automatically configure the DNS server

- **DNS infrastructure** (including multiple servers)

- **Firewall**: users can specify their firewall rules either as a script file or directly feed their rules to our Firewall class

- **NAT server (both DNAT and SNAT)**: there are many interesting things that we can do with DNAT and SNAT, such as load balancing. I did that in my lecture using VMs, but the number of machine I could use is quite limited. Container solves that problem.

- **Special BGP**: this special BGP router can connect our simulator to the outside world. It is the gateway from the simulator to the real world. 

- **Distributed simulation**: Deploy the simulator accross multiple computers. 

- **Software Defined Network (SDN)**: Build a SDN using the opensource tools.


## Miscellaneous

Most of the tools we use in our container will come from the existing open-source tools. However, if needed, we may need to develop our own tool that will be used in the container.  Basically, we develop two types of software:

- Software that generates the simulation files
- Software that runs during the simulation