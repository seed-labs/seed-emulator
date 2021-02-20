from seedsim.core import Simulator
from seedsim.services import DomainNameService

sim = Simulator()
sim.load('dns-dump.bin')

dns: DomainNameService = sim.getLayer('DomainNameService')

print(dns.getZoneServerNames('.'))               # => [('root_server', 150)]
print(dns.getZoneServerNames('com.'))            # => [('com_server', 151)]
print(dns.getZoneServerNames('net.'))            # => [('net_server', 152)]
print(dns.getZoneServerNames('example.com.'))    # => [('example_com_server', 153)]