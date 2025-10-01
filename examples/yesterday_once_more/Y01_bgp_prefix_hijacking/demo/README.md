## Demo for BGP Prefix Hijacking

This demo is about displaying victim's screen in our map website and Docker container terminal. Option to display victim's screen in your own VM using Virtualbox/VMware/Parallels/... is provided. The topology of our network is shown in `topology.txt`.

### Replay the attack

To replay the attack, follow the instructions below:

1. Generate the network dockerfile:

```bash
python ./BGP_Prefix_Hijacking.py
```

2. Start the InternetMap:

```bash
cd InternetMap
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

3. Start the emulator network:

```bash
cd output
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

***

#### (Optional) Use your own VM to display the victim's screen

1. Start your own VM using Virtualbox/VMware/Parallels/...
2. Copy the `Link_Ovpn` folder to your VM
3. Link your VM to the emulator network by following the instructions in `Link_Ovpn/README.md`

***

### Stop Replaying the attack

To stop the attack, follow the instructions below:

1. Disconnect your VM from the emulator network by following the instructions in `Link_Ovpn/README.md`
2. Stop the emulator network:

```bash
cd output
docker compose down
```

3. Stop the InternetMap:

```bash
cd InternetMap
docker compose down
```