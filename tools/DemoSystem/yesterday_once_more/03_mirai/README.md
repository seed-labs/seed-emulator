## Demo for Mirai Attack

We have provided demos for this attack in the following folders using different displaying methods:

### Replay the attack

To replay the attack, follow the instructions below:

1. Generate the emulator 

```bash
cd demo 
python ./mirai_internet_with_dns.py
```

2. Start the emulator:

```bash
cd demo_output
DOCKER_BUILDKIT=0 docker compose build
```

3. Operate on the `DemoSystem` webpage

