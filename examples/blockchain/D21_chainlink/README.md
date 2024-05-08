# Adding Chainlink Service to Blockchain

## Adding the Chainlink Service

Detailed explanation of each of the code is already provided as comments
in the code, so we will not repeat them in this document. 
Each server is protected by a login page; the default username 
is `seed@seed.com` and the default password is `Seed@emulator123`. 
We can change them using the following API of the server 
class (the username must be an email address and the password
must have 16 to 50 characters).

```python
setUsernameAndPassword(username = '<username>', password = '<password>')
```

## Interacting with the Chainlink Initializer Server

The Chainlink Initializer server is used to deploy the LINK token contract and
display the deployed oracle contract address. You can access the Chainlink
Initializer server by navigating to `http://<host_ip>:80` in your web browser.
The Chainlink Initializer server displays the deployed oracle contract address
and the LINK token contract address. This information is useful for building
and deploying solidity contracts and deploying jobs.


```bash
docker ps | grep Chainlink-Init
docker logs <CONTAINER ID>
```

Here is the sample output of the Chainlink Initializer server:
```
Link Token Contract: 0x34CFC22C4A0Bf351654CDADadAe821a86fc91554
Oracle Contract Address: 0x3F25076D76623e1A713A4fAEB78fc59Ee8E79024
Oracle Contract Address: 0xE1ca974bEC6f7FEA67BB9f7FF699390702EB00F8
Oracle Contract Address: 0xE4ea89d4557EFeF39B7e14ad4db6D942AeA7ac96
```

## Interacting with the Chainlink Server using CLI

Chainlink CLI: You can interact with the Chainlink service using the Chainlink
CLI. The Chainlink CLI is a command-line tool that allows you to interact with
the Chainlink node. You can use the CLI to create and manage Chainlink jobs,
check the status of the Chainlink node, and more. The Chainlink CLI can be
accessed by running the following command on Chainlink servers: 

```bash
# chainlink admin login

Default username: seed@seed.com
Default password: Seed@emulator123
```

Instructions on how to use the Chainlink CLI can be found
[here](https://github.com/smartcontractkit/chainlink/wiki/Command-Line-Options).


## Interacting with the Chainlink Server using UI

### Login  

Each Chainlink server comes with a web UI that can
be used to interact with the server.  You can access the UI by navigating
to `http://<host_ip>:6688`. It allows you to create and manage Chainlink jobs. 

  ```
  Default username: seed@seed.com
  Default password: Seed@emulator123
  ```

### Dashboard

After the login, we will enter the dashboard. From here, 
we can create and manage Chainlink jobs,
check the status of the Chainlink node, and more.
It will show the address of 
the account created during chainlink start command which 
should be funded with 5 ETH tokens.
```
Account Balance
Address  0xC485bC418643777f98A0C0eF31244Ea766028088
Native Token Balance 5.000000000000000000
LINK Balance         0.00000000
```

Instructions on how to use the dashboard to manage jobs can be
found [here](https://docs.chain.link/chainlink-nodes)
