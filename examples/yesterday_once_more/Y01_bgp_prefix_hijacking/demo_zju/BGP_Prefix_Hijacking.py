from seedemu import *
import large_internet 
from proxmox import Proxmox
import os, sys
from dotenv import load_dotenv

script_name = os.path.basename(__file__)

if len(sys.argv) == 1:
    platform = Platform.AMD64
elif len(sys.argv) == 2:
    if sys.argv[1].lower() == 'amd':
        platform = Platform.AMD64
    elif sys.argv[1].lower() == 'arm':
        platform = Platform.ARM64
    else:
        print(f"Usage:  {script_name} amd|arm")
        sys.exit(1)
else:
    print(f"Usage:  {script_name} amd|arm")
    sys.exit(1)

emu = Emulator()
ovpn = OpenVpnRemoteAccessProvider()

emu.load('./large_internet.bin')
base = emu.getLayer('Base')

as153 = base.getAutonomousSystem(153)
as153.getNetwork("net0").enableRemoteAccess(ovpn)

emu.render()

docker = Docker(platform=platform)
emu.compile(docker, './output', override=True)

# === Configuration ===
load_dotenv()
PVE_HOST = os.getenv('PVE_HOST')
API_TOKEN_ID = os.getenv('API_TOKEN_ID')
API_TOKEN_SECRET = os.getenv('API_TOKEN_SECRET')
NODE = os.getenv('NODE')

pm = Proxmox(PVE_HOST, API_TOKEN_ID, API_TOKEN_SECRET, NODE)
pm.createVM(153, "129").joinNetwork("net0", base)
pm.compile('./output_vm')