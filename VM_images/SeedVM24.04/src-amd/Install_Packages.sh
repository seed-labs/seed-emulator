git clone https://github.com/seed-labs/seed-emulator.git ~/seed-emulator
cd ~/seed-emulator
pip install -r ~/seed-emulator/requirements.txt
echo 'export PYTHONPATH="/home/seed/seed-emulator:$PYTHONPATH"' >> ~/.bashrc
