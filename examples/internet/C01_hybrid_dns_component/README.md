# Building a DNS Infrastructure Component for Hybrid Internet

This example demonstrates how we can build a DNS infrastructure as a component. 
We generate a hybrid DNS infrastructure and save it into a file as 
a DNS component. This component can be loaded into other emulators, which
means deploying the DNS infrastructure in those emulators. 

In this hybrid DNS, we created the following nameservers:
(TLD Name server is not exist in this hybrid DNS 
and the emulator only have second-level zones.)

- Root server: `a-root-server` - shadows a real root server's records
- `twitter.com` nameserver: `ns-twitter-com`
- `google.com` nameserver: `ns-google-com`


## Creating Virtual Nameserver for Root Server

We will create the DNS infrastructure at the DNS layer, 
so each node created is a virtual node, which is not bound to
any physical node. The example creates a real-world Root NameServer.
Using .setRealRootNS(), we can announce the root server a real one. 

```
# Create a nameserver for the root zone. 
# Make it shadow the real root zone. 
dns.install('a-root-server').addZone('.').setRealRootNS()
```

If it is set to the real root server, it will collect the records 
from the real world root server.

```
path : seedemu/services/DomainNameService.py

def __getRealRootRecords(self):
    """!
    @brief Helper tool, get real-world prefix list for the current ans by
    RIPE RIS.

    @throw AssertionError if API failed.
    """
    rules = []
    rslt = requests.get(ROOT_ZONE_URL)

    assert rslt.status_code == 200, 'RIPEstat API returned non-200'
    
    rules_byte = rslt.iter_lines()
    
    for rule_byte in rules_byte:
        line_str:str = rule_byte.decode('utf-8')
        if not line_str.startswith('.'):
            rules.append(line_str)
    
    return rules
```

