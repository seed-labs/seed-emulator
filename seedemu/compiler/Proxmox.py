import paramiko
import os

FILE_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json
machine_config = json.load(open('machine_config.json'))
for machine_id, machine in enumerate(machine_config['machines']):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    try:
        ssh_executor.upload(
            local_path=f'output_{machine_id}/',
            remote_path=f'/home/seed/output_{machine_id}/'
        )
    finally:
        ssh_executor.close()
"""

EXECUTOR_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json

machine_config = json.load(open('machine_config.json'))
for machine_id, machine in enumerate(machine_config['machines']):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && DOCKER_BUILDKIT=0 docker compose build && docker compose up')
"""

BUILDNET_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json

machine_config = json.load(open('machine_config.json'))
for machine_id, machine in enumerate(machine_config['machines']):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && ./net.sh')
"""

class SSHExecutor:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._client = None

    def _get_client(self):
        if self._client is None or not self._client.get_transport().is_active():
            print(f"Connecting to {self.user}@{self.host}:{self.port}...")
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(self.host, port=self.port, username=self.user, password=self.password)
        return self._client

    def run_command(self, command):
        client = self._get_client()
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        print(f"--- Command Output from {self.host} ---")
        if output:
            print(output)
        if error:
            print(f"--- Command Error from {self.host} ---")
            print(error)
            
        return output, error

    def upload(self, local_path, remote_path):
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            if os.path.isdir(local_path):
                print(f"Uploading directory '{local_path}' to '{remote_path}'...")
                self._upload_directory(sftp, local_path, remote_path)
            elif os.path.isfile(local_path):
                print(f"Uploading file '{local_path}' to '{remote_path}'...")
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    sftp.mkdir(remote_dir)
                sftp.put(local_path, remote_path)
            else:
                raise ValueError(f"Local path '{local_path}' is not a valid file or directory.")
            print("Upload complete.")
            return True
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
        finally:
            sftp.close()
    def _upload_directory(self, sftp, local_path, remote_path):
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            print(f"Creating remote directory: {remote_path}")
            sftp.mkdir(remote_path)
        for item in os.listdir(local_path):
            local_item_path = os.path.join(local_path, item)
            remote_item_path = os.path.join(remote_path, item).replace('\\', '/')
            if os.path.isdir(local_item_path):
                self._upload_directory(sftp, local_item_path, remote_item_path)
            elif os.path.isfile(local_item_path):
                print(f"  Uploading {local_item_path} -> {remote_item_path}")
                sftp.put(local_item_path, remote_item_path)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            print(f"Connection to {self.host} closed.")

class ScriptGenerator:
    def generate(self, script_type: str):
        if script_type == 'file':
            return FILE_SCRIPT_TEMPLATE
        elif script_type == 'executor':
            return EXECUTOR_SCRIPT_TEMPLATE
        elif script_type == 'buildnet':
            return BUILDNET_SCRIPT_TEMPLATE
        else:
            raise ValueError(f'Invalid script type: {script_type}')