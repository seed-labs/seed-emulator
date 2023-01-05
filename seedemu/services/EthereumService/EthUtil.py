from __future__ import annotations
from .EthEnum import ConsensusMechanism
from typing import Dict, List
import json
from datetime import datetime, timezone
from os import path
from .EthTemplates import GenesisFileTemplates
from web3 import Web3
from sys import stderr
class Genesis():
    """!
    @brief Genesis manage class
    """

    __genesis:dict
    __consensusMechanism:ConsensusMechanism
    
    def __init__(self, consensus:ConsensusMechanism):
        self.__consensusMechanism = consensus
        self.__genesis = json.loads(GenesisFileTemplates[self.__consensusMechanism.value]) 


    def setGenesis(self, customGenesis:str):
        """!
        @brief set custom genesis 

        @param customGenesis genesis file contents to set. 

        @returns self, for chaining calls.
        """
        self.__genesis = json.loads(customGenesis)

        return self

    def getGenesis(self) -> str:
        """!
        @brief get a string format of genesis block.
        
        returns genesis.
        """
        return json.dumps(self.__genesis)

    def addAccounts(self, accounts:List[SEEDAccount]) -> Genesis:
        """!
        @brief allocate balance to account by setting alloc field of genesis file.

        @param accounts list of accounts to allocate balance. 

        @returns self, for chaining calls.
        """
        for account in accounts:
            address = account.address
            balance = account.balance

            assert balance >= 0, "Genesis::addAccounts: balance cannot have a negative value. Requested Balance Value : {}".format(account.getBalance())
            self.__genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}

        return self

    def addLocalAccount(self, address:str, balance:int) -> Genesis:
        """!
        @brief allocate balance to a local account by setting alloc field of genesis file.

        @param address : external account's address to allocate balance

        @param balance

        @returns self, for chaining calls.
        """

        assert balance >= 0, "Genesis::allocateBalance: balance cannot have a negative value. Requested Balance Value : {}".format(balance)
        checksum_address = Web3.toChecksumAddress(address)
        self.__genesis["alloc"][checksum_address[2:]] = {"balance":"{}".format(balance)}

        return self

    def setSigner(self, accounts:List[SEEDAccount]) -> Genesis:
        """!
        @brief set initial signers by setting extraData field of genesis file. 
        
        extraData property in genesis block consists of 
        32bytes of vanity data, a list of iinitial signer addresses, 
        and 65bytes of vanity data.

        @param accounts account lists to set as signers.

        @returns self, for chaning API calls. 
        """

        assert self.__consensusMechanism == ConsensusMechanism.POA, 'setSigner method supported only in POA consensus.'

        signerAddresses = ''

        for account in accounts:
            signerAddresses = signerAddresses + account.address[2:]
        
        self.__genesis["extraData"] = GenesisFileTemplates['POA_extra_data'].format(signer_addresses=signerAddresses)

        return self

    def setGasLimit(self, gasLimit:int) -> Genesis:
        """!
        @brief set GasLimit (the limit of gas cost per block)

        @param int
        
        @returns self, for chaining API calls
        """

        self.__genesis["gasLimit"] = hex(gasLimit) 

        return self

    def setChainId(self, chainId:int) -> Genesis:
        """!
        @brief set ChainId
        @param int
        @returns self, for chaining API calls
        """

        self.__genesis["config"]["chainId"] = chainId

        return self

LOCAL_ACCOUNT_KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{index}" 
ETH_ACCOUNT_KEY_DERIVATION_PATH   = "m/44'/60'/{id}'/0/{index}" 
class MnemonicAccounts():
    __base_balance:int
    __mnemonic:str
    __index:int
    __eth_id:int
    __accounts:List[SEEDAccount]

    def __init__(self, eth_id:int, mnemonic:str=None, balance:int=10, password="admin"):
        from eth_account import Account
        self.lib_eth_account = Account
        self.lib_eth_account.enable_unaudited_hdwallet_features()

        self.__eth_id = eth_id
        self.__mnemonic = "great awesome fun seed security lab protect system network prevent attack future" if mnemonic is None else mnemonic
        self.__base_balance = balance
        self.__index = 0
        self.__accounts = []
        self.__password = password

    def createAccounts(self, total:int, balance:int=-1):
        for i in range(total):
            self.createAccount(balance)

    def createAccount(self, balance:int=-1):
        self._log('creating eth account...')
        balance = self.__base_balance if balance < 0 else balance
        acct = self.lib_eth_account.from_mnemonic(self.__mnemonic, account_path=ETH_ACCOUNT_KEY_DERIVATION_PATH.format(id=self.__eth_id, index=self.__index))
        address = Web3.toChecksumAddress(acct.address)
        keystore_content = json.dumps(acct.encrypt(password='admin'))
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        keystore_filename = "UTC--"+datastr+"--"+address
        self.__accounts.append(SEEDAccount(address, balance, keystore_filename, keystore_content, self.__password))
        self.__index += 1

    def restoreAccounts(self, total, balance:int=-1):
        for i in range(total):
            self._log('restoring eth account from mnemonic...')
            balance = self.__base_balance if balance < 0 else balance
            acct = self.lib_eth_account.from_mnemonic(self.__mnemonic, account_path=ETH_ACCOUNT_KEY_DERIVATION_PATH.format(id=self.__eth_id, index=self.__index))
            address = Web3.toChecksumAddress(acct.address)
            self.__accounts.append(SEEDAccount(address, balance, "", "", ""))
            self.__index += 1


    def getAccounts(self):
        return self.__accounts
    
    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print("==== MnemonicAccounts: {}".format(message), file=stderr)

