from web3 import Web3
from web3.middleware import geth_poa_middleware
import json

# Connect to an Ethereum node
rpc_url = 'http://10.163.0.71:8545'
web3 = Web3(Web3.HTTPProvider(rpc_url))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

if web3.isConnected():
    print("Connected to Ethereum node successfully")
else:
    print("Failed to connect to the Ethereum node")


# Contract address and ABI
contract_address = '0xA08Ae0519125194cB516d72402a00A76d0126Af8'
with open('./Contracts/Contract.abi', 'r') as f:
    contract_abi = json.load(f)

# Load the contract
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Check if the contract is deployed by checking its code at the address
contract_code = web3.eth.getCode(contract_address).hex()
if contract_code == '0x':
    print('Contract is not deployed')
else:
    print('Contract is deployed successfully')

# Call the contract function
totalSupply = contract.functions.totalSupply().call()
print(f'Total supply: {totalSupply}')

# Check the balance of an owner
account_1 = '0xA08Ae0519125194cB516d72402a00A76d0126Af8'
account_2 = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
private_key_1 = 'f33955bfd6a24c8479916bbb16ac7f689a3e62015886498697a1afcccb021aa5'
private_key_2 = '20aec3a7207fcda31bdef03001d9caf89179954879e595d9a190d6ac8204e498'

print("Checking the initial balance of the accounts...")
account_1_init_balance = contract.functions.balanceOf(account_1).call()
print(f'Balance of account {account_1}: {account_1_init_balance}')

account_2_init_balance = contract.functions.balanceOf(account_2).call()
print(f'Balance of account {account_2}: {account_2_init_balance}')

# Transfer tokens from account 2 to account 1
print("Transferring 100 tokens from account 2 to account 1...")

transaction = contract.functions.transfer(account_1, 100).buildTransaction({
    'from': account_2,
    'nonce': web3.eth.getTransactionCount(account_2),
    'gas': 3000000,
    'gasPrice': web3.toWei('50', 'gwei'),
    'chainId': 1337
})

signed_txn = web3.eth.account.signTransaction(transaction, private_key_2)
tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)    
receipt = web3.eth.waitForTransactionReceipt(tx_hash)

account_1_final_balance = contract.functions.balanceOf(account_1).call()
account_2_final_balance = contract.functions.balanceOf(account_2).call()

print("Balance after transaction:")
print(f'Balance of account {account_1}: {account_1_final_balance}')
print(f'Balance of account {account_2}: {account_2_final_balance}')

# Check the values of fixedSizeArray
print("Checking the fixedSizeArray...")
for i in range(5):  # Since fixedSizeArray has 5 elements
    value = contract.functions.fixedSizeArray(i).call()
    print(f"fixedSizeArray[{i}] = {value}")

# Check the values of dynamicArray
print("Checking the dynamicArray...")
length = contract.functions.dynamicArrayLength().call()
print(f"Length of dynamicArray: {length}")
for i in range(length):
    value = contract.functions.dynamicArray(i).call()
    print(f"dynamicArray[{i}] = {value}")