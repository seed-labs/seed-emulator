# Project File & Script Documentation

## File Descriptions

- **`assignment.pkl`**
  Contains the reassigned Autonomous System (AS) numbers and their corresponding prefixes.

- **`real_topology_{n}.txt`**
  Contains backbone network data for *n* nodes.
  > **Note:** `real_topology.txt` is the original, unpruned dataset containing over 15,000 nodes.

- **`large_internet.py`**
  Script used to process the topology.
  - **Configuration:** Select the desired backbone network dataset on **line 181**.
  - **Output:** Running this script will generate an `output` directory.

---

## `docker.py` Usage Guide

This script manages the lifecycle of the Docker containers used in the simulation.

**Command Syntax:**
```bash
python docker.py <command_id> <monitor_interval> <batch_size> <parallel_jobs>

Parameters:

<command_id>:

'1': Build images

'2': Up images (Start containers)

<monitor_interval>: Time interval (in seconds) to monitor CPU and memory usage.

<batch_size>: Number of items (images/containers) processed per batch.

<parallel_jobs>: Number of parallel processes/jobs to run.

Recommended Configurations (for AMD Machine)

1. Build Images

Command:

python docker.py 1 2 50 16


Details:

Runs the build process.

Settings: 2-second monitoring interval, batch size of 50, and 16 parallel jobs.

Verification: The script includes an internal integrity check to ensure the build is complete. You can also manually verify the approximate number of created images using:

docker images | wc


2. Start Containers (Up)

Command:

python docker.py 2 2 50 8


Details:

Starts the containers (up).

Settings: 2-second monitoring interval, batch size of 50, and 8 parallel jobs.

Verification: For the startup phase, it is recommended to manually check if all containers have started successfully by verifying the count:

docker ps | wc
