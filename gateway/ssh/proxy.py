import logging
import threading

import paramiko

from gateway.ssh.backend import BackendResource
from gateway.ssh.connection import ServerConnection

logger = logging.getLogger("gateway.ssh")


def create_proxy_to_backend_and_forward(backend_res: BackendResource, connection: ServerConnection) -> paramiko.Channel:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname=backend_res.ssh_hostname, port=backend_res.ssh_port,
                   username=backend_res.ssh_username, pkey=backend_res.ssh_key)
    backend: paramiko.Channel = client.invoke_shell(
        width=connection.pty_dimensions.width,
        height=connection.pty_dimensions.height,
        width_pixels=connection.pty_dimensions.width_pixels,
        height_pixels=connection.pty_dimensions.height_pixels,
        term=connection.pty_dimensions.term
    )

    class ForwardThread(threading.Thread):
        def run(self):
            while not backend.closed:
                try:
                    recv = backend.recv(1024)
                    connection.channel.send(recv)
                except Exception:
                    break
            try:
                connection.channel.close()
                backend.close()
            except EOFError:
                pass
            except Exception:
                logger.error("An error occurred while closing a dead connection", exc_info=1)

    ForwardThread().start()
    return backend
