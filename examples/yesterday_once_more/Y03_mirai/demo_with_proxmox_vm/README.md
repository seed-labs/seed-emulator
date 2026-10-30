## Demo for Proxmox VM System

### Setup the Environment

To setup the environment, follow the instructions below:

1. Install required packages based on the original seed-emulator environment:

```bash
conda activate your_environment_name
pip install -r requirements.txt
```

2. Import relevant classes by adding PYTHONPATH to .bashrc:
> or ~/.zshrc , depends your shell

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

1. Start the emulator network:

```bash
python3 mirai_internet_with_dns.py
cd output
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

2. After the network is successfully launched, start the VMs:

```bash
cd output_vm
./vm_buildup.sh
```

3. Follow the instructions in the Jupyter notebook `mirai.ipynb` to replay the attack.

***

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