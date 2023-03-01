from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import os, sys, random, subprocess
import json
import docker


class Wallet: 
    """!
    @brief The Wallet class.

    This class implements the basic functionalities of an Ethereum wallet.
    It can be considered as a library form of "MetaMask", making it
    easy for client programs to interact the Ethereum blockchain 
    (especially the emulator).
    """

    _accounts: list   # These accounts are generated from mnemonic code 
    _imported_accounts: list  # These are imported accounts

    _web3: Web3
    _default_account: Account  
    _chain_id: int
    _url: str
    _max_fee: float
    _max_priority_fee: float 
    _KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{}"
    _DEFAULT_MNEMONIC = "great amazing fun seed lab protect network system " \
                        "security prevent attack future"
    _mnemonic: str 
    _mnemonic_account_index: int  

    def __init__(self, mnemonic=None, chain_id=1337, max_fee=3.0, max_tip=2.0): 
        """!
        @brief Wallet constructor.
        """

        self._accounts = [] 
        self._imported_accounts =[] 
        self._web3 = None
        self._url  = None
        self._default_account = None
        self._mnemonic_account_index = 0
        self._chain_id = chain_id

        self._max_fee =  Web3.toWei(max_fee, 'gwei')
        self._max_priority_fee = Web3.toWei(max_tip, 'gwei')

        self._mnemonic = mnemonic
        if self._mnemonic is None:
            self._mnemonic = self._DEFAULT_MNEMONIC

        return 


    def importAccount(self, key:str, name:str):
        """!
        @brief Import an account from its private key.

        @param key The private key. 
        @param name The name given to the key.
        @returns Return self, for the purpose of API chaining.
        """

        account = Account.from_key(key)
        self._imported_accounts.append({'name': name, 'account': account})
        return self

    def importAccountFromKeystore(self, keystore:str, name:str):
        """!
        @brief Import account from the keystore folder.

        It will get the private key from the _index.json file inside 
        the keystore, using the specified key name. This pre-existing file 
        is used to store the keys obtained from the emulator. 

        @param keystore The folder name of the keystore.
        @param name The name of the key.
        @returns Return self, for the purpose of API chaining.
        """

        filename = keystore + "/_index.json"
        json_file = open(filename)
        assert json_file is not None, "File %s does not exist" % filename

        eth_accounts = json.load(json_file)
        counter = 0 
        for address in eth_accounts:
            account = eth_accounts[address]
            if account['name'] == name:
                if counter > 0:  # Multiple keys may have the same name
                    name = name +'-%d'%counter
                    self.importAccount(account['key'], name)
                else:
                    self.importAccount(account['key'], name)
                counter += 1
        return self


    def importEncryptedAccount(self, encrypted_key:str, name:str, password='admin'):
        """!
        @brief Import an account from its encrypted private key.

        @param encrypted_key The encrypted private key (a JSON string).
        @param name The name of the key.
        @param password The decryption password.
        @returns Return self, for the purpose of API chaining.
        """

        private_key = Account.decrypt(encrypted_key, password)
        self.importAccount(private_key, name)
        return self


    def exportEncryptedAccount(self, name:str, password='admin') -> str:
        """!
        @brief Export the encrypted private key. 

        @param name The name of the account.
        @param password The password used for encrypting the private key.

        @returns Return the JSON string of the encrypted key.
        """
        encrypted = None
        for account in self._accounts + self._imported_accounts:
            if account['name'] == name:
                encrypted = account['account'].encrypt(password=password)

        return encrypted


    def createAccount(self, name:str):
        """!
        @brief Create a new account from the wallet's mnemonic phrase.

        @param name The name given to the account.

        @returns Return self, for the purpose of API chaining.
        """
        Account.enable_unaudited_hdwallet_features()

        path = self._KEY_DERIVATION_PATH.format(self._mnemonic_account_index)
        account = Account.from_mnemonic(self._mnemonic, account_path=path)
        self._accounts.append({'name': name, 'account': account})

        # Make the first created account the default
        if self._default_account is None: 
            self._default_account = account

        self._mnemonic_account_index += 1

        return self


    def setDefaultAccount (self, name:str):
        """!
        @brief Set an account as the default account.

        The default account is used for signing and sending transactions 
        if the sender information is not provided. 

        @param name The name of the account.

        @returns Return self, for the purpose of API chaining.
        """
        for account in self._accounts + self._imported_accounts:
            if account['name'] == name:
                self._default_account = account['account']

        assert self._default_account is not None, "The key (%s) cannot be found" % name

        return self


    def connectToBlockchain(self, url:str, isPOA=False): 
        """!
        @brief Connect to a blockchain node

        @param url The URL of the node (e.g., http://10.150.0.71:8545)
        @param isPOA Is the POA used for the consensus protocol (Proof-Of-Authority)? 

        @returns Return self, for the purpose of API chaining.
        """

        self._url = url
        self._web3 = Web3(Web3.HTTPProvider(url))
        if isPOA:
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self._web3.isConnected(), "Connection failed"

        return self

    def sendRawTransaction(self, key, transaction:dict, wait=True, verbose=True):
        """!
        @brief Send a raw transaction. 

        @param key The sender's private key (used to sign the transaction).
        @param transaction The complete transaction data.
        @param wait Whether to wait for the receipt or not.
        @param verbose Whether to print out the full or shortened transaction receipt.

        @returns Returns the transaction hash.
        """
        assert self._web3 is not None

        print(json.dumps(transaction, indent=2))

        signed_tx = self._web3.eth.account.sign_transaction(transaction, key)
        tx_hash = self._web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        print("Transaction Hash: {}".format(tx_hash.hex()))

        if wait:
           print("Waiting for receipt ...")
           tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)
           if verbose:
               Wallet.printTransactionReceipt(tx_receipt, short=False)
           else:
               print("Abbreviated transaction ----")
               Wallet.printTransactionReceipt(tx_receipt, short=True)

        return tx_hash

    @staticmethod
    def printTransactionReceipt(tx_receipt:str, short=False):
        """!
        @brief Print out well-formatted transaction receipt.

        @param tx_receipt The transaction receipt string.
        @param short Whether to print out the full or abbreviated receipt.
        """

        tx_dict = dict(tx_receipt)
        if short: 
            short_receipt = {}
            selected_fields = ['from', 'to', 'status', 'blockNumber', 
                               'effectiveGasPrice', 'gasUsed', 'contractAddress']
            for field in selected_fields:
                if tx_dict[field] is not None:
                   short_receipt[field] = tx_dict[field] 
            print(json.dumps(short_receipt, indent=3))
        else:
            print(tx_receipt)


    def sendTransaction(self, recipient, amount, sender_name='', 
            gas=30000, nonce:int=-1, data:str='', 
            maxFeePerGas:float=-1, maxPriorityFeePerGas:float=-1, 
            wait=True, verbose=True):
        """!
        @brief Send a transaction. 

        @param recipient The recipient's account address.
        @param amount The amount of Ether to be sent.
        @param sender_name The name of the sender account (if empty, use the default account)
        @param gas The gas limit of the transaction.
        @param nonce The nonce field of the transaction.
        @param data The data field of the transaction (needed for smart contract deployment).
        @param maxFeePerGas The maxFeePerGas field (unit: gwei). 
        @param maxPriorityFeePerGas The maxPriorityFeePerGas field (unit: gwei).  
        @param wait Whether to wait for the receipt or not.
        @param verbose Whether to print out detailed transaction receipt or not.

        @returns Return the transaction hash.
        """
        assert self._web3 is not None
 
        if sender_name == '':
            sender = self._default_account
        else: 
            sender = self.__getAccountByName(sender_name)
        assert sender is not None, "Sender account does not exist"
 
        if nonce == -1:
            nonce = self._web3.eth.getTransactionCount(sender.address)

        if maxFeePerGas < 0: 
            maxFeePerGas = self._max_fee
        else:
            maxFeePerGas = Web3.toWei(maxFeePerGas, 'gwei')

        if maxPriorityFeePerGas < 0:
            maxPriorityFeePerGas = self._max_priority_fee
        else:
            maxPriorityFeePerGas = Web3.toWei(maxPriorityFeePerGas, 'gwei')

        transaction = {
          'nonce':    nonce,
          'from':     sender.address,
          'to':       recipient,
          'value':    Web3.toWei(amount, 'ether'),
          'chainId':  self._chain_id,
          'gas':      gas,
          'maxFeePerGas':         maxFeePerGas,
          'maxPriorityFeePerGas': maxPriorityFeePerGas,
          'data':     data
        }

        tx_hash = self.sendRawTransaction(sender.key, transaction, wait, verbose)
        return tx_hash


    def deployContract(self, contract_file, sender_name='', amount=0, gas=3000000, wait=True, verbose=True):
        """!
        @brief Deploy a smart contract

        @param contract_file The name of the file containing the contract bytecode (the bin file).
        @param sender_name The name of the sender account (if empty, use the default account).
        @param amount The amount of Ether to be sent when deploying the contract.
        @param gas The gas limit for the transaction.
        @param wait Whether to wait for the receipt or not.
        @param verbose Whether to print out detailed transaction receipt or not.

        @returns Return the transaction hash.
        """
        with open(contract_file) as contract:
            data = contract.read()
            data.replace("\n","")

        txhash = self.sendTransaction(None, amount, sender_name, gas=gas, 
                                      data=data, wait=wait, verbose=verbose)
        return txhash 


    def createContract(self, address, abi:str):
        """!
        @brief Create a contract object.

        @param address The address of the contract.
        @param abi The ABI information of the contract. 

        @returns Return the contract object.
        """

        contract   = self._web3.eth.contract(address=address, abi=abi)
        return contract


    def invokeContract(self, function, sender_name='', amount=0, gas=3000000, wait=True, verbose=True):
        """!
        @brief Invoke a contract function via a transaction.

        @param function The function object.  
        @param sender_name The name of the sender account (if empty, use the default account).
        @param amount The amount of Ether to be sent.
        @param gas The gas limit for the transaction.
        @param wait Whether to wait for the receipt or not.
        @param verbose Whether to print out detailed transaction receipt or not.

        @returns Return the transaction hash.
        """

        assert self._web3 is not None
        assert function is not None

        if sender_name == '':
            sender = self._default_account
        else:
            sender = self.__getAccountByName(sender_name)
        assert sender is not None, "Sender account does not exist"

        transaction_info = {
            'nonce':    self._web3.eth.getTransactionCount(sender.address),
            'from':     sender.address,
            'value':    Web3.toWei(amount, 'ether'),
            'chainId':  self._chain_id,
            'gas':      gas,
            'maxFeePerGas':         self._max_fee,
            'maxPriorityFeePerGas': self._max_priority_fee
        }

        transaction = function.buildTransaction(transaction_info)

        tx_hash = self.sendRawTransaction(sender.key, transaction, wait, verbose)
        return tx_hash


    def __getAccountByAddress(self, address:str):
        """!
        @brief Get the Account object from the account address.
        """

        for account in self._accounts + self._imported_accounts:
            if account['account'].address == address:
                return account['account']

        return None


    def __getAccountByName(self, name:str):
        """!
        @brief Get the Account object from the account name.
        """
        for account in self._accounts + self._imported_accounts:
            if account['name'] == name:
                return account['account']

        return None

 
    def getAccountAddressByName(self, name:str):
        """!
        @brief Get the account address from the account name. 
        @param name The name of the account.
        @returns Return the account address.
        """
        account = self.__getAccountByName(name)

        if account is not None:
           return account.address
        else: 
           return None

    def getBalanceByName(self, name, unit='ether') -> int:
        """!
        @brief Get the balance of an account from a name.
        @param name The name of the account.
        @param unit The unit of the balance value.
        @returns Return the balance.
        """

        address = self.getAccountAddressByName(name)
        return self.getBalance(address, unit)


    def getBalance(self, address, unit='ether') -> int:
        """!
        @brief Get the balance of an account. 
        @param address The account address.
        @param unit The unit of the balance value. 
        @returns Return the balance. 
        """
        checksum_address = Web3.toChecksumAddress(address)
        balance = self._web3.eth.get_balance(checksum_address)
        return Web3.fromWei(balance, unit)


    def getBalanceForAll(self, unit='ether') -> dict:
        """!
        @brief Get the balances of all the accounts in the wallet.
        @param unit The unit of the balance value. 
        @returns Return balance and address for each account name. 
        """
        all_balance = {}
        for account in self._accounts + self._imported_accounts:
            address = account['account'].address
            balance = float(self.getBalance(address, unit))
            name = account['name']
            all_balance[name] = {'address': address, 'balance': balance}

        return all_balance 


    def getNonce(self, address) -> int:
        """!
        @brief Get the current nonce value of an account. 
        @param address The account address.
        @returns Return the nonce value.
        """
        checksum_address = Web3.toChecksumAddress(address)
        return self._web3.eth.getTransactionCount(checksum_address)


    def getNonceByName(self, name:str) -> int:
        """!
        @brief Get the current nonce value of an account using name. 
        @param name The name of the account.
        @returns Return the nonce value.
        """
        address = self.getAccountAddressByName(name)
        return self.getNonce(address)


    def getNonceForAll(self) -> dict:
        """!
        @brief Get the current nonce values for all the accounts in the wallet.
        @returns Return nonce and address for each account name. 
        """

        all_nonces = {}
        for account in self._accounts + self._imported_accounts:
            address = account['account'].address
            nonce   = self.getNonce(address)
            name = account['name']
            all_nonces[name] = {'address': address, 'nonce': nonce}

        return all_nonces


    def printAccounts(self):
        """!
        @brief Print out all the accounts (address and key) in the wallet.
        @returns Return self, for the purpose of API chaining.
        """

        for account in self._accounts + self._imported_accounts:
            print("Address:     %s" % account['account'].address)
            print("Private key: %s" % account['account'].key.hex())


    def getTransactionReceipt(self, txhash:str) -> dict:
        """!
        @brief Get the transaction receipt from the transaction hash.
        @param txhash Transaction hash.
        @returns Return the transaction receipt (a dictionary).
        """

        receipt = self._web3.eth.get_transaction_receipt(txhash)
        tx_receipt = dict(receipt)
        return tx_receipt


    def getContractAddress(self, txhash:str) -> str:
        """!
        @brief Get the contract address from the transaction hash.
        @param txhash Transaction hash.
        @returns Return the contract address.
        """

        receipt = self._web3.eth.get_transaction_receipt(txhash)
        tx_receipt = dict(receipt)
        return tx_receipt['contractAddress']




