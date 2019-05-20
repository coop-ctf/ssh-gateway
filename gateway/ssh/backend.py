from dataclasses import dataclass
from time import sleep

import paramiko

from gateway.ssh.connection import ServerConnection


@dataclass
class BackendResource:
    ssh_username: str
    ssh_hostname: str
    ssh_port: int
    ssh_key: paramiko.PKey


def is_username_known(username: str) -> bool:
    # TODO: Have an external source/DB for team names
    return username in ("test1", "test2", "test3")


def get_pod_backend(connection: ServerConnection, key: paramiko.PKey) -> BackendResource:
    # TODO: Create pod in Kubernetes
    sleep(5)
    return BackendResource(
        ssh_hostname="nice.momoperes.ca",
        ssh_port=22,
        ssh_username="momo",
        # ssh_key=None
        ssh_key=key
    )
