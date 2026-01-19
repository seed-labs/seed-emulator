# Install Conda Environment for Emulator

To run the emulator code, we need to install additional python modules. We use `miniconda` to manage the development environment. This document shows how to set up the environment. 


Step 1: Run this provided script:
```
./install_conda.sh
```

This script installs `miniconda` and create an environment called `seedpy310` (based on python3.10)


Step 2: Activate `seedpy310` environment
```
conda activate seedpy310
```

Step 3: Install the required python modules

```
git clone https://github.com/seed-labs/seed-emulator.git ~/seed-emulator
cd ~/seed-emulator
pip install -r ~/seed-emulator/requirements.txt
echo 'export PYTHONPATH="$HOME/seed-emulator:$PYTHONPATH"' >> ~/.bashrc
```
