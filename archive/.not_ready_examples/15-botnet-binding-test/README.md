# Botnet binding example

## Step 1:

Run `15-base-component.py`, in order to reuse a base component. In this base component, there are 7 AS, which are `AS150,AS151,AS152,AS153,AS154,AS160,AS161`. Each of AS has 5 hosts. All of hosts are able to connect each other. After running, you will see a base-component.bin file in this folder.


## Step 2:

Run `15-botnet-component.py`. In this component, we have pre-built a botnet component, including 10 bots and 1 C2 server, and we tell all the bots that the IP address of C2 server is `10.150.0.71`, so after running container, all of bots would know who they should connect to.


## Step 3

Next, we will run `15-botnet-binding-test.py`. Firstly, we need to make sure there are 2 bin files in the folder, then the `13-botnet-binding-test.py` will load these 2 bin files, deploy our botnet into base component. For the `c2_server` binding, we need to use `filter = Filter(asn = 150), action=Action.FIRST`. Because we have told bots the IP address of C2 server, which is the first host in AS150, so we have to install our C2 server by the percise filter.

If everything goes smoothly. You would see there is a folder called `botnet-binding` has been generated. Then go to `botnet-binding` folder, build and run all container by running `docker-compose build && docker-compose up`.

## Step 4

Let's verify if our botnet works. Attach into the C2 server. Then in the C2 container, we will go to ```/tmp/byob/byob``` folder to launch our Botnet C2 console by using command ```python3 server.py --port 445```. Next, wait a couple of minutes, we will see our bot client join to our botnet (type ```sessions``` command in C2 console to check. ). That means we can control those bot and send any commands to them.
