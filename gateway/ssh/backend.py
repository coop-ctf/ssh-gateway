from dataclasses import dataclass
from typing import Optional

import paramiko

from gateway.ssh import kube
from gateway.ssh.connection import ServerConnection


@dataclass
class BackendResource:
    ssh_username: str
    ssh_hostname: str
    ssh_port: int
    ssh_key: Optional[paramiko.PKey]


def is_username_known(username: str) -> bool:
    # TODO: Have an external source/DB for team names
    return username in ("test1", "test2", "test3")


def is_challenge_known(challenge: str) -> bool:
    # TODO: Check challenge name
    return challenge in ("CATWALK", "PLAINSIGHT")


def get_pod_backend(connection: ServerConnection, key: paramiko.PKey) -> Optional[BackendResource]:
    kube_client: kube.KubeClient = kube.KubeClient.INSTANCE

    if not kube_client:
        # For testing purposes: outside of cluster
        return BackendResource(
            ssh_hostname="nice.momoperes.ca",
            ssh_port=532,
            ssh_username="momo",
            ssh_key=None
        )

    pod = kube_client.create_pod(f"chal-catwalk-{id(connection.client)}",
                                 "momothereal/ctf-linux-linux-cat")

    if not pod:
        return None

    pod_ip = kube_client.wait_until_pod_has_ip(pod, 30.0)
    if not pod_ip:
        return None

    return BackendResource(
        ssh_hostname=pod_ip,
        ssh_port=22,
        ssh_username="guest",
        ssh_key=key
    )
