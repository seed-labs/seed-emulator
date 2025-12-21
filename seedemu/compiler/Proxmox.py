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
from concurrent.futures import ThreadPoolExecutor, as_completed

def upload_to_machine(machine_id, machine):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    try:
        ssh_executor.upload(
            local_path=f'output_{machine_id}/',
            remote_path=f'/home/seed/output_{machine_id}/'
        )
        return f"Machine {machine_id} ({machine['ip']}): Upload completed"
    except Exception as e:
        return f"Machine {machine_id} ({machine['ip']}): Upload failed - {str(e)}"
    finally:
        ssh_executor.close()

machine_config = json.load(open('machine_config.json'))
with ThreadPoolExecutor(max_workers=len(machine_config['machines'])) as executor:
    futures = {
        executor.submit(upload_to_machine, machine_id, machine): (machine_id, machine)
        for machine_id, machine in enumerate(machine_config['machines'])
    }
    for future in as_completed(futures):
        result = future.result()
        print(result)
"""

EXECUTOR_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def execute_on_machine(machine_id, machine):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    try:
        ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && DOCKER_BUILDKIT=0 docker compose build && docker compose up -d')
        return f"Machine {machine_id} ({machine['ip']}): Command executed successfully"
    except Exception as e:
        return f"Machine {machine_id} ({machine['ip']}): Command failed - {str(e)}"
    finally:
        ssh_executor.close()

machine_config = json.load(open('machine_config.json'))
with ThreadPoolExecutor(max_workers=len(machine_config['machines'])) as executor:
    futures = {
        executor.submit(execute_on_machine, machine_id, machine): (machine_id, machine)
        for machine_id, machine in enumerate(machine_config['machines'])
    }
    for future in as_completed(futures):
        result = future.result()
        print(result)
"""

