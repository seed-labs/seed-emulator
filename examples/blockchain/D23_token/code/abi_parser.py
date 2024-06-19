#!/bin/env python3

import os, json, logging, socket
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper
from lib.UtilityServerHelper import UtilityServerHelper

##############################################
# Import global variables related to the emulator
from emulator_setup import *

CONTRACT = '../contract/SEEDToken20'
##############################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


with open(CONTRACT + '.abi', 'r') as f:
    data = json.load(f) 

arglist = []
for item in data:
    #print(item)
    type_ = item['type']

    if type_ == 'constructor':
       print("Name: constructor")
       print("StateMutability: " + item['stateMutability'])
       for arg in item['inputs']:
           s = arg['type'] + " " + arg['name']
           print("Argument: " + s)

    elif type_ == 'function':
       print("Name: " + item['name'])
       print("StateMutability: " + item['stateMutability'])

       for arg in item['inputs']:
           s = arg['type'] + " " + arg['name']
           print("Argument: " + s)

       for out in item['outputs']:
           s = out['type'] + " " + out['name']
           print("Output: " + s)

    print("---------------------------------")
