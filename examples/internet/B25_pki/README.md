# Public Key Infrastructure

This is an example that demonstrates how to use the public key infrastructure (PKI) in the emulator.

In this example we create a PKI infrastructure on node `ca` with ACME support. All the nodes in the emulator will have this private CA root certificate installed. We will also create a web server on node `web` and request a certificate from the CA. The CA will sign the certificate and send it to the web server. The web server will then use this certificate to serve HTTPS requests.

## What is ACME

The Automatic Certificate Management Environment (ACME) protocol is a communications protocol for automating interactions between certificate authorities and their users' servers, allowing servers and infrastructure software to obtain certificates without user interaction.

The protocol itself has been published as an Internet Standard in [RFC 8555](https://datatracker.ietf.org/doc/html/rfc8555).

As of 2024, over 42% of certificates in the world are issued by Let's Encrypt using ACME protocol.

The real user count of ACME protocol is much higher than 42% because many other CAs also support ACME protocol.

More details about ACME protocol can be found [here](./ACME.md).


## DNS Infrastructure

DNS is required for the PKI infrastructure to work. The PKI infrastructure will use the DNS service to resolve the domain names and verify the target node's control of domain in ACME challenges.

The DNS service can be provided via a DNS infrastructure or simply
using the `/etc/hosts` file. We provide two sets of examples,
one for each approach. 

### Using `EtcHosts` layer 

Using this approach, the static name-to-ip mappings will be added to
the `/etc/hosts` file of all the nodes. 
In our example code in `pki.py`, we created three physical nodes, and assign each of them a using the
`addHostName` API. The mapping of this name to the node's IP address will be added
to the `/etc/hosts` file of all the nodes in the emulator. 

```python
as150.createHost('ca').joinNetwork('net0').addHostName('seedCA.net')
as151.createHost('web1').joinNetwork('net0').addHostName('example32.com')
as151.createHost('web2').joinNetwork('net0').addHostName('bank32.com')
``` 


### Using `DomainNameService` service

This approach is much more complicated, as it needs to set up a
DNS infrastructure, consisting of multiple nameservers,
including the root servers, TLD name servers, and specific domain name servers. 
The example `pki-with-dns.py` uses this approach. Part of the
DNS set up is in `basenetwithDNS.py`. For detailed instructions on 
how to create a DNS, please see `examples/B01-dns-component`.

In this example, we create three physical nodes, and then
add then assign a hostname to each of them using DNS, i.e., adding 
records to the corresponding zones. 

```python
# Create physical nodes
as150.createHost('ca').joinNetwork('net0', address='10.150.0.7')
as151.createHost('web1').joinNetwork('net0', address='10.151.0.7')
as151.createHost('web2').joinNetwork('net0', address='10.151.0.8')

# Assign hostnames 
dns.getZone('seedCA.net.').addRecord('@ A 10.150.0.7')
dns.getZone('example32.com.').addRecord('@ A 10.151.0.7')
dns.getZone('bank32.com.').addRecord('@ A 10.151.0.8')
```

## PKI Infrastructure

To create a PKI infrastructure, we need root CAs. We will generate 
a root CA certificate and its corresponding private key during the emulator build time. 
This is done through the `RootCAStore` class, which generates the root CA
certificate and private key on the host machines at the build time
and stores it inside the `/tmp` folder.
Users can also supply their own Root CA certificate and private key.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='seedCA.net')
```

After creating the Root CA store, we can create a PKI infrastructure.

```python
from seedemu.services import CAService
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')  # Create a CA server
caServer.setCertDuration("2160h")  # Set the expiration date 
caServer.installCACert()           # Install the root CA certficate to all nodes
# caServer.installCACert(Filter(asn=160))  
emu.addLayer(ca)
```

The current CA service uses a private certificate authority program called `smallstep`
to provide the PKI infrastructure.
For now, the CA service only supports the ACME protocol, but it can be easily extended to support X.509 & SSH certificates. 

In the example, `ca.install('ca-vnode')` will create a CA server node, which will
accept certificate-signing requests from clients, conduct verification, and then
issue certificates. The generated root CA certificate and private key
will be copied to this node, to the corresponding sub-folders inside `/root/.step/`.

We also need to copy all the root CA certificates to all the nodes.
This is done via `caServer.installCACert()`, which by default installs the Root CA certificate to all the nodes in the emulator. If we only want to install the certificate to specific nodes,
we can use pass a `Filter` argument to this call. 

It should be noted that since the actual filter logic is implemented inside the class that uses the filter,
not inside the `Filter` class itself, the `Filter` object might perform differently
in the `CAService` than in other places.
For example, the `allowBound` filter is not supported in the `CAServer`.
Moreover, inside the `CAService`, the prefix filter is implemented in a portable way that
supports both IPv4 and IPv6 via IPv4-mapped IPv6 addresses. This might not be the case in other places. 

Filter logic is described in [developer manual](../../docs/developer_manual/11-ca-service.md).
More API examples are available in the [user manual](../../docs/user_manual/internet/ca.md).

## Web Server

In this example, we use a web server to demonstrate how the PKI is used. 
This is a simple web server that serves a static page. When this machine starts,
it will request a certificate from the specified CA server, and use it to serve HTTPS requests.

```python
webServer: WebServer = web.install('web-vnode')
webServer.setServerNames(['example32.com'])
webServer.setCAServer(caServer).enableHTTPS()
```

Server names are required for the web server to request a certificate from the CA. The ACME client will also use the server names to determine which nginx configuration to use.
The `enableHTTPS` API will configure the web server using the certificate, allowing
the server to serve HTTPS requests.

## Demo

On nodes that have the Root CA certificate installed (not routers or ix nodes, as they might not have DNS configured properly):

In this example, we set up https for https://example32.com and https://bank32.com.
In your case you can set up https for any domain you want.
Remember to change the domain name accordingly.

```bash
$ curl https://example32.com
<h1>web server at example32.com</h1>
```

You will not encounter any certificate errors as the PKI infrastructure is set up correctly. If it is not set up correctly, you will encounter an error like this:

```bash
$ curl https://self-signed.badssl.com/
curl: (60) SSL certificate problem: self-signed certificate
More details here: https://curl.se/docs/sslcerts.html

