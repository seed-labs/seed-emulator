import docker
import os
import subprocess

def get_container_by_ip(ip):
    client = docker.from_env()
    client.containers.list()
    for container in client.containers.list():
        labels = container.attrs['Config']['Labels']
        if ip == labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]:
            client.close()
            return container
    client.close()
    return None

def get_container_pid_by_ip(ip):
    client = docker.from_env()
    client.containers.list()
    for container in client.containers.list():
        labels = container.attrs['Config']['Labels']
        if ip == labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]:
            client.close()
            return container.attrs['State']['Pid']
    client.close()
    return None

def get_container_name_by_ip(ip):
    client = docker.from_env()
    client.containers.list()
    for container in client.containers.list():
        labels = container.attrs['Config']['Labels']
        if ip == labels.get("org.seedsecuritylabs.seedemu.meta.net.0.address").split("/")[0]:
            client.close()
            return container.name
    client.close()
    return None

def get_interface_by_ip(ip):
    get_if_cmd = 'sudo ovs-vsctl --columns=name --no-headings find interface external_ids{{>}}container_id={container_name}'
    process = subprocess.run(get_if_cmd.format(container_name=get_container_name_by_ip(ip)).split(), capture_output=True)
    return process.stdout.decode('utf-8').strip()

print(get_interface_by_ip('10.0.0.1'))
    

