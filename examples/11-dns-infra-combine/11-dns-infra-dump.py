from seedemu.services.DomainNameService import DomainNameService
from seedemu.core import Simulator

sim = Simulator()
dns = DomainNameService()

dns.install('root_server').addZone(dns.getZone('.'))
dns.install('com_server').addZone(dns.getZone('com.')) 
dns.install('net_server').addZone(dns.getZone('net.'))
dns.install('example_com_server').addZone(dns.getZone('example.com.'))

sim.addLayer(dns)
sim.dump('dns-dump.bin')