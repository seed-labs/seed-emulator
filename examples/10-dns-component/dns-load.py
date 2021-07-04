from seedemu.core import Emulator
from seedemu.services import DomainNameService

emu = Emulator()
emu.load('dns-component.bin')

dns: DomainNameService = emu.getLayer('DomainNameService')

print(dns.getZoneServerNames('.'))               # => ['root_server']
print(dns.getZoneServerNames('com.'))            # => ['com_server']
print(dns.getZoneServerNames('net.'))            # => ['net_server']
print(dns.getZoneServerNames('example.com.'))    # => ['example_com_server']
