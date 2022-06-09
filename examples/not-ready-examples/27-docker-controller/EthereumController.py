#!/usr/bin/env python3
# encoding: utf-8

from DockerController import *

ETHServerCommandTemplates: Dict[str, str] = {}
ETHServerCommandTemplates['get_account'] = '''\
geth attach --exec 'eth.accounts[0]'
'''
ETHServerCommandTemplates['get_balance'] = '''\
geth attach --exec 'eth.getBalance({})'
'''

ETHServerCommandTemplates['unlock_account'] = '''\
geth attach --exec 'personal.unlockAccount({account}, "{password}")'
'''


class EthereumController(DockerController): 

    def __init__(self):
        super().__init__()

    def getEthereumServerById(self):

        return ""

    def getEthereumContainersByVnodeId(self):
        return ""

    def getEthContainers(self):
        return self.getContainersByClassName('EthereumService')

    def getAccount(self, container):
        return self.executeCommandInContainer(container, ETHServerCommandTemplates['get_account'])

    def getBalanceByContainer(self, container):
        account = self.getAccount(container)
        return self.getBalanceByAccount(container, account)

    def getBalanceByAccount(self, container, account):
        return self.executeCommandInContainer(container, ETHServerCommandTemplates['get_balance'].format(account))

    def unlockAccount(self, container, account, password="admin"):
        return self.executeCommandInContainer(container, 
                    ETHServerCommandTemplates['unlock_account']
                                    .format(account=account, password=password))

    
class EthereumServer:
    
