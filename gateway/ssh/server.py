import logging
import socket
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from time import sleep

import paramiko

from gateway.ssh.proxy import create_proxy_to_backend_and_forward

logger = logging.getLogger("gateway.ssh")

connections = {}


def run_ssh_server(ip_address: str, port: int, host_key_file: str, backend_key_file: str):
    host_key = paramiko.RSAKey(filename=host_key_file)
    backend_key = paramiko.RSAKey(filename=backend_key_file)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip_address, port))
    except Exception as e:
        logger.error("Socket bind failed: %s", e, exc_info=1)
        sys.exit(1)

    try:
        sock.listen(20)
        logger.info("Listening for connections on %s:%s", ip_address, port)
    except Exception as e:
        logger.error("Socket listen failed: %s", e, exc_info=1)
        sys.exit(1)

    while True:
        client, addr = sock.accept()
        logger.debug("Received a connection from %s (id=%s)", addr, id(client))
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        server = GatewayServer(client)
        transport.start_server(server=server)
        ConnectionThread(client, transport, server, backend_key).start()


class GatewayServer(paramiko.ServerInterface):

    def __init__(self, client):
        self.client = client
        self.event = threading.Event()
        self.username = None

    def get_allowed_auths(self, username):
        return "none"

    def check_auth_none(self, username):
        logger.debug("Allowing client %s to connect without password for username: %s", id(self.client), username)
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        logger.debug("Received channel request of type %s from channel %s (client: %s)", kind, chanid, id(self.client))
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
            self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True


@dataclass
class ServerConnection:
    client: socket.socket
    channel: paramiko.Channel
    transport: paramiko.Transport
    server: object
    backend: paramiko.Channel
    last_active: datetime

    def kill(self):
        if not self.is_alive():
            logger.debug("Tried to kill an already closed session (client: %s)", id(self.client))
            return

        logger.debug("Connection with %s was closed", id(self.client))
        if self.backend and not self.backend.closed:
            self.backend.close()
        if self.channel and not self.channel.closed:
            self.channel.close()
        if self.transport and self.transport.active:
            self.transport.close()

    def is_alive(self) -> bool:
        if self.backend and self.backend.closed:
            return False
        if self.channel and self.channel.closed:
            return False
        if self.transport and not self.transport.active:
            return False
        return True


class ConnectionThread(threading.Thread):
    def __init__(self, client, transport: paramiko.Transport, server: GatewayServer, backend_key: paramiko.PKey):
        super().__init__()
        self.backend_key = backend_key
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

        connection = ServerConnection(
            client=self.client,
            channel=self.channel,
            transport=self.transport,
            server=self.server,
            backend=None,
            last_active=datetime.utcnow()
        )
        connections[id(self.client)] = connection

        self.channel.send("Preparing resources...\r\n")

        # TODO: Create pod in Kubernetes
        sleep(15)
        pod_hostname = "nice.momoperes.ca"
        pod_port = 22
        pod_username = "momo"
        pod_key = self.backend_key

        if not connection.is_alive():
            # TODO: Delete pod because it is no longer needed
            return

        try:
            logger.debug("Creating proxy to %s:%s, with username %s (client: %s)", pod_hostname, pod_port, pod_username,
                         id(self.client))
            connection.backend = create_proxy_to_backend_and_forward(pod_hostname, pod_port, pod_username, pod_key,
                                                                     self.channel)
        except Exception:
            logger.error("Failed to create connection to backend (proxy) for client %s", id(self.client), exc_info=1)
            self.channel.send("*********\r\n"
                              "  Could not create connection due to a backend error.\r\n"
                              f"  Please tell the event organizers with this code: {id(self.client)}\r\n"
                              "*********\r\n")
            connection.kill()
            return

        logger.debug("Listening from client %s", id(self.client))
        while not self.channel.closed and not connection.backend.closed:
            try:
                recv = self.channel.recv(1024)
                connection.last_active = datetime.utcnow()
                connection.backend.send(recv)
            except Exception:
                break

        connection.kill()
