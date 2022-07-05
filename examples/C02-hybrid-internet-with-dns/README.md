# Deploying DNS Infrastructure in Emulator

This example demonstrates how we can build a DNS infrastructure as a 
component, and then deploy this infrastructure onto a pre-built
emulator. This is based on the B02-mini-internet-with-dns. 
You can refer to the examples/B02-mini-internet-with-dns/Readme.md for detailed explain.
The change from the mini-internet-with-dns to hybrid-internet-with-dns is 
the configuration of ldns. 

## Creating Local DNS Server for Hybrid Internet

Creating a local DNS server is similar to creating 
other types of services. The local dns in hybrid internet emulator should 
add the emulator's zones to its forward zone. 
By doing this, the query can be forward to the 
name servers inside the emulator.

```
#####################################################################################
# Create a local DNS servers (virtual nodes).
# Add forward zone so that the DNS queries from emulator can be forwarded to the emulator's Nameserver not the real ones.
ldns = DomainNameCachingService()
ldns.install('global-dns-1').addForwardZone('google.com.', 'ns-google-com').addForwardZone('twitter.com.', 'ns-twitter-com')
```
