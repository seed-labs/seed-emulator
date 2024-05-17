from web3 import Web3
from web3.middleware import geth_poa_middleware
import json

# Connect to an Ethereum node
rpc_url = 'http://10.162.0.71:8545'
web3 = Web3(Web3.HTTPProvider(rpc_url))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Check if the connection is successful
if web3.isConnected():
    print('Connected to Ethereum node')
else:
    print('Connection failed')

# Contract address and ABI
contract_address = '0xA08Ae0519125194cB516d72402a00A76d0126Af8'
with open('./Contracts/Hello.abi', 'r') as f:
    contract_abi = json.load(f)

# Load the contract
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Check if the contract is deployed by checking its code at the address
contract_code = web3.eth.getCode(contract_address).hex()
print(f'Contract code at address {contract_address}: {contract_code}')

if contract_code != b'0x' and contract_code != '0x' and contract_code != b' ':
    print('Contract is deployed successfully')
else:
    print('Contract is not deployed')

# Call the contract function
sayHello = contract.functions.sayHello().call()
print(f'Contract function sayHello() returned: {sayHello}')
