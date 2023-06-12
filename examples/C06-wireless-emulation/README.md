# DEMO for wireless network emulation.
## Setting
Use SDN-MANET branch of SEED-Emulator repo.
```sh
$ git checkout SDN-MANET
```

## Step 1. Generate emulation files and run containers

The emulator.py will generates emulation files of 30 nodes.
To run 30 nodes (docker containers), you need to run 
`docker-compose build` and `docker-compose up` inside the `output` folder 
generated from `emulator.py`.
The emulator runs `Babel` protocol inside and it is enabled to update loss, latency, and bandwidth among the nodes' connections via `tc` command.

```sh
$ ./emulator.py
$ cd output
$ docker-compose build
$ docker-compose up
```

## Step 2. Run simulation.py script

```sh
./simulation.py --help
usage: simulation.py [-h] {init,move} ...

positional arguments:
  {init,move}
    init       initialize nodes positisons
    move       move nodes positions

optional arguments:
  -h, --help   show this help message and exit
```

The `simulation.py` is a simple simulation script that changes nodes position. In every changes, the script calculate distances among nodes 
and update the loss among the nodes connection according to the distances. 

Currently a loss is calculated by the simple logic in `simulation_util.py`.
```python
def __get_loss(self, dist):
        loss = 100
        if dist <= 100:
            loss = 0
        elif dist <= 200:
            loss = 20    
        elif dist <= 300:
            loss = 40
        elif dist <= 400:
            loss = 60
        # elif dist <= 500:
        #     loss = 80
        return loss
```

### (1) ./simulation.py init
```sh
$ ./simulation.py init
```
The simulation.py with `init` option will initialize the nodes' positions.
There is no loss between connections at init status.
The image below shows the map after running `./simulations.py init`.
<img width="1607" alt="image" src="https://github.com/seed-labs/seed-emulator/assets/19922651/71ab034a-9d5d-4275-a039-b1295a1d96fc">


### (2) ./simulation.py move -c (or --count) COUNT
```sh
$ ./simulation.py move -c 3
```
The `move` option is used with `--count or -c`. This will move nodes for the given number of counts.
The image below shows the map after running `./simulations.py move -c 3`.
<img width="1610" alt="image" src="https://github.com/seed-labs/seed-emulator/assets/19922651/547bd67a-b54f-470d-9ba1-bc9658d04152">


## Step 3. Run map client (for visualization)

```sh
$ cd seedemu-client-simulator
$ dcbuild && dcup
```

You can access to the page with "http://localhost:8080/simulator.html".
The nodes will appear after going through Step 3.

## connectivity test
1) click a node to send ping in the map. (change to red color)
2) click a node of destination. (change to blue color)
3) click `Start Test` button in the Connectivity Test (ping) panel at the left-top side.

<img width="1607" alt="image" src="https://github.com/seed-labs/seed-emulator/assets/19922651/b69d360b-05f7-42bb-857d-50c513ba9fd5">

## (Optional) manualmoving.py

The `manualmoving.py` allows us to move a node to designated position.

```python
#!/usr/bin/env python3
# encoding: utf-8

from simulation_util import *

sim = Simulation()

#sim.move_nodes([(node_id, x_position, y_position), ...])
sim.move_nodes([(0, 0, 0),
                (1, 250, 0),
                (2, 250, 250),
                (3, 500, 0),
                (4, 500, 500)])

sim.update_loss_on_containers()
```
