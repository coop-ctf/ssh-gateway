from dataclasses import dataclass
from typing import Optional

import paramiko

from gateway.ssh import kube, ctf
from gateway.ssh.connection import ServerConnection


@dataclass
class BackendResource:
    ssh_username: str
    ssh_hostname: str
    ssh_port: int
    ssh_key: Optional[paramiko.PKey]


def is_username_known(username: str) -> bool:
    return username.lower() in ctf.teams


def is_challenge_known(challenge: str) -> bool:
    return challenge.lower() in ctf.challenge_images.keys()


def get_pod_backend(connection: ServerConnection, key: paramiko.PKey) -> Optional[BackendResource]:
    kube_client: kube.KubeClient = kube.KubeClient.INSTANCE
    challenge = connection.challenge.lower()
    team_name = connection.server.username.lower()
    challenge_image = ctf.challenge_images[connection.challenge.lower()]

    if not kube_client:
        # For testing purposes: outside of cluster
        return BackendResource(
            ssh_hostname="nice.momoperes.ca",
            ssh_port=532,
            ssh_username="momo",
            ssh_key=None
        )

    pod_name = f"chal-{challenge}-{team_name}"
    pod = kube_client.create_pod(pod_name, challenge_image)

    if not pod:
        return None

    pod_ip = kube_client.wait_until_pod_has_ip(pod, 30.0)
    if not pod_ip:
        return None

    if not kube_client.wait_until_pod_port_available(pod, pod_ip, 22, 15.0):
        return None

    return BackendResource(
        ssh_hostname=pod_ip,
        ssh_port=22,
        ssh_username="guest",
        ssh_key=key
    )
