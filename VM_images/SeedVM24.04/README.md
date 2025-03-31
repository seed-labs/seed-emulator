# Instructions for creating a Seed VM using Ubuntu 24.04

## 1. Create a VM using Ubuntu 24.04

Simply create a brand new and clean Ubuntu 24.04 virtual machine.

We recommand you to set the disk volume at least 128GB, 2 CPU cores and 4G memory.

***

## 2. Execute the setup script

We provide different scripts for different CPU architectures. You can select the one that matches your system. The only difference is in the installation script of Anaconda.

For instance, the `src-amd` folder contains:

- `Files/` - folder with necessary files to setup the environment.
- `Create_Account.sh` - script to create a new user account named `seed`.
- `Lab_Base.sh` - script to install the base environment.
- `Create_Environment.sh` - script to create virtual environment
- `Install_Packages.sh` - script to install required packages.

***

### 2.1. Create a new user account

Run the following command to create a new user account named `seed`:

```bash
./Create_Account.sh
```

During the process, you will be prompted to setup a password for the new user account.

***

### 2.2. Install the base environment

Run the following command to install the base environment:

```bash
./Lab_Base.sh
```

During the process, you will be prompted whether non-superuser should be able to capture packets. Select `No`.

***

### 2.3. Install Anaconda

Firstly run the following command to initialize Anaconda:

```bash
source ~/.bashrc
```

Then run the following command to create a new conda virtual environment:

```bash
./Create_Environment.sh
```

The script will create a new python 3.10 environment named `seedpy310`.

***

### 2.4. Install required packages

Firstly run the following command to activate the `seedpy310` environment:

```bash
conda activate seedpy310
```

Then run the following command to install required packages:

```bash
./Install_Packages.sh
```

After installation, please run again `source ~/.bashrc` to make PYTHONPATH activated.