# ACME Protocol Overview

## Account Management

Client first creates a pair of public/private keys for account management.

Every request to the server will be signed by this private key including the account creation request.

```
POST /acme/new-account

+--------------------------+
| contact                  |
| termsOfServiceAgreed     | --> Server
| Account Public Key       |
+--------------------------+

           +-----------------------------------------------------+
Client <-- | Existing orders URL /acme/acct/evOfKhNU60wg/orders  |
           +-----------------------------------------------------+
```



## Order Management

Client creates a new order for a certificate.

```
POST /acme/new-order
+--------------------------------+
| identifiers (www.example.org)  | --> Server
+--------------------------------+

            +-----------------------------------------------+
            | Authorization URL /acme/authz/PAniVnsZcis     |
Client <--  | Finalize URL /acme/order/TOlocE8rfgo/finalize |
            +-----------------------------------------------+
```



## Challenge and Response

```
POST /acme/authz/PAniVnsZcis

            +--------------------------------------------+
Client <--  | type http-01                               |
            | token DGyRejmCefe7v4NfDGDKfA               |
            | Challenge URL /acme/challenge/prV_B7yEyA4  |
            +--------------------------------------------+
```



## Prepare the Challenge

In web server, create a file with the token and the hash of the account public key.

```bash
$ curl http://www.example.org/.well-known/\
    acme-challenge/DGyRejmCefe7v4NfDGDKfA
DGyRejmCefe7v4NfDGDKfA.<SHA256(Account Public Key)>
```



## Respond to the Challenge

```
POST /acme/challenge/prV_B7yEyA4

                          Check the Challenge
Challenge & Response URL <--------------------- Server


Challenge & Response URL:
http://www.example.org/.well-known/acme-challenge/DGyRejmCefe7v4NfDGDKfA
```

Server will check the dns record and find the corresponding IP.
Server will then request to the port 80 of the IP to check the file content.



## Finalize the Order

```
POST /acme/order/TOlocE8rfgo/finalize

+----------------------------------+
| CSR (Certificate of Web Server)  | --> Server
+----------------------------------+

            +----------------------------------------+
Client <--  | Certificate URL /acme/cert/mAt3xBGaobw |
            +----------------------------------------+
```



## Certificate Issuance

```
POST /acme/cert/mAt3xBGaobw

            +-------------------------------------+
Client <--  | Certificate (Signed)                |
            | Intermediate Certificate (Optional) |
            | Root Certificate (Optional)         |
            +-------------------------------------+
```