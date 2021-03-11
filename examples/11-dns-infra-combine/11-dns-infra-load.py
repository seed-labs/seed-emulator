from seedsim.core import Simulator
from seedsim.services import DomainNameService

sim = Simulator()
sim.load('dns-dump.bin')

dns: DomainNameService = sim.getLayer('DomainNameService')

print(dns.getZoneServerNames('.'))               # => ['root_server']
print(dns.getZoneServerNames('com.'))            # => ['com_server']
print(dns.getZoneServerNames('net.'))            # => ['net_server']
print(dns.getZoneServerNames('example.com.'))    # => ['example_com_server']