# Y04: WannaCry Ransomware Simulator

This folder will recreate the WannaCry incident step by step inside an isolated
SEED Emulator lab. The first piece is a bounded ransomware simulator.

The simulator only operates on a directory named `import_folder`. It creates
fake files, transforms those files into `.wncry_lab` files, writes a ransom
note, and provides a recovery command.

## First Script

```text
safe_ransomware_sim.py
```

Create fake victim files:

```sh
python3 safe_ransomware_sim.py create-sample-files --target ./import_folder
```

Simulate encryption:

```sh
python3 safe_ransomware_sim.py encrypt \
  --target ./import_folder \
  --i-understand-this-is-a-lab
```

Show status:

```sh
python3 safe_ransomware_sim.py status --target ./import_folder
```

Recover files using the lab controller key:

```sh
python3 safe_ransomware_sim.py recover \
  --target ./import_folder \
  --key-file /tmp/wannacry_lab_keys/<victim_id>.key \
  --i-understand-this-is-a-lab
```

## Safety Boundaries

- The target directory must be named `import_folder`.
- The script does not scan the filesystem.
- The script skips hidden files and its own state files.
- File and total byte limits are enforced.
- Recovery is built in.
- The script requires an explicit lab acknowledgement before encryption or
  recovery.

For simplicity, this version does not include blockchain payment. In the real
WannaCry incident, victims were asked to pay ransom to obtain a recovery key.
In this lab, the simulator leaves a copy of the lab decryption key under `/tmp`
so students can inspect the victim host, find the key, and recover the fake
files.

## Emulator Stage

The first emulator entrypoint is:

```text
wannacry_emulator.py
```

It uses the mini-Internet plus the DNS component from
`examples/internet/B02_mini_internet_with_dns` as the base topology. The
`--hosts-per-as` option controls how many hosts are created in each mini-Internet
stub AS. Each stub host gets:

- `/home/seed/import_folder` with fake victim files;
- `/opt/wannacry-lab/safe_ransomware_sim.py`;
- `/opt/wannacry-lab/decrypt_files.py`;
- `/opt/wannacry-lab/vulnerable_smb_service.py`;
- `/opt/wannacry-lab/wannacry_worm.py`;
- `/opt/wannacry-lab/trigger_initial_infection.py`;
- `/opt/wannacry-lab/targets.txt`;
- a lab-only vulnerable SMB-like service listening on TCP port `445`.

The example also includes a DNS kill-switch record:

```text
www.example.net
```

The initial value is:

```text
1.1.1.20
```

which means the worm is allowed to continue spreading.

Build the emulator:

```sh
python examples/yesterday_once_more/Y04_wannacry/wannacry_emulator.py \
  --platform amd \
  --hosts-per-as 4
```

The blockchain payment/key-release workflow is intentionally left out for now.
The code still contains a placeholder function named
`install_blockchain_placeholder()` so we can add that part later without
changing the overall example structure.

## Propagation Model

The worm is a bounded simulator:

```text
wannacry_worm.py
```

It does not scan arbitrary networks. Instead, the emulator generates
`/opt/wannacry-lab/targets.txt`, which contains only the stub host addresses in
this lab. The worm reads that file and sends this lab message to each target's
vulnerable service:

```text
INFECT seedemu-wannacry-lab
```

When a vulnerable host receives the message, it:

1. runs the bounded ransomware simulator against `/home/seed/import_folder`;
2. writes a ransom note and local lab state;
3. writes a visible lab decryption key under `/tmp`;
4. drops `DECRYPT_FILES.py` into `/home/seed/import_folder`;
5. starts `wannacry_worm.py` once, so the newly infected host attempts to infect
   the same bounded target list.

This models self-propagation without implementing a real SMB exploit.

The vulnerable service does not receive arbitrary code from the network. The
emulator installs the ransomware simulator and worm script on every lab host at
build time. The infection message activates those local lab components. This
keeps the example deterministic and avoids creating a reusable malware loader.

## DNS Kill Switch

Before each propagation attempt, the worm resolves:

```text
www.example.net
```

The resolved address controls the worm:

