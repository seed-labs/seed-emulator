# CA Service

This includes development notes on the technical implementation of the CA service.


## Root CA Store

The `RootCAStore` class is a store which contains the Root CA certificate and its private key. It is used by the `CAService` to setup the PKI infrastructure and install the Root CA certificate to the nodes.

If no Root CA certificate is provided, the `RootCAStore` will generate a new Root CA certificate and private key on the fly. The Root CA certificate and private key are stored in the host machine's `/tmp/seedemu-ca-*` directory.

There is also an option to save and restore the Root CA certificate and private key from a folder. 
This is done by copying and pasting the whole ca folder from or to the host machine's `/tmp/seedemu-ca-*` directory.

The new Root CA certificate and its private key are generated using `BuildtimeDockerImage` and `DockerContainer` classes. The generation process is done inside a Docker container to avoid polluting the emulator with unnecessary dependencies.

## CA Service and CA Server

The `CAService` class is a service that creates `CAServer`s which use the `RootCAStore` to serve the PKI infrastructures. It uses the `smallstep`'s `step-ca` program to serve the PKI infrastructure.

The `CAService` class for now only supports:

- Generate TLS certificates for private infrastructure using the ACME protocol.
- Automate TLS certificate renewal.

But it can be easily extended to support other certificate types if needed.

The following features are supported if the corresponding client service is available in the future:

- Issue short-lived SSH certificates via OAuth OIDC single sign on.
- Issue customized X.509 and SSH certificates.

Detailed documentation of `step-ca` can be found at https://smallstep.com/docs/step-ca/.

### Install CA Certificate on nodes

Nodes need to be configured to trust the Root CA certificate in order to make the PKI infrastructure a real authority. By default, as the Root CA certificate is self-signed on the fly, it is not trusted by the nodes.

The `installCACert()` method installs the Root CA certificate to all the nodes in the emulator. It accepts a `Filter` as a parameter to install the certificate to specific nodes.

```python
caServer.installCACert(Filter(asn=160))
caServer.installCACert(Filter(asn=161))
```

The examples above will install the Root CA certificate on the nodes in autonomous systems 160 and 161 respectively.
If there are overlaps among the filters, the certificate will be installed only once.
This is done by appending `Filter` to a list of filters in the `CAServer` class.
It does not replace the existing filters, but appends the new filter to the list.
In the `CAService` configuration stage, the `CAServer` will iterate through the list of filters and install the Root CA certificate to the nodes that match the filter.

The installation process is done by copying the Root CA certificate to the node's `/usr/local/share/ca-certificates` directory and running the `update-ca-certificates` command.

Any node that installs the Root CA certificate will install an additional certificate management tool `step` to inspect/manage the certificates.

Detailed documentation of `step` can be found at https://smallstep.com/docs/step-cli/.

### Enable HTTPS

Enabling HTTPS should be configured inside the `WebService`. However, depending on
how the certificates are managed, the way to configure HTTPS is different.
Therefore, in our design we put the actual HTTPS configuration in the `CAServer`, via
the `enableHTTPSFunc` function. We pass this function to the 
`WebService`, so it can be called to enable the HTTPS. In the future, if we
implement different types of CA services, we can use the same strategy.

In this function, the node will request a certificate from the CA and use it to serve HTTPS requests.
Moreover, a cron job will also be set up to renew the certificate automatically.

Server names are required for the web server to request a certificate from the CA. The ACME client will use the server names to determine which nginx configuration to use.

The default nginx server name is `_`, which means matching all server names. This should be changed to the actual server name (domain name) that the web server is serving.

In our case, the ACME client is the `certbot` which will automatically request the certificate from the CA and configure the nginx server to use the certificate.

When requesting using python library `requests`, please note that the request uses its own trust store, not the system's trust store.
So, when requesting to a website that uses the private PKI, we need to configure it like this:

```bash
$ REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt python3 -c "import requests; print(requests.get('https://{target_domain}').text)"
```

`REQUESTS_CA_BUNDLE` is an environment variable that tells the requests library to use the specified system trust store.

### Renew

The cron job is used to renew the certificate automatically. It is set up by the `enableHTTPS()` function.

```bash
* */1 * * * root test -x /usr/bin/certbot -a \! -d /run/systemd/system && perl -e 'sleep int(rand(3600))' && REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt certbot -q renew
```

It will run the `certbot renew` command every hour. If the certificate is about to expire in 8 hours, it will renew the certificate.

`perl -e 'sleep int(rand(3600))'` is used to randomize the start time of the cron job to avoid the situation where all the cron jobs are running at the same time causing a high load on the CA server.


### Bump step version

Change `seedemu/services/CAService.py`'s `CAService._step_version` to the desired version.

It is a protected variable, so it is technically possible to change it directly.
But it is recommended to be bumped by the maintainer to avoid any potential issues.

It is also recommended to create a file to manage all these versions in a single place.


## Using the step command

### Inspect Certificate

On the nodes that have the Root CA certificate installed, we can inspect certificates using the following command:

```bash
$ step certificate inspect /usr/local/share/ca-certificates/SEEDEMU_Internal_Root_CA.crt
$ step certificate inspect https://{target_domain}
```

Do not use the second command on router or ix nodes, as they might not have the
DNS configured properly.

### Get a standalone certificate without the web server

```bash
$ step ca certificate {target_domain} {target_domain}.crt {target_domain}.key --acme https://{ca_domain}/acme/acme/directory
```
