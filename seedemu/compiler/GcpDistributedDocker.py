from seedemu.core.Emulator import Emulator
from seedemu.core import Registry, Compiler
from .DistributedDocker import DistributedDocker
from typing import Dict
from hashlib import md5
from os import mkdir, chdir, chmod

GcpDistributedDockerFileTemplates: Dict[str, str] = {}

GcpDistributedDockerFileTemplates['_tf_scripts/get-swmtkn'] = '''\
#!/bin/bash
host="`jq -cr '.host'`"
token="`ssh -i ssh_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "seed@$host" 'sudo docker swarm join-token worker -q'`"
jq -ncr --arg token "$token" '{"token":$token}'
exit 0
'''

GcpDistributedDockerFileTemplates['_tf_scripts/ssh-keygen'] = '''\
#!/bin/bash
[ ! -e ssh_key ] && ssh-keygen -b 2048 -t rsa -f ./ssh_key -q -N ''
jq -ncr --arg private_key "`cat ssh_key`" --arg public_key "`cat ssh_key.pub`" '{"private_key":$private_key, "public_key":$public_key}'
exit 0
'''

GcpDistributedDockerFileTemplates['variables.tf'] = '''\
variable "project" {
  type = string
  description = "GCP project ID"
}

variable "region" {
  type = string
  description = "GCP region"
}

variable "zone" {
  type = string
  description = "GCP zone"
}

variable "credentials_file" {
  type = string
  description = "Path to the JSON credentials file (https://console.cloud.google.com/apis/credentials/serviceaccountkey)"
}
'''

GcpDistributedDockerFileTemplates['main.tf'] = '''\
terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

provider "google" {
  version = "3.5.0"

  credentials = file(var.credentials_file)

  project = var.project
  region  = var.region
  zone    = var.zone
}
'''

GcpDistributedDockerFileTemplates['network.tf'] = '''\
resource "google_compute_network" "swarm" {
  name = "seedemu-swarm"
}

resource "google_compute_firewall" "swarm" {
  name    = "seedemu-swarm-firewall"
  network = google_compute_network.swarm.name

  allow {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}
'''

GcpDistributedDockerFileTemplates['data.tf'] = '''\
data "external" "ssh_keys" {
  program = ["_tf_scripts/ssh-keygen"]
}

data "external" "swarm_tokens" {
  program = ["_tf_scripts/get-swmtkn"]

  query = {
    host = google_compute_instance.manager.network_interface[0].access_config[0].nat_ip
  }
}
'''

GcpDistributedDockerFileTemplates['manager_tf_template'] = '''\
resource "google_compute_instance" "manager" {{
  name = "manager"
  machine_type = "{machineType}"

  boot_disk {{
    initialize_params {{
      image = "debian-cloud/debian-10"
      size  = 16
    }}
  }}

  metadata = {{
    ssh-keys = "seed:${{data.external.ssh_keys.result.public_key}}"
  }}

  network_interface {{
    network = google_compute_network.swarm.name
    access_config {{
    }}
  }}

  connection {{
    host = self.network_interface[0].access_config[0].nat_ip
    type = "ssh"
    user = "seed"
    private_key = data.external.ssh_keys.result.private_key
  }}

  provisioner "file" {{
      source = "_containers/ix"
      destination = "/tmp/"
  }}

  provisioner "remote-exec" {{
    inline = [
      "sudo apt-get update",
      "sudo apt-get -qq --no-install-recommends install apt-transport-https ca-certificates curl gnupg-agent software-properties-common",
      "curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -",
      "sudo add-apt-repository \\"deb [arch=amd64] https://download.docker.com/linux/debian `lsb_release -cs` stable\\"",
      "sudo apt-get update",
      "sudo apt-get -qq --no-install-recommends install docker-ce docker-ce-cli containerd.io docker-compose",
      "sudo docker swarm init",
      "sudo modprobe mpls_router",
      "cd /tmp/ix",
      "sudo docker-compose up -d"
    ]
  }}

  depends_on = [google_compute_firewall.swarm]
}}
'''

GcpDistributedDockerFileTemplates['worker_tf_template'] = '''\
resource "google_compute_instance" "worker-as{name}" {{
  name = "worker-as{name}"
  machine_type = "{machineType}"

  boot_disk {{
    initialize_params {{
      image = "debian-cloud/debian-10"
      size  = 16
    }}
  }}

  metadata = {{
    ssh-keys = "seed:${{data.external.ssh_keys.result.public_key}}"
  }}

  network_interface {{
    network = google_compute_network.swarm.name
    access_config {{
    }}
  }}

  connection {{
    host = self.network_interface[0].access_config[0].nat_ip
    type = "ssh"
    user = "seed"
    private_key = data.external.ssh_keys.result.private_key
  }}

  provisioner "file" {{
      source = "_containers/{name}"
      destination = "/tmp/"
  }}

  provisioner "remote-exec" {{
    inline = [
      "sudo apt-get update",
      "sudo apt-get -qq --no-install-recommends install apt-transport-https ca-certificates curl gnupg-agent software-properties-common",
      "curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -",
      "sudo add-apt-repository \\"deb [arch=amd64] https://download.docker.com/linux/debian `lsb_release -cs` stable\\"",
      "sudo apt-get update",
      "sudo apt-get -qq --no-install-recommends install docker-ce docker-ce-cli containerd.io docker-compose",
      "sudo docker swarm join --token ${{data.external.swarm_tokens.result.token}} ${{google_compute_instance.manager.network_interface[0].network_ip}}:2377",
      "sudo modprobe mpls_router",
      "cd /tmp/{name}",
      "sudo docker-compose up -d"
    ]
  }}
}}
'''

class GcpDistributedDocker(Compiler):
    """!
    @brief The GcpDistributedDocker compiler class.

    GcpDistributedDocker is one of the compiler driver. It compiles the lab to
    sets of docker containers, and generate Terraform configuration for
    deploying the lab to GCP.
    """

    def getName(self) -> str:
        return 'GcpDistributedDocker'

    def __init_tf(self):
        """!
        @brief Get files required by Terraform ready.
        """
        self._log('initializing terraform environment...')
        mkdir('_tf_scripts')
        for file in ['_tf_scripts/get-swmtkn', '_tf_scripts/ssh-keygen', 'variables.tf', 'main.tf', 'network.tf', 'data.tf']:
            print(GcpDistributedDockerFileTemplates[file], file=open(file, 'w'))
        
        for exfile in ['_tf_scripts/get-swmtkn', '_tf_scripts/ssh-keygen']:
            chmod(exfile, 0o755)

    def __make_tf(self, registry: Registry):
        """!
        @brief Generate TF config for docker hosts.
        """
        self._log('generating terraform configurations...')

        print(GcpDistributedDockerFileTemplates['manager_tf_template'].format(
            machineType = "f1-micro" # todo
        ), file=open('manager.tf', 'w'))

        scopes = set()

        for (scope, type, _) in registry.getAll().keys():
            if scope == 'ix': continue
            if type == 'net' or type == 'hnode' or type == 'rnode' or type == 'snode':
                scopes.add(scope)

        for scope in scopes:
            print(GcpDistributedDockerFileTemplates['worker_tf_template'].format(
            machineType = "f1-micro", # todo
            name = scope
        ), file=open('worker-as{}.tf'.format(scope), 'w'))

    def _doCompile(self, emulator: Emulator):
        registry = emulator.getRegistry()
        dcomp = DistributedDocker()
        self.__init_tf()
        self._log('generating container configurations...')
        dcomp.compile(emulator, '_containers')
        self.__make_tf(registry)