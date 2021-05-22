
# Thoughts on Layered Design {#Layered}


**Inspiration**. I have been using Adobe Photoshop and Premiere quite a lot (for my lecture videos). I really like the layer idea in their software. Basically, you can build each image/video as layer, and you can have many layers. When you render them, you combine all the layers together to produce the final video or images. When you modify them, you can modify each individual layers. These layer not only make modification easier, they also conceptually separate the components. You can turn them on and off easily. I am thinking about use a similar approach. 

In Android, whatever is displayed on the screen is also the merging of multiple layers of images. The OS allows the Android apps to draw on layers, making the programs much easier. 

**Similarity**. Layers are popular among image and video processing software; their goal is to render images and videos. Our system is quite similar, because our goal is to render the final text files and folder structures (container files and configuration files). Therefore, applying the layered design seems quite natural.

### The Design 

In this design, our emulator starts from a base layer. Everything else will be a separate layer added to this base layer, such as BGP layer, DNS layer, etc. When we finally "render" the emulator, we will go through each layer, and merge the information generated from each layer, and put them into the final docker and configuration files. 

For example, when generating the docker and configuration files for a BGP router, we will go through all the layers, check whether the BGP router appears in that layer. If so, get the generated data from that layer, and move on to the next layer. All the information will be combined and saved to the final docker and configuration file. 

The underlying principle of layer is the same as one of the underlying principles of software engineering: modularization. In the code I wrote, I did have modularization, but when I compose the emulator, there is not much modularization. The binding of the component (BGP, IBGP, OSPF) to the Internet is hardcoded in the program, and the logic is quite complicated. When the emulator gets more complicated with many services running on top of it, things will blow up. Layers can solve that problem. For example, I still couldn't figure out an easy way to add multi-network transit AS to the emulator. With the layered approach, this becomes very easy, because each AS's OSPF is a separate layer.

**Base Layer**. We do need to have a base layer. This layer is the barebone setup. Considering this layer as the hardware layer. We use cable, switches, and routers to create and connect networks. However, nothing is set up on the routers yet. Setting up the routers is done through a routing protocol layer. Routers inside an IXP are automatically considered as BGP routers.

**BGP Layer** If we want to add BGP to the network, we create a BGP layer. In this layer, we configure all the BGP routers specified in this layer (or all the BGP routers in the base layer). The base layer has APIs for enumerating all the BGP routers and other components, such as ASes, networks, internal routers for an AS, etc. What this layer does is to specify the peering relationship, add BGP services and the corresponding configuration (based on peerings) to each BGP routers. This layer is for EBGP only.

**IBGP Layer**. If we want to run an IBGP inside an AS, we can create an IBGP layer for an AS, and then configure all the involved BGP routers. 

**OSPF Layer**. If we want to add OSPF to the internal routers of an AS, we can create an OSPF layer for that AS. In this layer, we configure the routers for each of the machines on this layer. 


## Case Studies 

Let me use a few case studies to illustrate the benefit of the layered design. In the case studies, I will be talking about more interesting layers.   

**DNS infrastructure**. We will build the DNS infrastructure as a layer of the Internet. When we build  it,  we only need to worry about the components of these DNS servers, without worrying about their placement. This makes the job conceptually simple, because we only need to worry about things related to DNS.  

In this layer, we will create root servers, TLD servers, and various nameservers, and we assign each of them an IP address. In graphics, each component on a layer is assigned an coordinate, so when we do the rendering, we know where to place the component. In our system, IP address is our "coordinates". When we do the rendering, these nameservers will be added to the network, as a new host or a new service to an existing host. Obviously, if the network does not exist, it is considered as "out of boundary".

**BGP infrastructure**. It is very similar to DNS, because they are both infrastructures of the Internet and they both run protocols. BGP is definitely more complicated than DNS though.  In this layered design, BGP is not special at all, and it should not be built into the system by default (the current design builds the BGP into the system). Whether BGP is part of the system depends on whether we have a BGP layer or not.

**Network emulator for VPN lab**.  The network used in the VPN lab does not use any BGP. We will simply create a routing layer which assigns semi-fixed routing rules to routers. This is a very simple layer. Assigning the routing rule is actually part of the lab task. Students could either do it manually on routers after the emulator starts, or they can set the routing rules when they build the emulator. Having the layered design makes things much easier, because students do not need to worry about the other relationship. They just need to create a new layer, and configure the router in that layer. The rest of them will be taken care by the system.     

**P2P network**. P2P networks are by nature an overlay on the existing network. If we want to run a P2P network, we create P2P layer. In this layer, we only see the P2P network, without worrying about where they are. The final rendering will merge it with the underlying topology. Mapping P2P nodes to actual hosts can be pre-defined or randomly assigned.  


**Blockchain layer**. This is a concrete case of P2P network. We can build a layer for this application. In this layer, we specify N nodes, designating some of them as miners, and some of them as non-miners. Instead of binding each blockchain node to an IP address, we can bind each node to a randomly selected IP in the base layer during the rendering.  


## Interesting Functionalities with Layers

Many of the interesting ideas from the image-processing software can be applied to here. I am listing some of them here. Not all of them are useful to our applications, but I just want to put them here for the sake of brainstorming. 

- **Visibility**: Each layer has a visibility flag. If we want to generate a emulator without including that layer, we will set its visibility to zero.  

- **Layer mask**: We can even adopt the layer mask idea from most of the image-processing software, so we can mask off certain elements in a layer. For example, we can mask off the AS2 from that layer.  

- **Layer order**: not sure whether this matters or not. We can change the order how each layer is processed. This is important to image processing, but not sure there is any application here. 

- **Duplicating layers**: We can easily duplicate a layer, and change its parameter, so it can be applies to another part of the emulator.  Not sure how useful this is. 

- **Visualizing individual layers**: We can visualize individual layers, either directly in Python or turning them into an image format for external viewer. 

- **Layers are independent**: Each layer can be individually saved to a file or load from an existing file (in ```PhotoShop```, you just do the copy and paste for individual layer). Therefore, we can easily export a layer and import it to another emulator. This also solved our configuration problem, because now our configuration files are layed. We no longer need to put everything inside a single table or configuration file. Each layer has its own set of tables of files. Writing CSV files becomes much easy now.  

- **Merging rules**: When you merge layers, you can use a variety of rules, such as AND, OR, XOR, Subtract, etc. You can also set the opacity level for each layer. These rules decide how the layer on the top combines the layer at the bottom. We can use the same idea. One example is the binding services to machine. In a particular layer, we can specify that service A is bound to IP address B. We can also do random binding, basically assigning A to a randomly selected host. This is very useful for P2P applications, like blockchain. 