BUILDNET_SCRIPT_TEMPLATE = """#!/usr/bin/env python3
# encoding: utf-8
from seedemu.compiler.Proxmox import SSHExecutor
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def buildnet_on_machine(machine_id, machine):
    ssh_executor = SSHExecutor(host=machine['ip'], port=machine['port'], user=machine['user'], password=machine['password'])
    try:
        ssh_executor.run_command(f'cd /home/seed/output_{machine_id}/ && chmod +x ./net.sh && ./net.sh')
        return f"Machine {machine_id} ({machine['ip']}): Buildnet completed successfully"
    except Exception as e:
        return f"Machine {machine_id} ({machine['ip']}): Buildnet failed - {str(e)}"
    finally:
        ssh_executor.close()

machine_config = json.load(open('machine_config.json'))
with ThreadPoolExecutor(max_workers=len(machine_config['machines'])) as executor:
    futures = {
        executor.submit(buildnet_on_machine, machine_id, machine): (machine_id, machine)
        for machine_id, machine in enumerate(machine_config['machines'])
    }
    for future in as_completed(futures):
        result = future.result()
        print(result)
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
    def create_ovs_bridge(self, bridge_name, comment="Created_by_Script", bridge_ip=None, bridge_cidr=24):
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
        
        # Configure bridge IP if provided
        if bridge_ip:
            self.config_bridge_ip(bridge_name, bridge_ip, bridge_cidr)
        
        print("    -> Network ready.")

    def config_bridge_ip(self, bridge_name, ip, cidr=24):
        # Configure IP address for the bridge interface
        # This allows Proxmox host to communicate with VMs on this bridge
        print(f"    -> Configuring IP address {ip}/{cidr} on bridge {bridge_name}...")
        
        # Check if IP is already configured
        try:
            result = subprocess.run(
                ["ip", "addr", "show", bridge_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if ip in result.stdout:
                print(f"    -> IP {ip}/{cidr} already configured on {bridge_name}. Skipping.")
                return
        except Exception:
            pass
        
        # Configure IP using ip command
        self._run_cmd(["ip", "addr", "add", f"{ip}/{cidr}", "dev", bridge_name])
        
        # Bring up the interface
        self._run_cmd(["ip", "link", "set", bridge_name, "up"])
        
        print(f"    -> Bridge {bridge_name} IP configured successfully.")

    # ================= VM Management =================
    def vm_exists(self, vmid):
        # Check if VM ID is already occupied
        res = self._run_cmd(["qm", "status", str(vmid)], ignore_error=True)
        return res is not None

   
    def get_next_available_vmid(self, start_from=100):
        # Get next available VM ID starting from start_from
        # List all existing VMs
        try:
            vms = self._run_cmd(["qm", "list"], ignore_error=True)
            if vms:
                # Parse VM list to get existing VMIDs
                existing_vmids = set()
                for line in vms.split('\n')[1:]:  # Skip header line
                    if line.strip():
                        parts = line.split()
                        if parts and parts[0].isdigit():
                            existing_vmids.add(int(parts[0]))
                
                # Find next available VMID
                vmid = start_from
                while vmid in existing_vmids:
                    vmid += 1
                return vmid
            else:
                return start_from
        except Exception:
            # If qm list fails, try checking sequentially
            vmid = start_from
            while self.vm_exists(vmid):
                vmid += 1
            return vmid

    def deploy_vm(self, template_id, vmid=None, name=None, 
                  storage="local-lvm", full_clone=False):
        # Clone VM
        # If vmid is None, auto-allocate next available VMID
        if vmid is None:
            vmid = self.get_next_available_vmid()
            print(f"[*] Auto-allocated VMID: {vmid}")
        
        if self.vm_exists(vmid):
            print(f"[Warn] VM {vmid} already exists. Skipping clone.")
            return False, vmid
        
        print(f"\n[*] Cloning VM {template_id} -> {vmid} ({name})...")
        cmd = [
            "qm", "clone", str(template_id), str(vmid),
            "--name", name
        ]
        if full_clone:
            cmd.extend(["--full", "1"])
            # Storage parameter is only allowed for full clones
            if storage:
                cmd.extend(["--storage", storage])
        # For linked clones, storage parameter is not allowed
            
        self._run_cmd(cmd)
        print("    -> Clone finished.")
        
        # Note: Cloud-Init reset will be done in config_cloudinit
        # to ensure it happens after all configuration is set
        
        return True, vmid

    def config_network(self, vmid, bridge, firewall=True, model="virtio"):
        # Configure VM network card to connect to specified bridge
        fw_flag = "1" if firewall else "0"
        net_conf = f"{model},bridge={bridge},firewall={fw_flag}"
        
        print(f"    -> Setting net0 to {bridge}")
        self._run_cmd([
            "qm", "set", str(vmid),
            "--net0", net_conf
        ])

    def reset_cloudinit(self, vmid):
        # Reset Cloud-Init state to ensure it runs on next boot
        # This is important for cloned VMs to apply new network configuration
        # In Proxmox, we can force Cloud-Init to run by toggling the ciupgrade option
        print(f"    -> Ensuring Cloud-Init will run on next boot...")
        try:
            # Method 1: Try using pvesh to reset Cloud-Init (Proxmox 7.0+)
            # This clears the Cloud-Init status so it runs again
            result = subprocess.run(
                ["pvesh", "create", f"/nodes/localhost/qemu/{vmid}/cloudinit", "reset"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"    -> Cloud-Init reset successful.")
                return
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Method 2: Force Cloud-Init to regenerate by toggling a setting
        # This ensures Cloud-Init runs on next boot
        try:
            # Get current ciupgrade value
            current_config = self._run_cmd(["qm", "config", str(vmid)], ignore_error=True)
            if current_config:
                # Toggle ciupgrade to force Cloud-Init refresh
                # First check if it's set
                has_ciupgrade = "ciupgrade:" in current_config or "ciupgrade: 1" in current_config
                if not has_ciupgrade:
                    # Set ciupgrade to enable Cloud-Init upgrade/refresh
                    self._run_cmd(["qm", "set", str(vmid), "--ciupgrade", "1"], ignore_error=True)
        except Exception:
            pass
        
        print(f"    -> Cloud-Init will run on next boot.")

    def config_cloudinit(self, vmid, ip, gw, user, password, nameserver=None):
        # Inject Cloud-Init configuration: IP, gateway, username, password
        print(f"    -> Injecting Cloud-Init (IP: {ip}, User: {user})")
        
        # Ensure Cloud-Init is enabled
        self._run_cmd([
            "qm", "set", str(vmid),
            "--agent", "enabled=1"
        ])
        
        cmd = [
            "qm", "set", str(vmid),
            "--ipconfig0", f"ip={ip}/24,gw={gw}",
            "--ciuser", user,
            "--cipassword", password
        ]
        
        # Format nameserver: if multiple DNS servers provided (comma-separated), convert to space-separated
        if nameserver:
            # Convert comma-separated to space-separated for Proxmox
            dns_servers = nameserver.replace(',', ' ').strip()
            cmd.extend(["--nameserver", dns_servers])
        
        # Execute the command to set Cloud-Init configuration
        self._run_cmd(cmd)
        
        # Clear any existing SSH keys to allow password authentication
        # Use --delete to remove SSH keys instead of setting empty string
        try:
            self._run_cmd([
                "qm", "set", str(vmid),
                "--delete", "sshkeys"
            ], ignore_error=True)
        except Exception:
            # If deletion fails, it's okay - SSH keys may not exist
            pass
        
        # Reset Cloud-Init to ensure it runs on next boot
        print(f"    -> Resetting Cloud-Init state...")
        self.reset_cloudinit(vmid)

    def start_vm(self, vmid, wait_for_cloudinit=True, wait_timeout=180):
        # Start VM
        # Check status
        status_out = self._run_cmd(["qm", "status", str(vmid)])
        if "status: running" in status_out:
            print(f"    -> VM {vmid} is already running.")
            if wait_for_cloudinit:
                print(f"    -> Checking Cloud-Init status...")
                self._wait_for_cloudinit(vmid, wait_timeout)
            return
        print(f"    -> Starting VM {vmid}...")
        self._run_cmd(["qm", "start", str(vmid)])