import time
import sys
import subprocess
import json
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
    ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && DOCKER_BUILDKIT=0 docker compose build && docker compose up -d')
"""

BUILDNET_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json

machine_config = json.load(open('machine_config.json'))
for machine_id, machine in enumerate(machine_config['machines']):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && chmod +x ./net.sh && ./net.sh')
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
        print(f"Running command: {command} on {self.host}")
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

class Proxmox:
    def __init__(self):
        # Check if 'qm' command is available
        try:
            subprocess.run(["which", "qm"], check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("[Error] 'qm' command not found. Are you running this on the Proxmox host?")
            sys.exit(1)

    def _run_cmd(self, cmd, ignore_error=False, return_json=False):
        # Execute command and return output
        cmd_str = " ".join(cmd)
        print(f"[Exec] {cmd_str}")
        try:
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            output = result.stdout.strip()
            if return_json and output:
                return json.loads(output)
            return output
        except subprocess.CalledProcessError as e:
            if ignore_error:
                return None
            print(f"[Error] Command failed: {cmd_str}")
            print(f"       {e.stderr.strip()}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"[Error] Failed to decode JSON from: {cmd_str}")
            sys.exit(1)
            
    # ================= Network Management =================
    def create_ovs_bridge(self, bridge_name, comment="Created_by_Script"):
        # Check if OVS bridge already exists
        print(f"\n[*] Checking network bridge: {bridge_name}")
        
        # Get network interface list
        networks = self._run_cmd(
            ["pvesh", "get", "/nodes/localhost/network", "--output-format", "json"],
            return_json=True
        )
        
        # Check if bridge already exists
        for net in networks:
            if net.get('iface') == bridge_name:
                print(f"    -> Bridge '{bridge_name}' already exists. Skipping.")
                return
        print(f"    -> Creating OVS Bridge '{bridge_name}'...")
        self._run_cmd([
            "pvesh", "create", "/nodes/localhost/network",
            "--iface", bridge_name,
            "--type", "OVSBridge",
            "--autostart", "1",
            "--comments", comment
        ])
        print("    -> Applying network configuration (ifreload)...")
        # Apply network configuration
        self._run_cmd(["pvesh", "set", "/nodes/localhost/network"])
        
        # Wait for network to stabilize
        print("    -> Waiting for network to stabilize...")
        time.sleep(5)
        print("    -> Network ready.")

    # ================= VM Management =================
    def vm_exists(self, vmid):
        # Check if VM ID is already occupied
        res = self._run_cmd(["qm", "status", str(vmid)], ignore_error=True)
        return res is not None

    def deploy_vm(self, template_id, vmid, name, 
                  storage="local-lvm", full_clone=True):
        # Clone VM
        if self.vm_exists(vmid):
            print(f"[Warn] VM {vmid} already exists. Skipping clone.")
            return False
        print(f"\n[*] Cloning VM {template_id} -> {vmid} ({name})...")
        cmd = [
            "qm", "clone", str(template_id), str(vmid),
            "--name", name
        ]
        if full_clone:
            cmd.extend(["--full", "1"])
        if storage:
            cmd.extend(["--storage", storage])
            
        self._run_cmd(cmd)
        print("    -> Clone finished.")
        return True

    def config_network(self, vmid, bridge, firewall=True, model="virtio"):
        # Configure VM network card to connect to specified bridge
        fw_flag = "1" if firewall else "0"
        net_conf = f"{model},bridge={bridge},firewall={fw_flag}"
        
        print(f"    -> Setting net0 to {bridge}")
        self._run_cmd([
            "qm", "set", str(vmid),
            "--net0", net_conf
        ])

    def config_cloudinit(self, vmid, ip, gw, user, password, nameserver=None):
        # Inject Cloud-Init configuration: IP, gateway, username, password
        print(f"    -> Injecting Cloud-Init (IP: {ip}, User: {user})")
        
        cmd = [
            "qm", "set", str(vmid),
            "--ipconfig0", f"ip={ip}/24,gw={gw}",
            "--ciuser", user,
            "--cipassword", password
        ]
        
        if nameserver:
            cmd.extend(["--nameserver", nameserver])
            
        self._run_cmd(cmd)

    def start_vm(self, vmid):
        # Start VM
        # Check status
        status_out = self._run_cmd(["qm", "status", str(vmid)])
        if "status: running" in status_out:
            print(f"    -> VM {vmid} is already running.")
            return
        print(f"    -> Starting VM {vmid}...")
        self._run_cmd(["qm", "start", str(vmid)])