| Address | Meaning |
|---|---|
| `1.1.1.10` | Pause spreading. The worm keeps running and polls DNS until the value changes. |
| `1.1.1.20` | Continue spreading. |
| `1.1.1.30` | Stop the worm process completely. |
| `1.1.1.40` | Reserved for the next behavior. |

The example includes an update helper copied from the B02 DNS example:

```text
add_record.sh
```

Run the helper on the `example.net` authoritative server container. For example,
copy it from the host into the authoritative server:

```sh
docker compose -f output/docker-compose.yml cp \
  examples/yesterday_once_more/Y04_wannacry/add_record.sh \
  hnode_163_host_0:/tmp/add_record.sh

docker compose -f output/docker-compose.yml exec hnode_163_host_0 \
  chmod +x /tmp/add_record.sh
```

To pause spreading:

```sh
docker compose -f output/docker-compose.yml exec hnode_163_host_0 \
  /tmp/add_record.sh 1.1.1.10
```

To continue:

```sh
docker compose -f output/docker-compose.yml exec hnode_163_host_0 \
  /tmp/add_record.sh 1.1.1.20
```

To stop the worm:

```sh
docker compose -f output/docker-compose.yml exec hnode_163_host_0 \
  /tmp/add_record.sh 1.1.1.30
```

## Manual Infection Trigger

After the emulator is running, one host can trigger another host's lab
infection by sending the expected lab message to TCP port `445`.

For example, from AS150 `host_0` to AS151 `host_0`:

```sh
docker compose -f output/docker-compose.yml exec hnode_150_host_0 \
  /opt/wannacry-lab/trigger_initial_infection.py 10.151.0.71
```

Then check the target host:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  python3 /opt/wannacry-lab/safe_ransomware_sim.py status \
    --target /home/seed/import_folder
```

This is not real SMB and not a real exploit. The vulnerable service exists only
to model the moment when a vulnerable host receives an infection trigger. After
that first trigger, propagation happens automatically through the bounded target
list.

To inspect the local worm log on an infected host:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  tail -n 20 /tmp/wannacry_lab_worm.log
```

## Manual Recovery

On an infected victim, the fake files in `/home/seed/import_folder` will have
the `.wncry_lab` suffix, and a ransom note will be present:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  ls -R /home/seed/import_folder
```

Find the lab decryption key:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  sh -lc "find /tmp -name '*key*' -o -name 'wannacry_lab_decryption_key.txt'"
```

For this simplified version, the expected visible key path is:

```text
/tmp/wannacry_lab_decryption_key.txt
```

Run the decryption helper left on the victim:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  python3 /home/seed/import_folder/DECRYPT_FILES.py
```

Then check the files again:

```sh
docker compose -f output/docker-compose.yml exec hnode_151_host_0 \
  python3 /opt/wannacry-lab/safe_ransomware_sim.py status \
    --target /home/seed/import_folder
```

## Monitoring The Attack

Run the monitor on the Docker host, not inside a container:

```sh
python examples/yesterday_once_more/Y04_wannacry/monitor_attack.py
```

If the output is in a different folder, pass the compose file explicitly:

```sh
python examples/yesterday_once_more/Y04_wannacry/monitor_attack.py \
  --compose-file examples/yesterday_once_more/Y04_wannacry/output/docker-compose.yml
```

The monitor discovers host containers from SEED Emulator Docker Compose labels,
queries each host's `/home/seed/import_folder` status, and prints a live
summary:

```text
Y04 WANNACRY LAB MONITOR
========================
hosts discovered          : 48
hosts reachable           : 48
encrypted hosts           : 21
recovered hosts           : 0
clean hosts               : 27
unknown/unreachable hosts : 0
key fingerprints          : 21/21 unique
duplicate key fingerprints: none observed
```

It also lists infected and recovered hosts with their victim IDs and a short
key fingerprint. The fingerprint is a hash of the decryption key, not the raw
key itself.

### Key Uniqueness

Each victim gets a fresh encryption key. In `safe_ransomware_sim.py`, every
successful encryption creates:

```python
key = secrets.token_bytes(32)
```

Each encrypted file also gets its own nonce:

```python
nonce = secrets.token_bytes(16)
```

The monitor checks this property in practice by hashing the visible lab key on
each infected/recovered host and reporting whether duplicate key fingerprints
are observed.
