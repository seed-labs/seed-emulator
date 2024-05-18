from seedemu.services.DomainNameService import DomainNameService
from seedemu.core import Emulator

emu = Emulator()
dns = DomainNameService()

dns.install('root_server').addZone(dns.getZone('.'))
dns.install('com_server').addZone(dns.getZone('com.')) 
dns.install('net_server').addZone(dns.getZone('net.'))
dns.install('example_com_server').addZone(dns.getZone('example.com.'))

emu.addLayer(dns)
emu.dump('dns-component.bin')
