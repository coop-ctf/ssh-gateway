import logging
import threading

import paramiko

logger = logging.getLogger("gateway")


def create_proxy_to_backend_and_forward(hostname: str, port: int, username: str, pkey: paramiko.PKey,
                                        chan: paramiko.Channel) -> paramiko.Channel:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname=hostname, port=port, username=username, pkey=pkey)
    backend: paramiko.Channel = client.invoke_shell()

    class ForwardThread(threading.Thread):
        def run(self):
            while not backend.closed:
                try:
                    recv = backend.recv(1024)
                    chan.send(recv)
                except Exception:
                    break
            chan.close()
            backend.close()

    ForwardThread().start()
    return backend