from flask import Flask, send_from_directory
from .config import Config
from web3 import Web3
import os, json, docker, subprocess
from web3.middleware import geth_poa_middleware
import os, sys
import time

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    client = docker.from_env()

    is_ready = 0
    containers_len = len(client.containers.list())
    while True:
        print("waiting for all containers to be ready...")
        time.sleep(3)
        new_containers_len = len(client.containers.list())
        if containers_len == new_containers_len:
            is_ready += 1
        else:
            is_ready = 0
        if is_ready > 3:
            break
        containers_len = new_containers_len
    
    # Load the configuration 
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)
    
    # Set the global parameters using the configuration data 
    app.configure = {}
    app.configure['eth_node_name_pattern'] = Config.ETH_NODE_NAME_PATTERN
    app.configure['client_waiting_time']   = Config.CLIENT_WAITING_TIME
    app.configure['key_derivation_path']   = Config.KEY_DERIVATION_PATH 
    app.configure['mnemonic_phrase']       = Config.MNEMONIC_PHRASE 
    app.configure['local_account_names']   = Config.LOCAL_ACCOUNT_NAMES 

    # Load the data from the emulator
    app.eth_accounts = load_eth_accounts(app.root_path)
    app.eth_nodes    = load_eth_nodes(app.root_path)
    # Pick the first for the default web3 URL
    eth_nodes_list = list(app.eth_nodes.items())
    assert len(eth_nodes_list) > 0
    app.web3_url  = "http://%s:8545" % eth_nodes_list[0][1]['ip'] 
    print(app.web3_url)

    # Get the consensus from the emulator
    app.consensus = get_eth_consensus()

    # Load blueprint modules
    from server.general.views import general
    from server.blockchain.blockchain import blockchain
    from server.beaconchain.view import beaconchain

    app.register_blueprint(general)
    app.register_blueprint(blockchain)
    app.register_blueprint(beaconchain)

    return app


# Load all the accounts from the emulator
def load_eth_accounts(root_path):
    path = os.path.join(root_path, "emulator_data")
    filename  = os.path.join(path, "accounts.json")

    if os.path.exists(filename) is False: # the file does not exist
        getEmulatorAccounts(path, "accounts.json")

    with open(filename) as json_file:
        eth_accounts = json.load(json_file)

    counters = {}
    new_eth_accounts = {}
    for address in eth_accounts:
        account = eth_accounts[address]
        #if self._chain_id != int(account['chain_id']):
        #    continue

        # Name might be duplicate, should we deal with it? 
        name = account['name']
        if name not in counters: # name already exists
            counters[name] = 0
        else:
            counters[name] += 1
            name = name + "-%d" % counters[name]

        new_eth_accounts[address] = {"name": name,
                                     "chain_id": account['chain_id']}

    return new_eth_accounts


# Get the ethereum nodes info: container name and ID
def load_eth_nodes(root_path):
    eth_nodes = {}
    path = os.path.join(root_path, "emulator_data")
    filename  = os.path.join(path, "containers.json")
    if os.path.exists(filename) is False: # the file does not exist
        getContainerInfo(path, "containers.json")

    with open(filename) as json_file:
        eth_nodes = json.load(json_file)

    return eth_nodes


