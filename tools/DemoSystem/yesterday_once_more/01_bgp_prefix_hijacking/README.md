## Demo for BGP Prefix Hijacking

The topology of our network is shown in `topology.txt` (it is only for reference purpose, the file is not used in the emulator code).

### Replay the attack

To replay the attack, follow the instructions below:

1. Generate the emulator 

```bash
python ./BGP_Prefix_Hijacking.py
```

2. Start the emulator:

```bash
cd output
DOCKER_BUILDKIT=0 docker compose build
docker compose up
```

3. Operate on the `DemoSystem` webpage.
    
    After the shooting range is successfully activated, select to enter the `Map` page and then proceed with the subsequent operations.


### Stop Replaying the attack

To stop the attack, follow the instructions below:

```bash
cd output
docker compose down
```
