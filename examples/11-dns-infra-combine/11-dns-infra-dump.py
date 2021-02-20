from seedsim.services.DomainNameService import DomainNameService
from seedsim.core import Simulator

sim = Simulator()
dns = DomainNameService()

dns.installByName(150, 'root_server').addZone(dns.getZone('.'))
dns.installByName(151, 'com_server').addZone(dns.getZone('com.')) 
dns.installByName(152, 'net_server').addZone(dns.getZone('net.'))
dns.installByName(153, 'example_com_server').addZone(dns.getZone('example.com.'))

sim.addLayer(dns)
sim.dump('dns-dump.bin')