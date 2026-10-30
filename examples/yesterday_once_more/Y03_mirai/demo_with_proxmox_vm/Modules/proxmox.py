from vmnode import VMNode
from ssh_executor import SSHExecutor
from vm_allocate import VMAllocate
from seedemu import *
import os
import shutil

GLOBAL_ENV_TEMPLATE = '''\
PVE_HOST={PVE_HOST}
API_TOKEN_ID={API_TOKEN_ID}
API_TOKEN_SECRET={API_TOKEN_SECRET}
NODE={NODE}
'''

class Proxmox:

    cur_vmid: int
    Registry: Dict[int, VMNode]

    PVE_HOST: str
    API_TOKEN_ID: str
    API_TOKEN_SECRET: str
    NODE: str

    def __init__(self, pve_host: str, api_token_id: str, api_token_secret: str, node: str, start_vmid: int = 300):
        self.cur_vmid = start_vmid
        self.PVE_HOST = pve_host
        self.API_TOKEN_ID = api_token_id
        self.API_TOKEN_SECRET = api_token_secret
        self.NODE = node
        self.Registry = {}

    def createVM(self, asn: int, vmbase: str) -> VMNode:
        vm = VMNode(asn, self.cur_vmid, vmbase)
        self.Registry[vm.vmid] = vm

        self.cur_vmid += 1
        return vm

    def generateAllScript(self, output_dir, script_name, subscript_name):
        sh_path = os.path.join(output_dir, script_name)
        with open(sh_path, "w") as f:
            f.write("#!/bin/bash\n\n")
            for subdir in sorted(os.listdir(output_dir)):
                sub_path = os.path.join(output_dir, subdir)
                script_path = os.path.join(subdir, subscript_name)
                if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, subscript_name)):
                    f.write(f'echo "Running {script_path}"\n')
                    f.write(f'python "{script_path}"\n')
        os.chmod(sh_path, 0o755)

    def compile(self, output_dir: str):
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        with open(os.path.join(output_dir, "global.env"), "w") as f:
            f.write(GLOBAL_ENV_TEMPLATE.format(
                PVE_HOST=self.PVE_HOST,
                API_TOKEN_ID=self.API_TOKEN_ID,
                API_TOKEN_SECRET=self.API_TOKEN_SECRET,
                NODE=self.NODE,
            ))

        for vm in self.Registry.values():
            vm.generateVMConfig(output_dir)

        self.generateAllScript(output_dir, "vm_buildup.sh", "start.py")
        self.generateAllScript(output_dir, "vm_down.sh", "down.py")