# Cache the emulator account information in a file.
def getEmulatorAccounts(path, filename):
    os.system("mkdir -p {}".format(path))

    client = docker.from_env()
    all_containers = client.containers.list()

    mapping = {}
    counters = {}
    for container in all_containers:
      labels = container.attrs['Config']['Labels']
      if 'EthereumService' in labels.get('org.seedsecuritylabs.seedemu.meta.class', []):
          chain_id = labels.get('org.seedsecuritylabs.seedemu.meta.ethereum.chain_id')

          # record which container each key file comes from
        #   cmd = ['docker', 'exec', container.short_id, 'ls', '-1', '/root/.ethereum/keystore']
          exit_code, output = container.exec_run('ls /root/.ethereum/keystore')
          keyfilenames = output.decode("utf-8").rstrip().split('\n')
          for keyfilename in keyfilenames:
              keyfile = '/root/.ethereum/keystore/' + keyfilename
              keyname = labels.get('org.seedsecuritylabs.seedemu.meta.displayname')

              print("Getting the key file from %s" % keyname)
            #   cmd = ['docker', 'exec', container.short_id, 'cat', keyfile]
              exit_code, output = container.exec_run('cat {}'.format(keyfile))
              encrypted_key = output.decode("utf-8").rstrip().split('\n')[0]
              account = json.loads(encrypted_key)
              address = Web3.toChecksumAddress(account["address"]) 
              mapping[address] = {
                      'name':     keyname,
                      'chain_id': chain_id
              }

    save_to_file = os.path.join(path, filename)
    with open(save_to_file, 'w') as json_file:
        json.dump(mapping, json_file, indent = 4)

    return 

# Cache the container information in a file.
def getContainerInfo(path, filename):
    os.system("mkdir -p {}".format(path))

    client = docker.from_env()
    all_containers = client.containers.list()

    mapping_all = {}
    for container in all_containers:
      labels = container.attrs['Config']['Labels']
      if 'EthereumService' in labels.get('org.seedsecuritylabs.seedemu.meta.class', []):
        info_map = {}
        info_map["container_id"] = container.short_id
        info_map["displayname"] = labels.get("org.seedsecuritylabs.seedemu.meta.displayname")
        ip = labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address")
        info_map["ip"] = ip.replace("/24", "") # remove the network mask
        info_map["node_id"] = labels.get("org.seedsecuritylabs.seedemu.meta.ethereum.node_id")
        info_map["chain_id"] = labels.get("org.seedsecuritylabs.seedemu.meta.ethereum.chain_id")
        info_map["node_role"] = labels.get("org.seedsecuritylabs.seedemu.meta.ethereum.role")
        info_map["consensus"] = labels.get("org.seedsecuritylabs.seedemu.meta.ethereum.consensus")

        mapping_all[container.name] = info_map
    
    save_to_file = os.path.join(path, filename)
    with open(save_to_file, 'w') as json_file:
        json.dump(mapping_all, json_file, indent = 4)

    return 


# Get the consensus type from the emulator
def get_eth_consensus():
    client = docker.from_env()
    all_containers = client.containers.list()

    for container in all_containers:
        labels = container.attrs['Config']['Labels']
        if 'EthereumService' in labels.get('org.seedsecuritylabs.seedemu.meta.class', []):
            return labels.get("org.seedsecuritylabs.seedemu.meta.ethereum.consensus")
        
# Load the timestamp of genesis block
def load_genesis_time(root_path):
    path = os.path.join(root_path, "emulator_data")
    filename  = os.path.join(path, "genesis_timestamp.json")

    if os.path.exists(filename) is False: # the file does not exist
        return -1

    with open(filename) as json_file:
        timestamp = json.load(json_file)
    
    return timestamp
        
# Get the timestamp of genesis block
def get_genesis_time(web3_url, consensus):
    web3  = connect_to_geth(web3_url, consensus)
    return web3.eth.getBlock(0).timestamp


# Connect to a geth node
def connect_to_geth(url, consensus):
  if   consensus==  'POA': 
        return connect_to_geth_poa(url)
  elif consensus == 'POS':
        return connect_to_geth_pos(url)
  elif consensus == 'POW':
        return connect_to_geth_pow(url)

# Connect to a geth node
def connect_to_geth_pos(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!") 
   web3.middleware_onion.inject(geth_poa_middleware, layer=0)

   return web3

# Connect to a geth node
def connect_to_geth_poa(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!") 
   web3.middleware_onion.inject(geth_poa_middleware, layer=0)
   return web3

# Connect to a geth node
def connect_to_geth_pow(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!")
   return web3

