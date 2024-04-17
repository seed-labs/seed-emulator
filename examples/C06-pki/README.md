# Public Key Infrastructure

This is an example that demonstrates how to use the public key infrastructure (PKI) in the emulator.

In this example we create a PKI infrastructure on node `ca` with ACME support. All the nodes in the emulator will have this private CA root certificate installed. We will also create a web server on node `web` and request a certificate from the CA. The CA will sign the certificate and send it to the web server. The web server will then use this certificate to serve HTTPS requests.

## Key Components

### DNS Infrastructure

Same as examples/B02-mini-internet-with-dns.

DNS infrastructure is required for the PKI infrastructure to work. The PKI infrastructure will consult the DNS infrastructure to resolve the domain names and verify the target node's control of domain in ACME challenges.

ETC hosts file can also be served as DNS infrastructure alternative.

### PKI Infrastructure

To create a PKI infrastructure, we need to prepare the Root CA store. The Root CA store is abstracted as a class but it is essentially a folder living in the host machine's `/tmp` directory. The Root CA store is used to generate the corresponding Root CA certificate and private key in the build time. It is also possible to supply your own Root CA certificate and private key.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
```

After creating the Root CA store, we can create a PKI infrastructure.

```python
from seedemu.services import CAService
ca = CAService(caStore)
ca.install('ca-vnode')
ca.installCACert()
# ca.installCACert(Filter(asn=160))
emu.addLayer(ca)
```

The CA service here uses a private certificate authority program `smallstep` to serve the PKI infrastructure.
For now, the CA service only supports ACME protocol, but it can be easily extended to support X.509 & SSH certificates if needed.

`ca.installCACert()` will by default install the Root CA certificate to all the nodes in the emulator.
It accepts a `Filter` as parameter to install the certificate to specific nodes.
Since the filter logic is implemented inside
the `CAService` rather than the `Filter` object, the `Filter` object might perform
differently in the `CAService` than in other parts.

For example, the allowBound filter is not supported in the `CAService`.

Moreover, inside the `CAService`, the prefix filter is implemented in a portable way that
supports both IPv4 and IPv6 via IPv4-mapped IPv6 addresses. This might not be the case in other
parts.

### Web Server

It's a simple web server that serves a static page. The web server will request a certificate from the CA and use it to serve HTTPS requests.

```python
webServer: WebServer = web.install('web-vnode')
webServer.setServerNames(['user.internal'])
webServer.getCertificatesFrom(ca).enableHTTPS()
```

Server names are required for the web server to request a certificate from the CA. The ACME client will use the server names to determine which nginx configuration to use.

After enabling HTTPS, the web server will serve HTTPS requests.

### Demo

On any nodes that have the Root CA certificate installed (not router or ix nodes, they might not have dns properly configured):

In this example, as we only set up https for https://user.internal.
In your case you can set up https for any domain you want.
Remember to change the domain name accordingly.

```bash
$ curl https://user.internal
```

You will not encounter any certificate errors as the PKI infrastructure is set up correctly.

If it is not set up correctly, you will encounter an error like this:

```bash
$ curl https://self-signed.badssl.com/
curl: (60) SSL certificate problem: self-signed certificate
More details here: https://curl.se/docs/sslcerts.html

curl failed to verify the legitimacy of the server and therefore could not
establish a secure connection to it. To learn more about this situation and
how to fix it, please visit the web page mentioned above.
```

### Inspect the certificate

We can verify that the certificate is issued by SEEDEMU Internal.

```bash
$ step certificate inspect https://user.internal
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
                    ed:c5:3f:15:71:bf:ba:54:d5:ea:78:0b:b8:52:a8:
                    52:06:7f:d7:bf:6f:40:21:40:27:18:86:cf:7d:5e:
                    eb:24:7b:e1:be:05:21:79:a4:c0:dd:c0:eb:06:da:
                    ee:76:19:10:69:ad:64:3d:c3:44:b4:8d:25:a3:5e:
                    31:5b:e7:74:71:f6:2e:d1:54:13:e6:cb:f5:3c:65:
                    94:3c:28:0f:3f:7a:7b:08:d5:08:4d:65:5c:c9:86:
                    2f:9b:57:46:28:9d:a9:a3:e6:6b:12:d0:83:52:a0:
                    fd:fc:e1:c7:38:26:21:19:1b:d5:75:73:5c:69:cb:
                    10:31:74:5d:fa:e9:28:e0:7e:5f:5e:02:72:7c:8a:
                    54:4f:09:27:73:5d:8e:3a:ae:cb:14:ab:16:46:17:
                    7a:89:d4:f3:44:ef:e6:7d:ef:6f:74:e6:b5:a7:ab:
                    a0:0f:8e:dd:c2:47:28:b6:b1:69:6b:d0:2b:ac:a9:
                    79:1e:4b:0e:b3:bc:de:3a:b6:b9:95:9c:6f:cb:e5:
                    85:85:c8:d5:ad:d6:c7:1c:74:34:1a:5b:9c:6e:a5:
                    48:98:ad:05:5d:96:33:ec:1d:e4:21:bd:e7:f8:ed:
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
                DNS:user.internal
            X509v3 Step Provisioner:
                Type: ACME
                Name: acme
    Signature Algorithm: ECDSA-SHA256
         30:44:02:20:65:7e:a2:57:b5:fa:db:53:32:d3:0b:f3:c5:aa:
         95:09:75:eb:75:9d:27:fb:87:fb:09:e4:bd:b9:77:95:01:00:
         02:20:0f:e2:7f:49:70:86:a0:00:a8:9f:2b:fe:cd:9b:12:da:
         55:83:bd:ab:26:0f:66:1f:38:5f:24:67:17:d3:e0:32
```

It shows the same content as the certificate viewer in the browser.
