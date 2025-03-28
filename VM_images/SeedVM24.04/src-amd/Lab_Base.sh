# Set the USERID shell variable
USERID=seed

#====================================
echo "==================================="
echo "Updating apt ..."

sudo apt update
#====================================
echo "==================================="
echo "Installing Conda..."

wget -O ~/Anaconda.sh https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Linux-x86_64.sh
chmod +x ~/Anaconda.sh
bash ~/Anaconda.sh -b -p ~/anaconda3
source ~/anaconda3/bin/activate
conda init --all

#====================================
echo "==================================="
echo "Installing Docker Utilities..."
# Uninstall old versions
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

# Set up Docker's apt repository
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install docker
sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start docker and enable it to start after the system reboot:
sudo systemctl enable --now docker

# Optionally give any user administrative privileges to docker:
sudo usermod -aG docker $USERID

sudo groupadd docker

#======================================sudo
echo "====================================="
echo "Installing Wireshark ..."

# Install Wireshark
# Make sure to select 'No' when asked whether non-superuser should be
#      able to capture packets.
sudo apt -y install wireshark
sudo chgrp $USERID /usr/bin/dumpcap
sudo chmod 750 /usr/bin/dumpcap
sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap

#=====================================
echo "====================================="
echo "Customization ..."

HOMEDIR=/home/$USERID

# Change the own of this folder (and all its files) to $USERID,
# because we need to access it from the $USERID account. This 
# guarantees that the "sudo -u $USERID cp Files/..." command will work.
sudo chown -R $USERID Files

#=====================================
# We have defined a few aliases for the SEED labs
sudo -u $USERID cp ./Files/System/seed_bash_aliases $HOMEDIR/.bash_aliases

# Customization for Wireshark
sudo -u $USERID mkdir -p $HOMEDIR/.config/wireshark/
sudo -u $USERID cp ./Files/Wireshark/preferences $HOMEDIR/.config/wireshark/preferences
sudo -u $USERID cp ./Files/Wireshark/recent $HOMEDIR/.config/wireshark/recent

#======================================
echo "====================================="
echo "Cleaning up ..."

# Clean up the apt cache
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*


#======================================
echo "***************************************"
echo "If you want to be able to SSH into the seed account, you need to set up public keys."
echo "You can find the instruction in the manual."
echo "***************************************"
source ~/.bashrc
