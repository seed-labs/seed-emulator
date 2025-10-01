## Demo for Zhejiang University

### Setup the Environment

To setup the environment, follow the instructions below:

1. Install required packages based on the original seed-emulator environment:

```bash
conda activate your_environment_name
pip install -r requirements.txt
```

2. Import relevant classes by adding PYTHONPATH to .bashrc:

```bash
echo "export PYTHONPATH=\"$(pwd)/Modules:\$PYTHONPATH\"" >> ~/.bashrc
```

3. Create a .env file by referring to .env_template and fill in the necessary information:

```bash
cp .env_template .env
nano .env
```

***

### Start Replaying the attack

To replay the attack, follow the instructions below:

1. Generate the basic network configuration by running large_internet.py:

```bash
python ./large_internet.py
```

2. Load the basic configuration and generate the overall dockerfile & vmfile:

```bash
python ./BGP_Prefix_Hijacking.py
```

3. Start the InternetMap:

```bash
cd InternetMap
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

4. Start the emulator network:

```bash
cd output
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

5. After the network is successfully launched, start the VMs:

```bash
cd output_vm
./vm_buildup.sh
```

6. Start the Jupyter notebook server by referring to `Jupyter/README.md` and follow the instructions in the Jupyter notebook `Jupyter/bgp_attack_cn.ipynb` or `Jupyter/bgp_attack.ipynb` to replay the attack.

***

### Stop Replaying the attack

To stop the attack, follow the instructions below:

1. Stop and destroy all the VMs:

```bash
cd output_vm
./vm_down.sh
```

2. Stop and destroy the InternetMap:

```bash
cd InternetMap
docker compose down
```

3. Stop and destroy the emulator network:

```bash
cd output   
docker compose down
```