curl failed to verify the legitimacy of the server and therefore could not
establish a secure connection to it. To learn more about this situation and
how to fix it, please visit the web page mentioned above.
```

### Inspect the certificate

We can verify the certificate of a server from any node; run the `step` command. 

```
$ step certificate verify https://bank32.com --roots="/etc/ssl/certs/vTrus_ECC_Root_CA.pem"

failed to connect: tls: failed to verify certificate: x509: certificate signed by unknown authority

$ step certificate verify https://bank32.com \
       --roots="/etc/ssl/certs/SEEDEMU_Internal_Root_CA.pem"
```

We can also display the certificate obtained from a server:

```bash
$ step certificate inspect https://example32.com
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 282740490654816244645159899382739884920 (0xd4b5d67668d27f85937a9ad18377db78)
    Signature Algorithm: ECDSA-SHA256
        Issuer: O=SEEDEMU Internal,CN=SEEDEMU Internal Intermediate CA
        Validity
            Not Before: Apr 14 20:48:38 2024 UTC
            Not After : Jul 14 20:49:38 2024 UTC
        Subject:
        Subject Public Key Info:
            Public Key Algorithm: RSA
                Public-Key: (2048 bit)
                Modulus:
                    a9:02:3e:b0:f1:27:f4:a0:6b:c9:0a:6a:2d:49:6b:
                    ...
                    20:eb:3c:5f:17:e8:a0:08:a2:6c:1f:bb:3b:91:d2:
                    b1
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage:
                Server Authentication, Client Authentication
            X509v3 Subject Key Identifier:
                20:1A:27:1F:9B:33:42:1C:F5:CB:E3:78:44:FE:0F:0D:8A:E0:74:9B
            X509v3 Authority Key Identifier:
                keyid:68:B3:54:CA:24:87:3F:D1:30:32:41:42:34:1A:11:34:5E:98:8C:D0
            X509v3 Subject Alternative Name: critical
                DNS:example32.com
            X509v3 Step Provisioner:
                Type: ACME
                Name: acme
    Signature Algorithm: ECDSA-SHA256
         30:44:02:20:65:7e:a2:57:b5:fa:db:53:32:d3:0b:f3:c5:aa:
         ...
         55:83:bd:ab:26:0f:66:1f:38:5f:24:67:17:d3:e0:32
```

