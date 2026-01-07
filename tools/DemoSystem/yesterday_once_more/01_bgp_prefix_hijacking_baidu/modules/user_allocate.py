from re import L
import time
import datetime
import string
from typing import Dict, Any
from base_client import ProxmoxClient, ProxmoxAPIError

class UserAllocate(ProxmoxClient):
    """!
    @brief User Allocate
    @details Class for creating and managing Proxmox users
    """
    
    BASE_USERNAME_PREFIX = "user"
    DEFAULT_USER_ROLE = "PVEVMUser"

    def __init__(self, pve_host: str, node: str, api_token_id: str, api_token_secret: str):
        """!
        @brief User Allocate Constructor
        @param pve_host: Proxmox VE Host
        @param node: Node Name
        @param api_token_id: API Token ID
        @param api_token_secret: API Token Secret
        """
        super().__init__(pve_host, node, api_token_id, api_token_secret, log_file="UserAllocate.log")
        self.last_created_user = None

    def create_user(self, username_len: int = 6, password_len: int = 12, random: bool = True) -> Dict[str, Any]:
        """!
        @brief Create User
        @param expire_minutes: User Expire Minutes
        @param username_len: Username Random Part Length
        @param password_len: Password Length
        @param random: Generate random username and password (default: True)
        @returns: User Info Dictionary
        """
        if random:
            # Generate random username and password
            username_suffix = self.generate_random_string(username_len, string.ascii_lowercase + string.digits)
            username = f"{self.BASE_USERNAME_PREFIX}_{username_suffix}@pve"
            
            password_chars = string.ascii_letters + string.digits + "!@#$%^&*"
            password = self.generate_random_string(password_len, password_chars)
        else:
            return {"username": "seed@pve", "password": "seed1234"}

        # Create user data
        user_data = {
            "userid": username,
            "password": password,
            "enable": 1,
            "comment": f"Created by API on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        }
        
        # Create user
        self.api_request("POST", "/access/users", data=user_data)
        
        # Record user info (password hidden in log)
        self.write_log(f"✅ Created User: {username} / Password: {password}")
        
        # Save user info
        self.last_created_user = {
            "username": username,
            "password": password,
        }
        
        return self.last_created_user

    def grant_vm_access(self, vmid: int, username: str = None, role: str = None) -> bool:
        """!
        @brief Grant VM Access
        @details Grants user access to a specific virtual machine
        @param vmid: Virtual Machine ID
        @param username: Username to grant access (default: last created user)
        @param role: Role to assign (default: class constant)
        @returns: True if successful
        @throws ValueError: If no valid username is provided
        @throws ProxmoxAPIError: If API request fails
        """
        # Use provided username or last created user
        if not username and not self.last_created_user:
            raise ValueError("No valid username provided, and no last created user")
            
        effective_username = username or self.last_created_user["username"]
        effective_role = role or self.DEFAULT_USER_ROLE
        
        self.write_log(f"🔑 Granting access to user {effective_username} for VMID {vmid} (role: {effective_role})...")
        
        # Prepare ACL data
        acl_data = {
            "path": f"/vms/{vmid}",
            "users": effective_username,
            "roles": effective_role,
            "propagate": 0
        }
        
        # Send API request
        self.api_request("PUT", "/access/acl", data=acl_data)
        self.write_log(f"✅ Successfully granted access to user {effective_username} for VMID {vmid}")
        
        return True

    def delete_user(self, vmid: int) -> bool:
        """!
        @brief Delete user from Proxmox
        @param username: Username to delete (should include @pve)
        @returns: True if deleted successfully or already not exist
        @raises ProxmoxAPIError: If deletion fails unexpectedly
        """
        associated_user = None
        endpoint = f"/access/acl"
        data = self.api_request("GET", endpoint)
        vm_path = f"/vms/{vmid}"
        for acl in data:
            if acl.get("path") == vm_path and "@pve" in acl.get("ugid", ""):
                associated_user = acl["ugid"]
                break
        
        if associated_user:
            self.write_log(f"🗑️ Attempting to delete user: {associated_user} ...")
            endpoint = f"/access/users/{associated_user}"
            try:
                self.api_request("DELETE", endpoint)
                self.write_log(f"✅ Successfully deleted user: {associated_user}")
                return True
            except ProxmoxAPIError as e:
                if "404" in str(e) or "does not exist" in str(e):
                    self.write_log(f"⚠️ User {associated_user} does not exist (already deleted).")
                    return True
                self.write_log(f"🔥 Failed to delete user {associated_user}: {e}")
        else:
            self.write_log(f"⚠️ No user found for VM {vmid}.")
            return False