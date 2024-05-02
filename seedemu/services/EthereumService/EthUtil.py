from __future__ import annotations
from .EthEnum import ConsensusMechanism
from typing import List
import json
from datetime import datetime, timezone
from os import path
from .EthTemplates import GenesisFileTemplates
from sys import stderr
from time import time

class Genesis():
    """!
    @brief Genesis manage class
    """

    _genesis:dict
    _consensusMechanism:ConsensusMechanism

    def __init__(self, consensus:ConsensusMechanism):
        from web3 import Web3
        self._Web3 = Web3
        self._consensusMechanism = consensus
        self._genesis = json.loads(GenesisFileTemplates[self._consensusMechanism.value])
        self._genesis["timestamp"] = hex(int((time())))
        

    def setGenesis(self, customGenesis:str):
        """!
        @brief set custom genesis 

        @param customGenesis genesis file contents to set. 

        @returns self, for chaining calls.
        """
        self._genesis = json.loads(customGenesis)

        return self

    def getGenesis(self) -> str:
        """!
        @brief get a string format of genesis block.
        
        returns genesis.
        """
        return json.dumps(self._genesis)

    def addCode(self, address: str, code: str) -> Genesis:
        """!
        @brief add code to genesis file.

        @param address address to add code.
        @param code code to add.

        @returns self, for chaining calls.
        """
        if self._genesis["alloc"][address[2:]] is not None:
            self._genesis["alloc"][address[2:]]["code"] = code
        else:
            self._genesis["alloc"][address[2:]] = {"code": code}

        return self

    def addAccounts(self, accounts:List[AccountStructure]) -> Genesis:
        """!
        @brief allocate balance to account by setting alloc field of genesis file.

        @param accounts list of accounts to allocate balance. 

        @returns self, for chaining calls.
        """
        for account in accounts:
            address = account.address
            balance = account.balance

            assert balance >= 0, "Genesis::addAccounts: balance cannot have a negative value. Requested Balance Value : {}".format(account.getBalance())
            self._genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}

        return self

    def addLocalAccount(self, address:str, balance:int) -> Genesis:
        """!
        @brief allocate balance to a local account by setting alloc field of genesis file.

        @param address : external account's address to allocate balance

        @param balance

        @returns self, for chaining calls.
        """

        assert balance >= 0, "Genesis::allocateBalance: balance cannot have a negative value. Requested Balance Value : {}".format(balance)
        checksum_address = self._Web3.toChecksumAddress(address)
        self._genesis["alloc"][checksum_address[2:]] = {"balance":"{}".format(balance)}

        return self

    def setSigner(self, accounts:List[AccountStructure]) -> Genesis:
        """!
        @brief set initial signers by setting extraData field of genesis file. 
        
        extraData property in genesis block consists of 
        32bytes of vanity data, a list of initial signer addresses, 
        and 65bytes of vanity data.

        @param accounts account lists to set as signers.

        @returns self, for chaining API calls. 
        """

        assert self._consensusMechanism == ConsensusMechanism.POA, 'setSigner method supported only in POA consensus.'

        signerAddresses = ''

        for account in accounts:
            signerAddresses = signerAddresses + account.address[2:]

        self._genesis["extraData"] = GenesisFileTemplates['POA_extra_data'].format(signer_addresses=signerAddresses)

        return self

    def setGasLimit(self, gasLimit:int) -> Genesis:
        """!
        @brief set GasLimit (the limit of gas cost per block)

        @param int
        
        @returns self, for chaining API calls
        """

        self._genesis["gasLimit"] = hex(gasLimit) 

        return self

    def setChainId(self, chainId:int) -> Genesis:
        """!
        @brief set ChainId
        @param int
        @returns self, for chaining API calls
        """

        self._genesis["config"]["chainId"] = chainId

        return self

class AccountStructure():
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

# Make the class stateless.


LOCAL_ACCOUNT_KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{index}" 
ETH_ACCOUNT_KEY_DERIVATION_PATH   = "m/44'/60'/{id}'/0/{index}" 
class EthAccount():
    """
    @brief Ethereum Local Account.
    """
    
    @staticmethod 
    def importAccount(keyfilePath: str, balance:int, password = "admin"):
        """
        @brief import account from keyfile
        """
        from eth_account import Account
        EthAccount._log('importing eth account...')
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        
        account = Account.from_key(Account.decrypt(keyfile_json=keyfileContent,password=password))

        keystore_content = json.dumps(EthAccount.__encryptAccount(account=account, password=password))

        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        keystore_filename = "UTC--"+datastr+"--"+account.address

        return AccountStructure(account.address, balance, keystore_filename, keystore_content, password)

    @staticmethod
    def importAccountFromKey(key:str, balance: int):
        """
        @brief Call this api to import an account from key.

        @param key key hex string of an account to import.
        @param balance The balance to allocate to the account.

        @returns self, for chaining API calls.
        """
        from eth_account import Account

        account = Account.from_key(key)

        keystore_content = json.dumps(EthAccount.__encryptAccount(account=account, password="admin"))

        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        keystore_filename = "UTC--"+datastr+"--"+account.address
        
        return AccountStructure(account.address, balance, keystore_filename, keystore_content, "admin")
    
    @staticmethod
    def __encryptAccount(account, password:str):
        from eth_account import Account
        while True:
            keystore = Account.encrypt(account.key, password=password)
            if len(keystore['crypto']['cipherparams']['iv']) == 32:
                return keystore

    @staticmethod
    def createEmulatorAccountFromMnemonic(id:int, mnemonic:str, balance:int, index:int, password:str):
        from eth_account import Account
        from web3 import Web3
        Account.enable_unaudited_hdwallet_features()

        EthAccount._log('creating node_{} emulator account {} from mnemonic...'.format(id, index))
        acct = Account.from_mnemonic(mnemonic, account_path=ETH_ACCOUNT_KEY_DERIVATION_PATH.format(id=id, index=index))
        address = Web3.toChecksumAddress(acct.address)
        
        keystore_content = json.dumps(EthAccount.__encryptAccount(account=acct, password=password))
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        keystore_filename = "UTC--"+datastr+"--"+address
        
        return AccountStructure(address, balance, keystore_filename, keystore_content, password)

    @staticmethod
    def createEmulatorAccountsFromMnemonic(id:int, mnemonic:str, balance:int, total:int, password:str):
        accounts = []
        index = 0 
        for i in range(total):    
            accounts.append(EthAccount.createEmulatorAccountFromMnemonic(id, mnemonic, balance, index, password))
            index += 1
        
        return accounts

    @staticmethod
    def createLocalAccountFromMnemonic(mnemonic:str, balance:int, index:int):
        from eth_account import Account
        from web3 import Web3
        Account.enable_unaudited_hdwallet_features()

        EthAccount._log('creating local account {} from mnemonic...'.format(index))
        acct = Account.from_mnemonic(mnemonic, account_path=LOCAL_ACCOUNT_KEY_DERIVATION_PATH.format(index=index))
        address = Web3.toChecksumAddress(acct.address)

        return AccountStructure(address, balance, "", "", "")

    @staticmethod
    def createLocalAccountsFromMnemonic(mnemonic:str, balance:int, total:int):
        accounts = []
        index = 0 
        for i in range(total):
            accounts.append(EthAccount.createLocalAccountFromMnemonic(mnemonic, balance, index))
            index += 1

        return accounts

    @staticmethod
    def _log(message: str) -> None:
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
