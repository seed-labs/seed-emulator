# CA Service

This includes development notes on the technical implementation of the CA service.

## Technical Implementation

### Root CA Store

The `RootCAStore` class is a store which contains the Root CA certificate and its private key. It is used by the `CAService` to setup the PKI infrastructure and install the Root CA certificate to the nodes.

If no Root CA certificate is provided, the `RootCAStore` will generate a new Root CA certificate and private key on the fly. The Root CA certificate and private key are stored in the host machine's `/tmp/seedemu-ca-*` directory.

There is also an option to save and restore the Root CA certificate and private key from a folder. 
This is done by copying and pasting the whole ca folder from or to the host machine's `/tmp/seedemu-ca-*` directory.

The new Root CA certificate and its private key are generated using `BuildtimeDockerImage` and `DockerContainer` classes. The generation process is done inside a Docker container to avoid polluting the seed-emulator with unnecessary dependencies.

### CA Service

The `CAService` class is a service that uses the `RootCAStore` to serve the PKI infrastructure. It uses the `smallstep`'s `step-ca` program to serve the PKI infrastructure.

The `CAService` class for now only supports:

- Generate TLS certificates for private infrastructure using the ACME protocol.
- Automate TLS certificate renewal.

But it can be easily extended to support other certificate types if needed.

Following features are supported if the corresponding client service is available in the future:

- Issue short-lived SSH certificates via OAuth OIDC single sign on.
- Issue customized X.509 and SSH certificates.

Detailed documentation of `step-ca` can be found at https://smallstep.com/docs/step-ca/.

#### Install CA Certificate in nodes

Nodes need to be configured to trust the Root CA certificate in order to make the PKI infrastructure a real authority. By default, as the Root CA certificate is self-signed on the fly, it is not trusted by the nodes.

The `installCACert()` method installs the Root CA certificate to all the nodes in the emulator. It accepts a `Filter` as a parameter to install the certificate to specific nodes.

```python
ca.installCACert(Filter(asn=160))
ca.installCACert(Filter(asn=161))
```

will install the Root CA certificate to the nodes with ASN 160 and 161 respectively.
If there is any overlap between the filters, the certificate will be only installed once.

This is done by appending `Filter` to a list of filters in the `CAService` class.
It does not replace the existing filters, but appends the new filter to the list.

In the configure stage, the `CAService` will iterate through the list of filters and install the Root CA certificate to the nodes that match the filter.

The installation process is done by copying the Root CA certificate to the node's `/usr/local/share/ca-certificates` directory and running the `update-ca-certificates` command.

Any nodes that install the Root CA certificate will install an additonal certificate management tool `step` to inspect/manage the certificates.

Detailed documentation of `step` can be found at https://smallstep.com/docs/step-cli/.

#### Enable HTTPS

This function is used to enable HTTPS on the web server, which is designed to be called by the `WebServer` class.

In this fucntion, it will request a certificate from the CA and use it to serve HTTPS requests.
Moreover, it will also set up a cron job to renew the certificate automatically.

Server names are required for the web server to request a certificate from the CA. The ACME client will use the server names to determine which nginx configuration to use.

The default nginx server name is `_`, which means match all server names. This should be changed to the actual server name (domain name) that the web server is serving.

In our case, the ACME client is the `certbot` which will automatically request the certificate from the CA and configure the nginx server to use the certificate.

When requesting using python library `requests`, please note that requests uses its own trust store but not the system trust store.
So, when requesting to a website that uses the private PKI, we need to configure it like this:

```bash
$ REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt python3 -c "import requests; print(requests.get('https://{target_domain}').text)"
```

`REQUESTS_CA_BUNDLE` is an environment variable that tells the requests library to use the specified system trust store.

#### Renew

The cron job is used to renew the certificate automatically. It is set up by the `enableHTTPS()` function.

```bash
* */1 * * * root test -x /usr/bin/certbot -a \! -d /run/systemd/system && perl -e 'sleep int(rand(3600))' && REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt certbot -q renew
```

It will run the `certbot renew` command every hour. If the certificate is about to expire in 8 hours, it will renew the certificate.

`perl -e 'sleep int(rand(3600))'` is used to randomize the start time of the cron job to avoid the situation where all the cron jobs are running at the same time causing a high load on the CA server.

#### Inspect Certificate

On any nodes that have the Root CA certificate installed:

```bash
$ step certificate inspect /usr/local/share/ca-certificates/SEEDEMU_Internal_Root_CA.crt
$ step certificate inspect https://{target_domain}
```

Do not use the second command on router or ix nodes, they might not have dns properly configured.

#### Get a standalone certificate without the web server

```bash
$ step ca certificate {target_domain} {target_domain}.crt {target_domain}.key --acme https://{ca_domain}/acme/acme/directory
```

#### Bump step version

Change `seedemu/services/CAService.py`'s `CAService._step_version` to the desired version.

It is a protected variable, so it is technically possible to change it directly.
But it is recommended to be bumped by the maintainer to avoid any potential issues.

It is also recommended to create a file to manage all these versions in a single place.
