# CA Service

## Root CA Store

The `RootCAStore` class is a store which contains the Root CA certificate and its private key. It is used by the `CAService` to setup the PKI infrastructure and install the Root CA certificate to the nodes.

If no Root CA certificate is provided, the `RootCAStore` will generate a new Root CA certificate and private key on the fly. The Root CA certificate and private key are stored in the host machine's `/tmp/seedemu-ca-*` directory.

### Initialize

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
caStore.initialize()
```

Or

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
# It initializes the Root CA store.
ca = CAService(caStore)
```

User can either call it manually or let the CA service to call it.

### Save and Restore

Save the Root CA certificate and private key to a folder for later reuse.

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
# It initializes the Root CA store.
ca = CAService(caStore)
caStore.save("/tmp/ca")
```

Restore the Root CA certificate and private key from a folder.

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
# It also initializes the Root CA store.
caStore.restore("/tmp/ca")
```

### Supply your own Root CA certificate and private key

```python
from seedemu.services import RootCAStore
caStore = RootCAStore(caDomain='ca.internal')
caStore.setRootCertAndKey("/path/to/ca.crt", "/path/to/ca.key")
# Yes, the private key should be encrypted.
# This is the password to decrypt the private key.
caStore.setPassword("QDsd0nyzwz0")
caStore.initialize()
```

## CA Service

The `CAService` class is a service that uses the `RootCAStore` to serve the PKI infrastructure.

The `CAService` class for now only supports:

- Generate TLS certificates for private infrastructure using the ACME protocol.
- Automate TLS certificate renewal.

But it can be easily extended to support other certificate types if needed.

### Install CA Certificate in nodes

#### Install to all nodes

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
ca.installCACert()
```

#### Install to specific nodes

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
ca.installCACert(Filter(asn=160))
ca.installCACert(Filter(asn=161))
```

The Root CA certificate will be installed to the nodes with ASN 160 and 161 respectively.

#### Lax filter will override strict filter

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
ca.installCACert(Filter(asn=160))
ca.installCACert(Filter(asn=160, ip='10.160.1.3'))
```

The Root CA certificate will be installed to the node with ASN 160.

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
ca.installCACert()
ca.installCACert(Filter(asn=160))
```

The Root CA certificate will be installed to all the nodes.

### Set Leaf Certificate Duration

```python
from seedemu.services import RootCAStore, CAService
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService(caStore)
ca.setCertDuration('48h')
```

The duration must end with "h".
The duration must no less than 12h.

Even if you don't set duration manually, it will not expire as it will be renewed automatically.
It is recommended to preserve the default duration 2160h.
