import logging
import socket
import sys
import threading
from datetime import datetime
from time import sleep

import paramiko

from gateway.ssh import pty
from gateway.ssh.connection import ServerConnection
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

        connection = ServerConnection(
            client=client,
            channel=None,
            transport=transport,
            server=None,
            backend=None,
            last_active=datetime.utcnow(),
            pty_dimensions=None
        )

        connection.server = GatewayServer(connection)
        transport.start_server(server=connection.server)
        ConnectionThread(connection, backend_key).start()


class GatewayServer(paramiko.ServerInterface):

    def __init__(self, connection: ServerConnection):
        self.client = connection.client
        self.event = threading.Event()
        self.connection = connection
        self.username = None

    def get_allowed_auths(self, username):
        return "none"

    def check_auth_none(self, username):
        logger.debug("Allowing client %s to connect without password for username: %s", id(self.client), username)
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        logger.debug("Received channel request of type '%s' from channel %s (client: %s)", kind, chanid,
                     id(self.client))
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
            self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        self.connection.pty_dimensions = pty.PtyDimensions(width=width, height=height,
                                                           width_pixels=pixelwidth, height_pixels=pixelheight)
        return True


class ConnectionThread(threading.Thread):
    def __init__(self, connection: ServerConnection, backend_key: paramiko.PKey):
        super().__init__()
        self.backend_key = backend_key
        self.client = connection.client
        self.server: GatewayServer = connection.server
        self.transport = connection.transport
        self.channel = None
        self.connection = connection

    def run(self):
        self.channel: paramiko.Channel = self.transport.accept(20)
        self.server.event.wait(10)
        if not self.server.event.is_set():
            logger.debug("Client %s never requested a shell, closing", id(self.client))
            self.connection.kill()
            return

        connections[id(self.client)] = self.connection

        self.channel.send("Preparing resources...\r\n")

        # TODO: Create pod in Kubernetes
        sleep(15)
        pod_hostname = "nice.momoperes.ca"
        pod_port = 22
        pod_username = "momo"
        pod_key = self.backend_key

        if not self.connection.is_alive():
            # TODO: Delete pod because it is no longer needed
            return

        try:
            logger.debug("Creating proxy to %s:%s, with username %s (client: %s)", pod_hostname, pod_port, pod_username,
                         id(self.client))
            self.connection.backend = create_proxy_to_backend_and_forward(pod_hostname, pod_port, pod_username, pod_key,
                                                                          self.channel, self.connection.pty_dimensions)
        except Exception:
            logger.error("Failed to create connection to backend (proxy) for client %s", id(self.client), exc_info=1)
            self.channel.send("*********\r\n"
                              "  Could not create connection due to a backend error.\r\n"
                              f"  Please tell the event organizers with this code: {id(self.client)}\r\n"
                              "*********\r\n")
            self.connection.kill()
            return

        logger.debug("Listening from client %s", id(self.client))
        while self.connection.is_alive():
            try:
                recv = self.channel.recv(1024)
                self.connection.last_active = datetime.utcnow()
                self.connection.backend.send(recv)
            except Exception:
                break

        self.connection.kill()
