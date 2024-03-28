# SEED Emulator for SEED Simulator

In this tutorial, the Emulator is configured to be used alongside the Simulator with two main settings. Firstly, preprocessing is done to enable the setting of network loss rates between nodes using the `tc` command. Secondly, it is configured to use the well-known wireless routing protocol, Babel Routing Protocol. By changing the loss rates, you can adjust the communication strength and adopt routes based on the communication strength according to the Babel Routing Protocol.

The emulator has 30 nodes and is designed to be used in conjunction with the simulator tutorials found in BXX and CXX. Before running the emulator.py, you should first execute the simulator script. Example simulator scripts can be found in BXX and CXX. Additionally, as emulator.py uses the seedemu Python package from SEED-Emulator, you need to perform the following setup beforehand.

```sh
$ git clone https://github.com/seed-labs/seed-emulator
$ cd seed-emulator
$ git checkout wireless
$ source development.env
```



