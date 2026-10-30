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

3. Start the Jupyter notebook server (see `Jupyter/README.md`) and follow the instructions in the Jupyter notebook `Jupyter/bgp_attack_cn.ipynb` (Chinese version) or `Jupyter/bgp_attack.ipynb` (English version) to replay the attack.


### Stop Replaying the attack

To stop the attack, follow the instructions below:

```bash
cd output
docker compose down
```
