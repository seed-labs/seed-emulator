from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.layers import Base
from seedemu.compiler import Docker

# Initialize the emulator and layers
emu = Emulator()
base = Base()

# Create an autonomous system
as100 = base.createAutonomousSystem(100)

# Create a network
as100.createNetwork('net0')

# Create a host in the autonomous system and connect it to the network
host = as100.createHost('custom-host').joinNetwork('net0')
# use the first GPU only
host.setGPUDevices([0])

# download miniconda
host.addBuildCommand("mkdir -p ~/miniconda3 && curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh --output ~/miniconda3/miniconda.sh")
# # install miniconda
host.addBuildCommand("bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 && rm -rf ~/miniconda3/miniconda.sh")
# host.addBuildCommand("curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba")
host.addBuildCommand("~/miniconda3/bin/conda install -n base conda-libmamba-solver && ~/miniconda3/bin/conda config --set solver libmamba")

host.addBuildCommand("~/miniconda3/bin/conda init bash && ~/miniconda3/bin/conda init zsh")
# for chinese users
host.addBuildCommand("~/miniconda3/bin/conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/free/ && ~/miniconda3/bin/conda config --add channels https://mirrors.ustc.edu.cn/anaconda/pkgs/main/ && ~/miniconda3/bin/conda config --set show_channel_urls yes")
host.addBuildCommand("~/miniconda3/bin/conda config --add channels https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge/")
# install deps
host.addBuildCommand("CONDA_OVERRIDE_CUDA=11.8 ~/miniconda3/bin/conda install tensorflow-gpu cudnn cudatoolkit=11.8")
# test is_gpu_available
host.appendStartCommand("~/miniconda3/bin/conda run python3 -c \"import tensorflow as tf; print('is_gpu_available': tf.test.is_gpu_available())\"")

# Bind the base layer to the emulator
emu.addLayer(base)

# Render the emulation
emu.render()

# Compile the emulation
emu.compile(Docker(), './output', override=True)

print("""
Before running docker-compose, it is required to add GPU support to your Docker by:
    Following Nvidia Container Toolkit Official Guide: 
        https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/user-guide.html
    In some linux system, you can driectly install the toolkit via community package manager (e.g. AUR in arch) 
        https://wiki.archlinux.org/title/docker#With_NVIDIA_Container_Toolkit_.28recommended.29

When the container running, you are able to run your tensorflow code with GPU
""")