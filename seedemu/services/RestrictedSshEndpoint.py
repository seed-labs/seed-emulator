"""Reusable installation of a source-restricted SSH forced-command endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from re import fullmatch
import subprocess
import tempfile
from typing import Tuple

from seedemu.core import Node


@dataclass(frozen=True)
class RestrictedSshEndpoint:
    """Configuration for one key-only SSH endpoint with no interactive shell."""

    source_address: str
    source_public_key: str
    host_private_key: str
    host_public_key: str
    forced_command: str
    config_name: str


def generateSshKeyPair(comment: str) -> Tuple[str, str]:
    """Generate a deployment-local Ed25519 private/public key pair."""
    assert comment.strip(), 'SSH key comment cannot be empty'
    with tempfile.TemporaryDirectory() as work:
        key_path = Path(work) / 'id_ed25519'
        subprocess.run(
            [
                'ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                '-C', comment, '-f', str(key_path),
            ],
            check=True,
            capture_output=True,
        )
        return (
            key_path.read_text(),
            key_path.with_suffix('.pub').read_text().strip(),
        )


def installRestrictedSshEndpoint(
    node: Node,
    endpoint: RestrictedSshEndpoint,
) -> None:
    """Install host keys and a source-bound forced command on ``node``."""
    ip_address(endpoint.source_address)
    assert endpoint.source_public_key.startswith('ssh-ed25519 '), (
        'restricted SSH source key must be Ed25519'
    )
    assert 'BEGIN OPENSSH PRIVATE KEY' in endpoint.host_private_key, (
        'invalid restricted SSH host private key'
    )
    assert endpoint.host_public_key.startswith('ssh-ed25519 '), (
        'restricted SSH host public key must be Ed25519'
    )
    assert fullmatch(r'/[A-Za-z0-9_./-]+', endpoint.forced_command), (
        'invalid restricted SSH forced command'
    )
    assert '..' not in endpoint.forced_command.split('/'), (
        'invalid restricted SSH forced command'
    )
    assert fullmatch(r'[A-Za-z0-9_.-]{1,64}', endpoint.config_name), (
        'invalid restricted SSH configuration name'
    )

    node.addSoftware('openssh-server')
    node.setFile(
        '/etc/ssh/ssh_host_ed25519_key',
        endpoint.host_private_key.strip() + '\n',
    )
    node.setFile(
        '/etc/ssh/ssh_host_ed25519_key.pub',
        endpoint.host_public_key.strip() + '\n',
    )
    node.setFile(
        '/root/.ssh/authorized_keys',
        'from="{}",restrict,command="{}" {}\n'.format(
            endpoint.source_address,
            endpoint.forced_command,
            endpoint.source_public_key.strip(),
        ),
    )
    node.setFile(
        '/etc/ssh/sshd_config.d/{}.conf'.format(endpoint.config_name),
        '''PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
Match User root Address {source_address}
    ForceCommand {forced_command}
'''.format(
            source_address=endpoint.source_address,
            forced_command=endpoint.forced_command,
        ),
    )
    node.appendStartCommand('chmod 0755 {}'.format(endpoint.forced_command))
    node.appendStartCommand('mkdir -p /root/.ssh /run/sshd')
    node.appendStartCommand('chmod 0700 /root/.ssh')
    node.appendStartCommand(
        'chmod 0600 /etc/ssh/ssh_host_ed25519_key /root/.ssh/authorized_keys'
    )
    node.appendStartCommand('chmod 0644 /etc/ssh/ssh_host_ed25519_key.pub')
    node.appendStartCommand(
        'usermod --shell {} root'.format(endpoint.forced_command)
    )
    node.appendStartCommand('service ssh start')


__all__ = [
    'RestrictedSshEndpoint',
    'generateSshKeyPair',
    'installRestrictedSshEndpoint',
]
