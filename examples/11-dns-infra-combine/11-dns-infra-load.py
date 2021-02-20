from seedsim.core import Simulator
from seedsim.services import DomainNameService

sim = Simulator()
sim.load('dns-dump.bin')

dns: DomainNameService = sim.getLayer('DomainNameService')

print(dns.getZoneServerName('.'))               # => [('root_server', 150)]
print(dns.getZoneServerName('com.'))            # => [('com_server', 151)]
print(dns.getZoneServerName('net.'))            # => [('net_server', 152)]
print(dns.getZoneServerName('example.com.'))    # => [('example_com_server', 153)]