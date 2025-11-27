## install conda env on user dir
run
```
./install_conda.sh
```
This script will help installed miniconda and create a env called seedpy310(based on python3.10)

## install python requirements for  seedemu and export seedemu to PATH
activate seedpy310 env
```
conda activate seedpy310
```
then
```
git clone https://github.com/seed-labs/seed-emulator.git ~/seed-emulator
cd ~/seed-emulator
pip install -r ~/seed-emulator/requirements.txt
echo 'export PYTHONPATH="$HOME/seed-emulator:$PYTHONPATH"' >> ~/.bashrc
```
