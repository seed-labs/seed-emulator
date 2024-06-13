
import socket

chain_id    = 1337
faucet_url  = "http://faucet.net:80"
utility_url = "http://utility.net:5000"

# Ethereum nodes can only be accessed using IP address, not hostname
#ip      = socket.gethostbyname("eth3")
ip = '10.150.0.75'
eth_url = "http://" + ip + ":8545"

SEED_ADDRESS = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
SEED_KEY = '20aec3a7207fcda31bdef03001d9caf89179954879e595d9a190d6ac8204e498' 
