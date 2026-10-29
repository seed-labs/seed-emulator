# Botnet Service Example

## Step 1:

In this example, we used two approaches to build up our Botnet network. First one is to load an existed base component, and deploy our botnet into the Base. Second approach is that we do not separate them, when we build the base, we also deploy Botnet as well. The following shows the files in this folder regarding to different approaches.

- Component approach:
	- 09-base-component.py (Base Component, it's from 06-mini-internet)
	- botnet-in-mini-internet.py (Botnet deploy logic)
- One-file approach:
	- 09-botnet-in-as.py

For component approach, we need to firstly run ```09-base-component.py```, then we would get a file called ```mini-internet.bin```. After that, run ```botnet-in-mini-internet.py```, we will get the final folder that contains all the containers Dockerfile.

For one file approach, we just need to run ```09-botnet-in-as.py```, then the result folder would be generated.

## Step 2:

For the details about how to launch the botnet and some demos. Check out the [labs/Botnet/lab.md](https://github.com/seed-labs/SEEDSimulator/blob/feature-merge/labs/Botnet/lab.md) document.
 