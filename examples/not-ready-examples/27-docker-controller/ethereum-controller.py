#!/usr/bin/env python3
# encoding: utf-8

from EthereumController import *

controller = EthereumController()
ethContainers = controller.getEthereumContainers()
'''
ethServers = controller.getEthServers()
ethServers[0].getAccount()
'''
account0 = ethContainers[0].getAccount()
balance0 = ethContainers[0].getBalanceByAccount(account0)
unlock = ethContainers[0].unlockAccount(account0, "admin")


print(ethContainers)
print(account0)
print(balance0)
print(unlock)