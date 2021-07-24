# Labs Based on Internet Emulator

The objective of this project is two-fold: (1) create education-oriented
Internet emulators, and (2) develop hands-on lab exercises based on the emulators.
The needs from these labs will also help drive the development of the
emulator. This folder hold the labs developed from this project.
We welcome contribution from the community.

In this document, we provide some initial lab ideas that could benefit from the emulators.
New ideas are welcome and they will constantly be added to this wish list.

## BGP Related Labs 

These will be a series of labs that help students understand
how BGP works and how it can be attacked. It can be used for teaching the
following:

- How BGP works in the real world. We hope to incorporate some of the business 
  aspects of BGP, such as peering agreement, tier status of autonomous system. 
  There were many disputes related to BGP (mostly due to the business interests),
  maybe we can recreate some of the disputes in the emulation.
- How IP anycast is supported (used by DNS root servers): 
  see [Example-B03](/examples/B03-ip-anycast). 
- BGP attacks: Network prefix hijacking:
  see [Example-B04](/examples/B04-bgp-prefix-hijacking). 

## Yesterday-Once-More Labs 

These labs will recreate interesting cybersecurity 
incidents happened in the past, including attacks, mistakes, and disasters.
We would like to take students back to the past to experience, observe,
or even change the "history". These will be a series of labs,
one for each past incident. Here is the list of ideas:

- *Morris Worm*: Recreating the Morris Worm, and release it inside the emulator.
   We do need to recreate those involved vulnerable programs and install them
   on all the nodes inside the emulator. 
- *Pakistan's Hijacking of YouTube*:  
- *Turkey's Hijacking of Global DNS*:  
- *Syria's Self Isolation from the Internet*:


## DNS Labs

We can easily deploy a DNS infrastructure inside the emulator, including 
root servers, TLD servers, and nameservers for specific domains. 
See examples 21 and 22. It can be used to teach the following:

- Understand the DNS infrastructure: the theory part of DNS is not hard to understand,
  but in practice, the DNS infrastructure is quite complicated. 
  This lab is intended to help student understand how DNS really works
  in the real world. We will design activities to help students understand 
  the technologies, such as IP anycast for root servers, domain registration,
  setting up nameserver, etc.  
  See [Example-B01](/examples/B01-dns-component) and 
  [Example-B02](/examples/B02-mini-internet-with-dns)
- Various DNS attacks: the DNS cache poisoning attack and DNS rebinding attack are
  already covered in the SEED labs. There are many other attacks on DNS, some of 
  which can benefit from this emulator.
- How DNSSEC works. 


## Blockchain and Smart Contract Labs

We are currently implement the Blockchain service. Using this service,
we can build a blockchain component, which is essentially an overlay network 
with the nodes running the Ethereum software. This example demonstrates
how the needs for lab development can drive the development of the Emulator software.

Once a component is built, it can be deployed inside an emulator, so we can have a blockchain
running inside our emulator. This blockchain will then become the platform
for lab exercises. It can be used for teaching the following:

- How blockchain works 
- How smart contract works 
- Common vulnerabilities in smart contract applications


## Botnet Lab

Botnet is already implemented. We will develop
a lab to help students understand how this type of attacks works, 
what it is capable of, what techniques it uses to evade detection, etc.


## Darknet Lab

Darknet is already implemented. We will develop a lab to 
help students understand how to achieve anonymous 
communication on the Internet, and the technical details
behind the Darknet.


## The CDN (Content Delivery Network) Technology

We can use our emulation to deploy a CDN, and then use 
it to study the technology behind CDN. Our emulator does not 
support CDN yet, so we need to first add CDN support first.


