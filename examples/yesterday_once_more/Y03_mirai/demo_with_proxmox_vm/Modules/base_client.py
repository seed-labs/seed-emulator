import os
import time
import logging
import requests
import random
import string
from typing import Dict, Any, Optional
from filelock import FileLock

class ProxmoxAPIError(Exception):
    """!
    @brief Proxmox API Exception Class
    """
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

    def to_json(self):
        import json
        return json.dumps({
            "success": False,
            "error": str(self),
            "detail": self.details
        })

class ProxmoxClient:
    """!
    @brief Proxmox API Client Base Class
    @details Provide basic API access and logging
    """

    def __init__(self, pve_host: str, node: str, api_token_id: str, api_token_secret: str, log_file: str = None):
        """!
        @brief Initialize Proxmox API Client
        @param pve_host: Proxmox Host Address (e.g., "https://pve.example.com:8006")
        @param node: Proxmox Node Name
        @param api_token_id: API Token ID
        @param api_token_secret: API Token Secret
        @param log_file: Log File Path (optional, default to class name.log)
        @details Initialize Proxmox API Client
        """
        import warnings
        warnings.filterwarnings("ignore")
        
        self.base_url = f"{pve_host}/api2/json"
        self.node = node
        self.headers = {"Authorization": f"PVEAPIToken={api_token_id}={api_token_secret}"}
        self.pve_host = pve_host
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        
        self._setup_logging(log_file or f"{self.__class__.__name__}.log")

    def _setup_logging(self, log_file: str):
        """!
        @brief Setup Logging
        @param log_file: Log File Path
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file_path = os.path.join(script_dir, log_file)
        self.log_lock_path = self.log_file_path + ".lock"
        
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(message)s')

    def write_log(self, message: str):
        """!
        @brief Write Log Safely
        @param message: Log Message
        """
        with FileLock(self.log_lock_path, timeout=10):
            fh = logging.FileHandler(self.log_file_path, encoding='utf-8')
            fh.setFormatter(self.formatter)
            self.logger.addHandler(fh)
            self.logger.info(message)
            self.logger.removeHandler(fh)
            fh.close()

    def api_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """!
        @brief Send API Request and Process Response
        @param method: HTTP Method (GET, POST, PUT, DELETE)
        @param endpoint: API Endpoint (e.g., "/nodes/{node}/qemu")
        @param data: Request Data
        @return: API Response Data
        @throws ProxmoxAPIError: If Request Failed or Response Format Error
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, data=data)
            response.raise_for_status()
            
            json_response = response.json()
            
            # Some APIs may return empty data on success
            if method == "POST" and endpoint.endswith(("/start", "/stop", "/shutdown")):
                return json_response.get("data")

            # Check for standard data field
            if "data" not in json_response:
                raise ProxmoxAPIError("API Response Format Error, Missing 'data' Field", details=response.text)

            return json_response["data"]

        except requests.exceptions.RequestException as e:
            error_details = e.response.text if hasattr(e, 'response') and e.response else str(e)
            raise ProxmoxAPIError(f"API Request Failed: {e}", details=error_details)

    def wait_for_task(self, upid: str):
        """!
        @brief Wait for Proxmox Task to Complete
        @param upid: Task ID
        @throws ProxmoxAPIError: If Task Failed
        """
        endpoint = f"/nodes/{self.node}/tasks/{upid}/status"
        self.write_log(f"⏳ Waiting for Task {upid} to Complete...")
        
        max_attempts = 120  # 6 Minutes (120 * 3 Seconds)
        attempt = 0
        
        while attempt < max_attempts:
            try:
                task_status = self.api_request("GET", endpoint)
                if task_status.get("status") == "stopped":
                    if task_status.get("exitstatus") == "OK":
                        self.write_log(f"✅ Task {upid} Completed Successfully")
                        return
                    else:
                        raise ProxmoxAPIError(f"Task Failed: {task_status.get('exitstatus')}", details=task_status)
            except ProxmoxAPIError as e:
                # When task is not found, it may be removed from task list
                if "no such task" in str(e) or "task does not exist" in str(e):
                    self.write_log(f"✅ Task {upid} Completed (Removed from Task List)")
                    return
                raise

            attempt += 1
            time.sleep(3)
            
        raise ProxmoxAPIError(f"Waiting for Task {upid} to Complete Timeout", details={"upid": upid})

    @staticmethod
    def generate_random_string(length: int, chars: str = None) -> str:
        """!
        @brief Generate Random String
        @param length: String Length
        @param chars: Characters to use (default to letters and digits)
        @return Generated String
        """
        if chars is None:
            chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))
