from __future__ import annotations
from .EthEnum import ConsensusMechanism
from typing import Dict, List
import json
from datetime import datetime, timezone
from os import path
from .EthTemplates import GenesisFileTemplates

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

    def allocateBalance(self, accounts:List[EthAccount]) -> Genesis:
        """!
        @brief allocate balance to account by setting alloc field of genesis file.

        @param accounts list of accounts to allocate balance. 

        @returns self, for chaining calls.
        """
        for account in accounts:
            address = account.getAddress()
            balance = account.getAllocBalance()

            assert balance >= 0, "Genesis::allocateBalance: balance cannot have a negative value. Requested Balance Value : {}".format(account.getAllocBalance())
            self.__genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}

        return self

    def setSigner(self, accounts:List[EthAccount]) -> Genesis:
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
            signerAddresses = signerAddresses + account.getAddress()[2:]
        
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

class EthAccount():
    """
    @brief Ethereum Local Account.
    """

    __address: str    
    __keystore_content: str  
    __keystore_filename:str  
    __alloc_balance: int
    __password: str
    


    def __init__(self, alloc_balance:int = 0,password:str = "admin", keyfilePath: str = None):
        """
        @brief create a Ethereum Local Account when initialize
        @param alloc_balance the balance need to be alloc
        @param password encrypt password for creating new account, decrypt password for importing account
        @param keyfile content of the keystore file. If this parameter is None, this function will create a new account, if not, it will import account from keyfile
        """
        from eth_account import Account
        self.lib_eth_account = Account

        self.__account = self.__importAccount(keyfilePath=keyfilePath, password=password) if keyfilePath else self.__createAccount()
        self.__address = self.__account.address

        assert alloc_balance >= 0, "EthAccount::__init__: balance cannot have a negative value. Requested Balance Value : {}".format(alloc_balance)
            
        self.__alloc_balance = alloc_balance
        self.__password = password

        encrypted = self.encryptAccount()
        self.__keystore_content = json.dumps(encrypted)
        
        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        self.__keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]

    def __validate_balance(self, alloc_balance:int):
        """
        validate balance
        It only allow positive decimal integer
        """
        assert alloc_balance>=0 , "Invalid Balance Range: {}".format(alloc_balance)
    
    def __importAccount(self, keyfilePath: str, password = "admin"):
        """
        @brief import account from keyfile
        """
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        return self.lib_eth_account.from_key(self.lib_eth_account.decrypt(keyfile_json=keyfileContent,password=password))
    
    def __createAccount(self):
        """
        @brief create account
        """
        return  self.lib_eth_account.create()

    def getAddress(self) -> str:
        return self.__address

    def getAllocBalance(self) -> str:
        return self.__alloc_balance

    def setAllocBalance(self, balance:int):
        self.__alloc_balance = balance
        return self

    def getKeyStoreFileName(self) -> str:
        return self.__keystore_filename

    def encryptAccount(self):
        while True:
            keystore = self.lib_eth_account.encrypt(self.__account.key, password=self.__password)
            if len(keystore['crypto']['cipherparams']['iv']) == 32:
                return keystore
                
    def getKeyStoreContent(self) -> str:
        return self.__keystore_content

    def getPassword(self) -> str:
        return self.__password


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
