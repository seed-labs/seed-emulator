
# Domain Registrar Service

## What is Domain Registrar?

Domain registrar manages the reservation of Internet domain names. A domain name registrar must be accredited by a generic top-level domain (gTLD) registry or a country code top-level domain (ccTLD) registry. A registrar operates in accordance with the guidelines of the designated domain name registries

Our emulator allows user to create and simulate their own Domain Name Registrar (like GoDaddy, Hover, Dynadot). Basically, Domain Registrar Service is based on Web Application, when the service has installed in host, users are able to visit Domain Registrar Service by Web browser. In real-world, user might need to sign up an account and sign in to the platform, then they could search the domain that they want to register. If this domain has not been registered yet, they can buy this domain and mangage it. In our Domain Registrar Service, we skip account sign up/in, domain check, payment steps. User can directly input the domain, and add A record for this domain.

## How to get started

### Install Domain Registrar Service example

```
from seedsim.services import DomainRegistrarService

domain_registrar = DomainRegistrarService()
domain_registrar.installByName(161, "s_com_dns")

```

The instance of DomainRegistrarService() could invoke installByName API to install domain registrar on a specific host by providing Autonomous System Number and Host Name.

*Notice: Domain Registrar Service should install on a DNS TLD server, otherwise the process of registering domain will be failed. TODO: By far, the service can only be installed on .com TLD server to manage com subdomain. It should be support ALL types of TLD.*


### Usage

After installation and docker container cluster is up, user can visit the IP address of Domain Registrar host by using browser. (e.g http://10.161.0.71/) You will see the index page of Domain Registrar Service. Input the domain that you want to register, add Buy button, service will redirect to `domain.php` page. Then you should be able to add an A record on this domain. When a record has added, it would take effect with in 1 minute.

### Multiple TLD server scenario

If target Internet structure has more than one TLD server. The Domain Registrar Service should be installed on master node of DNS server. When the master DNS server has dynamically add an record, it will synchronize all the zone data to slave node by zone transfer.

