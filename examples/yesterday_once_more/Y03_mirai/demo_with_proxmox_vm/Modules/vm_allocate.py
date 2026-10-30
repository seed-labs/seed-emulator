import datetime
import time
from typing import Dict, Any

from base_client import ProxmoxClient, ProxmoxAPIError

class VMAllocate(ProxmoxClient):
    """
    @brief Class for Creating and Managing Proxmox Virtual Machines
    """
    
    def __init__(self, pve_host: str, node: str, api_token_id: str, api_token_secret: str):
        """!
        @brief VM Allocate Constructor
        @param pve_host: Proxmox VE Host
        @param node: Node Name
        @param api_token_id: API Token ID
        @param api_token_secret: API Token Secret
        """
        super().__init__(pve_host, node, api_token_id, api_token_secret, log_file="VMAllocate.log")

        self.last_cloned_vm = None
        self.last_created_snapshot = None

    def clone_vm(self, template_vmid: int, new_vmid: int, new_vm_name: str, full_clone: bool = False) -> Dict[str, Any]:
        """!
        @brief Clone VM
        @param template_vmid: Template VM ID
        @param new_vmid: New VM ID
        @param new_vm_name: New VM Name
        @param full_clone: Full Clone (Default: False)
        @returns: VM Info Dictionary
        @raises ProxmoxAPIError: If VM Clone Failed
        """
        self.write_log(f"🚀 From templated VM {template_vmid} clone new VM {new_vmid} (name: {new_vm_name})")
        
        # Prepare request data
        clone_data = {
            "newid": new_vmid,
            "name": new_vm_name,
            "full": 1 if full_clone else 0
        }
        
        # Send clone request
        endpoint = f"/nodes/{self.node}/qemu/{template_vmid}/clone"
        upid = self.api_request("POST", endpoint, data=clone_data)
        
        # Wait for task completion
        self.wait_for_task(upid)
        
        # Record success status
        self.write_log(f"✅ VM {new_vmid} ({new_vm_name}) clone success")
        
        # Save VM information
        self.last_cloned_vm = {
            "vmid": new_vmid,
            "name": new_vm_name,
            "template_vmid": template_vmid,
            "creation_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return self.last_cloned_vm

    def start_vm(self, vmid: int, wait_for_status: bool = True, timeout: int = 120) -> bool:
        """!
        @brief Start VM
        @param vmid: VM ID
        @param wait_for_status: Wait for Status (Default: True)
        @param timeout: Timeout (Default: 120)
        @returns: True if VM Started
        @raises ProxmoxAPIError: If VM Start Failed
        """
        self.write_log(f"⚡️ Starting VMID {vmid}...")
        
        # Send start request
        start_endpoint = f"/nodes/{self.node}/qemu/{vmid}/status/start"
        self.api_request("POST", start_endpoint)
        
        if wait_for_status:
            status_endpoint = f"/nodes/{self.node}/qemu/{vmid}/status/current"
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                vm_status = self.api_request("GET", status_endpoint)
                if vm_status.get("status") == "running":
                    self.write_log(f"✅ VM {vmid} started")
                    return True
                time.sleep(3)
                
            raise ProxmoxAPIError(f"Waiting VM {vmid} Start Timeout", 
                                  details={"vmid": vmid, "timeout": timeout})
        
        self.write_log(f"⏳ VM {vmid} start command sent (without waiting)")
        return True

    def create_snapshot(self, vmid: int, snapname: str = None, description: str = None) -> Dict[str, Any]:
        """!
        @brief Create Snapshot
        @param vmid: VM ID
        @param snapname: Snapshot Name (Default: None)
        @param description: Snapshot Description (Default: None)
        @returns: Snapshot Info Dictionary
        """
        # Generate snapshot name if not provided
        if not snapname:
            now = datetime.datetime.now()
            snapname = now.strftime("snap_%Y%m%d_%H%M%S")
            
        if not description:
            description = f"Auto Created Snapshot - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        self.write_log(f"📸 Create Snapshot {snapname} for VM {vmid}...")
        
        # Prepare request data
        snapshot_data = {
            "snapname": snapname,
            "description": description
        }
        
        # Send create snapshot request
        endpoint = f"/nodes/{self.node}/qemu/{vmid}/snapshot"
        upid = self.api_request("POST", endpoint, data=snapshot_data)
        
        # Wait for task completion
        self.wait_for_task(upid)
        
        self.write_log(f"✅ Snapshot {snapname} for VM {vmid} created")
        
        # Save snapshot information
        self.last_created_snapshot = {
            "vmid": vmid,
            "snapshot_name": snapname,
            "description": description,
            "creation_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return self.last_created_snapshot

    def get_vm_ip_and_prefix(self, vmid, wait_timeout=60):
        """
        @brief Get VM IP Address and Prefix
        @param vmid: VM ID
        @param wait_timeout: Timeout (seconds)
        @return: IP address string and prefix, None if not found
        """
        self.write_log(f"🔍 Getting IP address and prefix for VM {vmid}...")
        endpoint = f"/nodes/{self.node}/qemu/{vmid}/agent/network-get-interfaces"
        start_time = time.time()
        while True:
            try:
                resp = self.api_request("GET", endpoint)
                result = resp.get('result')
                if not result:
                    raise Exception("No IP address found")
                for iface in result:
                    if 'ip-addresses' not in iface:
                        continue
                    for ipinfo in iface['ip-addresses']:
                        if (ipinfo['ip-address-type'] == 'ipv4' and 
                            not ipinfo['ip-address'].startswith("127.") and
                            not ipinfo['ip-address'].startswith("169.")):
                            ip = ipinfo['ip-address']
                            prefix = ipinfo.get('prefix', None)
                            return (ip, prefix)
            except Exception:
                pass
            if time.time() - start_time > wait_timeout:
                return None
            time.sleep(3)

    def shutdown_vm(self, vmid: int, wait_for_status: bool = True, timeout: int = 120) -> bool:
        """
        @brief Shutdown VM
        @param vmid: VM ID
        @param wait_for_status: Whether to wait for shutdown complete
        @param timeout: Timeout in seconds
        @returns: True if shutdown success
        @raises ProxmoxAPIError: If shutdown fails
        """
        self.write_log(f"⚡️ Shutting down VMID {vmid} ...")
        shutdown_endpoint = f"/nodes/{self.node}/qemu/{vmid}/status/shutdown"
        try:
            self.api_request("POST", shutdown_endpoint)
        except ProxmoxAPIError as e:
            if "VM is not running" in str(e) or "already stopped" in str(e):
                self.write_log(f"ℹ️ VM {vmid} already powered off.")
                return True
            raise
        
        if wait_for_status:
            status_endpoint = f"/nodes/{self.node}/qemu/{vmid}/status/current"
            start_time = time.time()
            while time.time() - start_time < timeout:
                vm_status = self.api_request("GET", status_endpoint)
                if vm_status.get("status") == "stopped":
                    self.write_log(f"✅ VM {vmid} shutdown complete")
                    return True
                time.sleep(3)
            raise ProxmoxAPIError(f"Waiting VM {vmid} Shutdown Timeout", details={"vmid": vmid, "timeout": timeout})
        else:
            self.write_log(f"⏳ VM {vmid} shutdown command sent (without waiting)")
            return True

    def delete_vm(self, vmid: int, timeout: int = 180) -> bool:
        """
        @brief Delete a QEMU virtual machine (with Proxmox API)
        @param vmid: VM ID to be deleted
        @param timeout: Timeout in seconds for task completion (default 180)
        @returns: True if deleted successfully
        @raises ProxmoxAPIError: If deletion fails
        """
        self.write_log(f"🗑️ Attempting to delete VM {vmid} ...")
        try:
            self.shutdown_vm(vmid)
        except Exception as e:
            self.write_log(f"⚠️ Failed to shutdown VM {vmid} before delete: {e}")
        endpoint = f"/nodes/{self.node}/qemu/{vmid}"
        try:
            upid = self.api_request("DELETE", endpoint)
            if not upid:
                raise ProxmoxAPIError("No UPID returned for VM deletion", details={"vmid": vmid})
            self.wait_for_task(upid)
            self.write_log(f"✅ Successfully deleted VM {vmid}")
            return True
        except ProxmoxAPIError as e:
            if "404" in str(e) or "does not exist" in str(e):
                self.write_log(f"⚠️ VM {vmid} does not exist (already deleted).")
                return True
            self.write_log(f"🔥 Failed to delete VM {vmid}: {e}")
            raise