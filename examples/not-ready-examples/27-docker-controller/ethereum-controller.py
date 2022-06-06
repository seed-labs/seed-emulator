#!/usr/bin/env python3
# encoding: utf-8

from EthereumController import *

controller = EthereumController()
ethContainers = controller.getEthContainers()
'''
ethServers = controller.getEthServers()
ethServers[0].getAccount()
'''
account0 = controller.getAccount(ethContainers[0])
balance0 = controller.getBalanceByContainer(ethContainers[0])
unlock = controller.unlockAccount(ethContainers[0], account0, "admin")


print(ethContainers)
print(account0)
print(balance0)
print(unlock)