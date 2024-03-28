# How to run Simulation + Emulation example

## Setting

### (1) SEED-Emulator
Use wireless branch of SEED-Emulator repo.
```sh
$ git checkout wireless
```

### (2) SEED-Blockchain
Use experiment branch of SEED-Blockchain repo.
```sh
$ cd seed-blockchain
$ git checkout experiment
```

Add PythonPath to use `seedsim` package. 
```sh
$ cd seed-blockchain
$ cd wireless/propagationModel
$ source development.env
``` 

Install required python packages. 
```sh
$ cd seed-blockchain
$ cd wireless/propagationModel
$ pip3 install -r requirements.txt
``` 

## Step 1. Create simulation information (/tmp/siminfo/siminfo.csv)

```sh
$ ./v2v_urban_simulation.py
```

## Step 2. Generate tc commands from siminfo.csv

```sh
$ ./generate_tc_command.py
```

## Step 3. Generate emulation files and run containers

```sh
$ ./emulator.py
$ cd output
$ dcbuild
$ ./z_start.sh
```

After completing step 2, the following file structure will be created in the /tmp/seedinfo folder:
`/tmp/seedsim/tc_command/{node_id}` folder will be shared with the container with {node_id}. And when the simulation is running, `tc_command_{iter}` will be executed at the given {iter}.

```sh
/tmp/seedsim/
├── setting
│   └── info.txt
├── siminfo
│   └── siminfo.csv
├── tc_command
│   ├── 0
│   │   ├── tc_command_0
│   │   ├── tc_command_1
│   │   ├──    ...
│   ├── 1
│   │   ├── tc_command_0
│   │   ├── tc_command_1
│   │   ├──    ...
│   ├── 2
│   │   ├── tc_command_0
│   │   ├── tc_command_1
│   │   ├──    ...
│   │   ...
└── tc_runner.sh
```

## Step 4. Run simulator client (for visualization)

```sh
$ cd seedemu-client-simulator
$ dcbuild && dcup
```

You can access to the page with "http://localhost:8080/simulator.html".
The nodes will appear after going through Step 5.

## Step 5. Run tc_runner.sh script

```sh
./tc_runner.sh
```

This script will trigger to start simulation inside the emulators.
When you want to rerun the simulation inside the emulators, run `tc_runner.sh` script again without running step 1 - step 4.


## Node Counts and Iteration Counts are customizable.

Default value is as follow:
`Node Counts: 30`
`Iteration Counts: 100`

If you want to customize them, `NODE_TOTAL` and `ITERATION` variable in 4 files need to be changed.

- `v2v_urban_simulation.py`
- `generate_tc_command.py`
- `emulator.py`
- `visualization.py`