class EmuWallet (Wallet):
    """!
    @brief A utility class, providing pre-built wallets.
    """

    def __init__(self, url:str = 'http://10.150.0.72:8545', chain_id:int = 1337, isPOA=False):
        """!
        @brief The constructor.
        @param url The URL of the Ethereum node.
        """

        super().__init__()

        self._url = url
        self._chain_id = chain_id
        self._keystore = 'keystore/eth/'

        self.connectToBlockchain(self._url, isPOA)

    def addEmulatorAccounts(self):
        """!
        @brief Add all the keys from the emulator.

        The key information is stored in the cache file "./keystore/eth/_index.json". 
        If the folder does not exist, get the keys from the emulator and store 
        them in the cache file. 
        """

        isExist = os.path.exists(self._keystore)
        if isExist is False: # the keystore folder does not exist
            self._getEmulatorKeys(keystore=self._keystore)

        index_file = self._keystore +"/_index.json"         
        json_file = open(index_file)
        assert json_file is not None, "File %s does not exist" % keystore

        eth_accounts = json.load(json_file)
        counters = {}
        for address in eth_accounts:
            account = eth_accounts[address]
            if self._chain_id != int(account['chain_id']):
                continue

            name = account['name']
            if name not in counters: # name already exists
                counters[name] = 0 
            else:
                counters[name] += 1 
                name = name + "-%d" % counters[name]

            self.importAccount(account['key'], name)

        return self


    def addLocalAccounts(self, names:list = None):
        """!
        @brief Add some of the accounts from the Emulator.
        If the name list is not provided, use a fixed name list.

        @param names The list of account names. 
        @returns Return self for API chaining.
        """

        if names is None:
             names = ['Alice', 'Bob', 'Charlie', 'David', 'Eve']

        for name in names:
            self.createAccount(name)

        if self._default_account is None:
            if len(names) > 0:
               self.setDefaultAccount(names[0])

        return self


    def getRandomAccountName(self, scope:str = 'all'):
        """!
        @brief Get a random account from the wallet. 
        @param scope The scope of accounts ('local', 'emulator', 'all')

        @returns Return the name of an account
        """

        if scope == 'local': 
            accounts = self._accounts
        elif scope == 'emulator': 
            accounts = self._imported_accounts
        else:
            accounts = self._accounts + self._imported_accounts

        total = len(accounts)
        index = random.randint(0, total-1)

        return accounts[index]['name'] 


    def _getEmulatorKeys(self, keystore):
        """!
        @brief Get the keys from the emulator, save them to keystore/_index.json

        It takes a long time to get and encrypt all the keys from the emulator. 
        This method will do it once, and cache the keys in keystore/_index.json. 
        After that, loading the keys from the emulator will use this cache. 

        @param keystore The keystore folder name
        """

        client = docker.from_env()
        all_containers = client.containers.list()
        
        os.system("mkdir -p %s"  % keystore)
        
        mapping = {}
        counters = {} 
        for container in all_containers:
          labels = container.attrs['Config']['Labels']
          if 'EthereumService' in labels.get('org.seedsecuritylabs.seedemu.meta.class', []):
              chain_id = labels.get('org.seedsecuritylabs.seedemu.meta.chain_id')
        
              # record which container each key file comes from
              cmd = ['docker', 'exec', container.short_id, 'ls', '-1', '/root/.ethereum/keystore']
              filenames = subprocess.check_output(cmd).decode("utf-8").rstrip().split('\n') 
              for filename in filenames:
                  keyfile = '/root/.ethereum/keystore/' + filename
                  keyname = labels.get('org.seedsecuritylabs.seedemu.meta.displayname')
        
                  print("Decrypting the key from %s" % keyname)
                  cmd = ['docker', 'exec', container.short_id, 'cat', keyfile]
                  encrypted_key = subprocess.check_output(cmd).decode("utf-8").rstrip().split('\n')[0]
                  private_key = Account.decrypt(encrypted_key, 'admin')
                  acct = Account.from_key(private_key)
                  address = Web3.toChecksumAddress(acct.address)
        
                  if keyname not in counters:   # Name already exists
                        counters[keyname] = 0
                  else:
                        counters[keyname] += 1
                        keyname = keyname + "-%d" % counters[keyname]
        
                  mapping[address] = { 
                          'name': keyname,
                          'key':  acct.key.hex(), 
                          'chain_id': chain_id
                  }
        
        with open('%s/_index.json' % keystore, 'w') as json_file:
            json.dump(mapping, json_file, indent = 4)


