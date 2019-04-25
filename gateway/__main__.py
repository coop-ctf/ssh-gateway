import logging
import socket
import sys
import threading
import traceback
import warnings
from time import sleep

import paramiko
from cryptography.utils import CryptographyDeprecationWarning

from gateway.server import GatewayServer

logging.basicConfig(format='%(asctime)s - [%(levelname)s] %(message)s')
logger = logging.getLogger("gateway")
logger.setLevel(logging.DEBUG)

warnings.filterwarnings(
    action='ignore',
    category=CryptographyDeprecationWarning
)


class ConnectionThread(threading.Thread):
    def __init__(self, client, transport: paramiko.Transport, server: GatewayServer):
        super().__init__()
        self.client = client
        self.server = server
        self.transport = transport
        self.channel = None

    def run(self):
        self.channel: paramiko.Channel = self.transport.accept(20)
        self.server.event.wait(10)
        if not self.server.event.is_set():
            logger.debug("Client %s never requested a shell, closing", id(self.client))
            self.channel.close()
            self.transport.close()
            return

        self.channel.send("Preparing resources...\r\n")
        sleep(5)
        try:
            backend = create_proxy_to_backend_and_forward(self.channel)
        except Exception:
            logger.error("Failed to create connection to backend (proxy) for client %s", id(self.client), exc_info=1)
            self.channel.send("*********\r\n"
                              "  Could not create connection due to a backend error.\r\n"
                              "  Please tell the event organizers!\r\n"
                              "*********\r\n")
            self.channel.close()
            self.transport.close()
            return

        logger.debug("Listening from client %s", id(self.client))
        while not self.channel.closed and not backend.closed:
            try:
                recv = self.channel.recv(1024)
                backend.send(recv)
            except Exception:
                break

        logger.debug("Connection with %s was closed", id(self.client))
        self.channel.close()
        backend.close()
        self.transport.close()


def create_proxy_to_backend_and_forward(chan: paramiko.Channel) -> paramiko.Channel:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname="localhost", port=22, username="momo")
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


def run():
    host_key = paramiko.RSAKey(filename="host.key")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 2200))
    except Exception as e:
        logger.error("Socket bind failed: %s", e)
        traceback.print_exc()
        sys.exit(1)

    try:
        sock.listen(20)
        logger.info("Listening for connections...")
    except Exception as e:
        logger.error("Socket listen failed: %s", e)
        traceback.print_exc()
        sys.exit(1)

    while True:
        client, addr = sock.accept()
        logger.debug("Received a connection from %s (id=%s)", addr, id(client))
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        server = GatewayServer(client)
        transport.start_server(server=server)
        ConnectionThread(client, transport, server).start()


if __name__ == '__main__':
    run()
