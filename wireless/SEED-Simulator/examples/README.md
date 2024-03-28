# Tutorials

In this document, we will explain how to utilize the simulator tutorials under the 'examples' folder. When examining the file structure, folders starting with AXX contain files related to the emulator, viewer, and driver that should be used in conjunction with the simulator. Folders starting with BXX and CXX are tutorials related to the simulator, where BXX includes a tutorial on propagation loss models, and CXX includes a tutorial on mobility models for node movement.

We will provide a guide on how to execute the simulator in the following sequence. The example below demonstrates how to run the C00-constant-velocity simulation and apply its information to the emulator:

Tutorial Video : https://youtu.be/Qk0ab_512fg 

1. Run the simulation script.
```sh
cd C00-constant-velocity
./constant-velocity-sim.py
```

2. Execute the A00-emulator script to generate emulation files, build docker containers, and bring them up.
```sh
cd A00-emulator
./emulator.py
cd output_30
docker-compose build
docker-compose up
```

3. Run the viewer from the A01-visualization folder.
```sh
cd A01-visualization
docker-compose build
docker-compose up
```
Once the container is up, you can access to the viewer: http://localhost:8080/simulator.html.


4. Execute the script in the A02-simulation-driver to apply simulation data to the emulator.
```sh
cd A02-simulation-driver
./sim-driver.sh
```

For detailed instructions, please refer to the README.md file under the respective folder.

