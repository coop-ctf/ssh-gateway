import logging
import threading

import paramiko

from gateway.ssh import pty

logger = logging.getLogger("gateway.ssh")


def create_proxy_to_backend_and_forward(hostname: str, port: int, username: str, pkey: paramiko.PKey,
                                        chan: paramiko.Channel, dimensions: pty.PtyDimensions) -> paramiko.Channel:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname=hostname, port=port, username=username, pkey=pkey)
    backend: paramiko.Channel = client.invoke_shell(
        width=dimensions.width,
        height=dimensions.height,
        width_pixels=dimensions.width_pixels,
        height_pixels=dimensions.height_pixels
    )

    class ForwardThread(threading.Thread):
        def run(self):
            while not backend.closed:
                try:
                    recv = backend.recv(1024)
                    chan.send(recv)
                except Exception:
                    break
            try:
                chan.close()
                backend.close()
            except Exception as e:
                logger.debug("An error occurred while closing a dead connection: %s", e.__class__.__name__)

    ForwardThread().start()
    return backend
