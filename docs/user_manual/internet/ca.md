# CA Service and PKI

A full example can be found in the `examples` folder ([here](../../../examples/C06-pki/)) 

## Root CA Store

The `RootCAStore` class is a store containing the root CA certificate and its private key. It is used by the `CAService` to set up the PKI infrastructure and install the root CA certificate on nodes.

If no root CA certificate is provided, the `RootCAStore` will generate a new root CA certificate and the corresponding private key on the fly. The root CA certificate and private key are stored in the host machine's `/tmp/seedemu-ca-*` directory.

### Initialization

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
caStore.initialize()
```

Or

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
# It initializes the Root CA store.
caServer.setCAStore(caStore)
```

User can either call the initialization manually or let the CA server call it. 


### Save and Restore

After the initialization, we save the root CA certificate and the private key to a folder for later reuse.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
caStore.initialize()
caStore.save("/tmp/ca")
```

Or

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
# It initializes the Root CA store.
caServer.setCAStore(caStore)
caStore.save("/tmp/ca")
```

We can also restore the root CA certificate and private key from a folder.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
# It also initializes the Root CA store.
caStore.restore("/tmp/ca")
```

### Supply your own Root CA certificate and private key

Users can also provide their own root CA certificates and private keys.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
caStore.setRootCertAndKey("/path/to/ca.crt", "/path/to/ca.key")
# The private key should be encrypted.
# This is the password to decrypt the private key.
caStore.setPassword("QDsd0nyzwz0")
caStore.initialize()
```


## CA Service and CA Server

The `CAService` class is a service that creates `CAServer`s which use the `RootCAStore` to serve the PKI infrastructures.

The `CAService` class for now only supports the following, but
it can be easily extended to support other certificate types.

- Generate TLS certificates for the PKI infrastructure using the ACME protocol.
- Automate TLS certificate renewal.


### Install CA Certificate on nodes

We need to install the root CA certificates nodes. We can install the certificates
on all the nodes or use `Filter` to specify the candidate nodes. See the
following examples. 


```python
from seedemu.services import RootCAStore, CAService, CAServer
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
caServer.installCACert()    # On all the nodes
```

```python
from seedemu.services import RootCAStore, CAService, CAServer
from seedemu.core import Filter
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
caServer.installCACert(Filter(asn=160))  # Only on nodes in ASN 160
caServer.installCACert(Filter(asn=161))  # Only on nodes in ASN 161
```

It should be noted that a lax filter will override a more strict filter. This is because the filters are applied individually, so the final set of candidates is the union of the candidates from each filter.
In the following example, the root CA certificate will be installed on the node with ASN 160 (i.e., the one with the `ip` restriction will be overriden). 

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
caServer.installCACert(Filter(asn=160))
caServer.installCACert(Filter(asn=160, ip='10.160.1.3'))
```

In the following example, the root CA certificate will be installed to all the nodes (i.e., the one with `asn` restriction will be overriden). 


```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
caServer.installCACert()
caServer.installCACert(Filter(asn=160))
```


### Set Certificate Duration

Users can set the valid duration for certificates. 

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
ca.setCertDuration('48h')
```

The duration must end with "h". The duration must be no less than 12h.
It is recommended to preserve the default duration `2160h`. Before a certificate expires, it will be renewed automatically. 
