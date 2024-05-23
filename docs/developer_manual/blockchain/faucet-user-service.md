# Faucet User Service: An Example on How to Use Faucet 

## Fund Script Requirements: 
1) Check if the faucet server is up
2) Send request api with an account address and an amount value

```python
#!/bin/env python3

import time
import requests
import json
from eth_account import Account
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get("{faucet_url}")
        if response.status_code == 200:
            break
        time.sleep(10)
        if time.time() - start_time > timeout:
            logging.info("faucet server connection failed: 600 seconds exhausted.")
            exit()
    except Exception as e:
        pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_url = "{faucet_fund_url}"
	try:
		response = requests.post(request_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
		logging.info(response)
		if response.status_code == 200:
			api_response = response.json()
			message = api_response['message']
			if message:
				print(f"Success: {{message}}")
			else:
				logging.error("Funds request was successful but the response format is unexpected.")
		else:
			api_response = response.json()
			message = api_response['message']
			logging.error(f"Failed to request funds from faucet server. Status code: {{response.status_code}} Message: {{message}}")
			# Send another request
			logging.info("Sending another request to faucet server.")
			send_fundme_request(account_address)
	except Exception as e:
		logging.error(f"An error occurred: {{str(e)}}")
		exit()

# Create an account
user_account = Account.create()
account_address = user_account.address

# Send /fundme request to faucet server
send_fundme_request(account_address)
```

## Service Requirements:
- Install python3 python3-pip package
- Install required python packages (eth_account and requests)
- Set fund script and run

```python
def install(self, node: Node):
    """!
    @brief Install the service.
    """
    node.appendClassName("FaucetUserService")
    #Install python3 python3-pip package
    node.addSoftware('python3 python3-pip')
    #Install required python packages (eth_account and requests)
    node.addBuildCommand('pip3 install eth_account==0.5.9 requests')
    #Set fund script and run
    node.setFile('/fund.py', FUND_SCRIPT.format(faucet_url=self.__faucet_util.getFacuetUrl(),
                                                faucet_fund_url=self.__faucet_util.getFaucetFundUrl()))
    node.appendStartCommand('chmod +x /fund.py')
    node.appendStartCommand('/fund.py')
```

## FaucetUtil Requirements:
In the FaucetUserService, it utilize FaucetUtil class to get the url of the Faucet Server.
To initialize FaucetUserService, we need to specify the vnode name of faucet server and port number.
Those information are set using `FaucetUserService::setFaucetServerInfo(vnode:str, port:int)` method.

```
faucetUserService.setFaucetServerInfo(vnode = 'faucet', port=80)
```

Once the emulator is rendered, a method call flow is as follow:
`FaucetUserService::configure()` -> `FaucetUserServer::setFaucetServerInfo()`
                                 -> `FaucetUserServer::configure()`
                                 -> `FaucetUtil::configure()`

Those information will be used to configure FaucetUtil instance inside the method `FaucetUserServer::configure` according to the method call flow above.

If you are creating your own Service class utilizing faucet Server, please make sure to follow these code and flow.

```python
class FaucetUserServer:
    ...
    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port
        
    def configure(self, emulator:Emulator):
        self.__faucet_util.setFaucetServerInfo(vnode=self.__faucet_vnode_name, port=self.__faucet_port)
        self.__faucet_util.configure(emulator)
    ...

class FaucetUserService:
    ...
    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port
    
    def configure(self, emulator: Emulator):
        super().configure(emulator)

        for (server, node) in self.getTargets():
            server.setFaucetServerInfo(self.__faucet_vnode_name, self.__faucet_port)
            server.configure(emulator)
        return 
    ...
```

