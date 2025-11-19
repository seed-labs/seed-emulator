## Demo for Zhejiang University

This demo is for an exhibit in the Zhejiang University. It uses a special setup that is not meant for the general public. The setup  requires the Proxmox VM system. 

### Setup the Environment

To setup the environment, follow the instructions below:

1. Install the required packages based on the original seed-emulator environment:

```bash
conda activate your_environment_name
pip install -r requirements.txt
```

2. Import relevant classes by adding `PYTHONPATH` to `.bashrc`:

```bash
echo "export PYTHONPATH=\"$(pwd)/Modules:\$PYTHONPATH\"" >> ~/.bashrc
```

3. Create an `.env` file and fill in the necessary information (see `.env_template`):

```bash
cp .env_template .env
nano .env
```

### Start Replaying the attack

To replay the attack, follow the instructions below:

1. Generate the emulator:

```bash
python ./large_internet.py
python ./BGP_Prefix_Hijacking.py
```

2. Start the emulator:

```bash
cd output
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

3. After the emulator is successfully launched, start the VMs:

```bash
cd output_vm
./vm_buildup.sh
```

5. Start the Jupyter notebook server (see `Jupyter/README.md`) and follow the instructions in the Jupyter notebook `Jupyter/bgp_attack_cn.ipynb`  to replay the attack.


### Stop Replaying the attack

To stop the attack, follow the instructions below:

1. Stop and destroy all the VMs:

```bash
cd output_vm
./vm_down.sh
```

2. Stop and destroy the emulator network:

```bash
cd output   
docker compose down
```