class SEEDAccount():
    address: str    
    keystore_content: str  
    keystore_filename:str  
    balance: int
    password: str

    def __init__(self, address:str, balance:int, keystore_filename:str, keystore_content:str,  password:str):
        self.address = address
        self.keystore_content = keystore_content
        self.keystore_filename = keystore_filename
        self.balance = balance
        self.password = password

class EthAccount():
    """
    @brief Ethereum Local Account.
    """
    __account: SEEDAccount

    def __init__(self, balance:int = 0,password:str = "admin", keyfilePath: str = None):
        """
        @brief create a Ethereum Local Account when initialize
        @param alloc_balance the balance need to be alloc
        @param password encrypt password for creating new account, decrypt password for importing account
        @param keyfile content of the keystore file. If this parameter is None, this function will create a new account, if not, it will import account from keyfile
        """
        from eth_account import Account
        self.lib_eth_account = Account

        account = self.__importAccount(keyfilePath=keyfilePath, password=password) if keyfilePath else self.__createAccount()
        address = account.address

        assert balance >= 0, "EthAccount::__init__: balance cannot have a negative value. Requested Balance Value : {}".format(balance)

        encrypted = self.encryptAccount(account)
        keystore_content = json.dumps(encrypted)
        
        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]

        self.__account = SEEDAccount(address, balance, keystore_filename, keystore_content, password)
    
    def __importAccount(self, keyfilePath: str, password = "admin"):
        """
        @brief import account from keyfile
        """
        self._log('importing eth account...')
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        return self.lib_eth_account.from_key(self.lib_eth_account.decrypt(keyfile_json=keyfileContent,password=password))
    
    def __createAccount(self):
        """
        @brief create account
        """
        self._log('creating eth account...')
        return  self.lib_eth_account.create()

    def encryptAccount(self, account):
        while True:
            keystore = self.lib_eth_account.encrypt(account.key, password=self.__account.password)
            if len(keystore['crypto']['cipherparams']['iv']) == 32:
                return keystore

    def getAccount(self):
        return self.__account

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print("==== EthAccount: {}".format(message), file=stderr)


class SmartContract():

    __abi_file_name: str
    __bin_file_name: str

    def __init__(self, contract_file_bin, contract_file_abi):
        self.__abi_file_name = contract_file_abi
        self.__bin_file_name = contract_file_bin

    def __getContent(self, file_name):
        """!
        @brief get Content of the file_name.
        @param file_name from which we want to read data.
        
        @returns Contents of the file_name.
        """
        file = open(file_name, "r")
        data = file.read()
        file.close()
        return data.replace("\n","")
        

    def generateSmartContractCommand(self):
        """!
        @brief generates a shell command which deploys the smart Contract on the ethereum network.
        @param contract_file_bin binary file of the smart Contract.
        @param contract_file_abi abi file of the smart Contract.
        
        @returns shell command in the form of string.
        """
        abi = "abi = {}".format(self.__getContent(self.__abi_file_name))
        byte_code = "byteCode = \"0x{}\"".format(self.__getContent(self.__bin_file_name))
        unlock_account = "personal.unlockAccount(eth.accounts[0], \"{}\")".format("admin")
        contract_command = "testContract = eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000})"
        display_contract_Info = "testContract"
        finalCommand = "{},{},{},{},{}".format(abi, byte_code, unlock_account, contract_command, display_contract_Info)

        SmartContractCommand = "sleep 30 \n \
        while true \n\
        do \n\
        \t balanceCommand=\"geth --exec 'eth.getBalance(eth.accounts[0])' attach\" \n\
        \t balance=$(eval \"$balanceCommand\") \n\
        \t minimumBalance=1000000 \n\
        \t if [ $balance -lt $minimumBalance ] \n\
        \t then \n \
        \t \t sleep 60 \n \
        \t else \n \
        \t \t break \n \
        \t fi \n \
        done \n \
        echo \"Balance ========> $balance\" \n\
        gethCommand=\'{}\'\n\
        finalCommand=\'geth --exec \"$gethCommand\" attach\'\n\
        result=$(eval \"$finalCommand\")\n\
        touch transaction.txt\n\
        echo \"transaction hash $result\" \n\
        echo \"$result\" >> transaction.txt\n\
        ".format(finalCommand)
        return SmartContractCommand
