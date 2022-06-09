#!/usr/bin/env python3
# encoding: utf-8
from __future__ import annotations
from DockerController import *
from docker.models.containers  import *

ETHServerCommandTemplates: Dict[str, str] = {}
ETHServerCommandTemplates['get_account'] = '''\
geth attach --exec 'eth.accounts[{}]'
'''
ETHServerCommandTemplates['get_balance'] = '''\
geth attach --exec 'eth.getBalance({})'
'''

ETHServerCommandTemplates['unlock_account'] = '''\
geth attach --exec 'personal.unlockAccount({account}, "{password}")'
'''
ETHServerCommandTemplates['custom_geth_command'] = '''\
geth attach --exec '{}'    
'''

class EthereumController(DockerController): 

    def __init__(self):
        super().__init__()

    def getContainerById(self, id) -> EthereumContainer:
        return EthereumContainer(self._getContainerById(id))

    def getContainersByClassName(self, className:str) -> List[EthereumContainer]:
        return list(map(EthereumContainer, self._getContainersByClassName(className)))

    def getEthereumContainers(self) -> List[EthereumContainer]:
        return self.getContainersByClassName('EthereumService')

    
class EthereumContainer(DockerContainer):
    

    def getAccount(self, index:int = 0):
        return self.executeCommand(ETHServerCommandTemplates['get_account'].format(index))

    def getBalanceByAccount(self, account):
        return self.executeCommand(ETHServerCommandTemplates['get_balance'].format(account))

    def unlockAccount(self, account, password="admin"):
        return self.executeCommand( 
                    ETHServerCommandTemplates['unlock_account']
                                    .format(account=account, password=password))

    def executeGethCommand(self, gethCmd:str) -> str:
        return self.executeCommand(ETHServerCommandTemplates['custom_geth_command'].format(gethCmd))
    
